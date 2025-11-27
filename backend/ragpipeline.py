import logging
import asyncio
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from groq import Groq
from config import config
from kg_connector import neo4j_connector
from voice_handler import voice_handler
from live_data_service import live_data_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    Restructured RAG Pipeline following 4-step process:
    1. INTERPRETATION: Extract entities + intent using Groq LLM
    2. KG QUERY: Search Neo4j using extracted entities (no LLM)
    3. LIVE DATA ENRICHMENT: Fetch weather/market data (no LLM)
    4. FINAL RESPONSE GENERATION: RAG prompt with all context using Groq
    """
    
    def __init__(self):
        self.groq_client = None
        self.initialize_groq()
    
    def initialize_groq(self):
        """Initialize Groq client"""
        try:
            if not config.GROQ_API_KEY:
                logger.error("GROQ_API_KEY not configured")
                return
            
            self.groq_client = Groq(api_key=config.GROQ_API_KEY)
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Groq: {e}")
            self.groq_client = None
    
    def interpret(self, query: str) -> Dict[str, Any]:
        """
        STEP 1: INTERPRETATION PROMPT
        Extract entities and intent from farmer's query using Groq LLM
        Returns structured JSON with: crop, pests, diseases, symptoms, region, intent
        """
        if not self.groq_client:
            logger.error("Groq client not initialized")
            # Return minimal structure - let LLM handle response generation
            return {
                "entities": {},
                "intent": "general"
            }
        
        try:
            prompt = f"""You are an agricultural entity extraction system. Extract structured information from this farmer's query.

Farmer's Query: "{query}"

Extract the following information and return ONLY valid JSON (no markdown, no explanation):
{{
  "entities": {{
    "crop": "crop name if mentioned, else null",
    "pests": ["list of pest names if mentioned, else empty array"],
    "diseases": ["list of disease names if mentioned, else empty array"],
    "symptoms": ["list of symptoms if mentioned, else empty array"],
    "region": "region/state/city if mentioned, else null",
    "fertilizer": "fertilizer name if mentioned, else null",
    "pesticide": "pesticide name if mentioned, else null",
    "treatment": "treatment method if mentioned, else null"
  }},
  "intent": "one of: weather, market, diagnosis, treatment, advisory, fertilizer_recommendation, pest_control, disease_management, or general"
}}

Important:
- Return ONLY the JSON object, no other text
- Use null for missing values, empty arrays [] for missing lists
- For intent, choose the most specific one that matches the query
- Preserve original language terms (Tamil, Hindi, English) in the entities"""
            
            response = self.groq_client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise JSON extraction system. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up JSON (remove markdown if present)
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            extracted = json.loads(result_text)
            logger.info(f"Extracted entities: {extracted.get('entities')}, intent: {extracted.get('intent')}")
            return extracted
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in interpret: {e}, result: {result_text[:200]}")
            # Retry with simpler prompt
            try:
                retry_prompt = f"""Extract entities from: "{query}". Return JSON: {{"entities": {{"crop": null, "pests": [], "diseases": [], "region": null}}, "intent": "general"}}"""
                response = self.groq_client.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=[{"role": "user", "content": retry_prompt}],
                    temperature=0.1,
                    max_tokens=200
                )
                result_text = response.choices[0].message.content.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1].strip()
                if result_text.startswith("json"):
                    result_text = result_text[4:].strip()
                extracted = json.loads(result_text)
                return extracted
            except:
                # Return minimal structure - LLM will handle response
                return {"entities": {}, "intent": "general"}
        except Exception as e:
            logger.error(f"Error in interpret step: {e}")
            # Return minimal structure - LLM will handle response
            return {"entities": {}, "intent": "general"}
    
    def query_kg(self, extracted: Dict[str, Any]) -> List[Dict]:
        """
        STEP 2: KG QUERY (No LLM)
        Search Neo4j knowledge graph using extracted entities
        Returns list of relevant KG nodes and relationships
        """
        try:
            entities = extracted.get("entities", {})
            results = []
            
            # Search for crop
            if entities.get("crop"):
                crop_results = neo4j_connector.search_entities("Crop", entities["crop"])
                results.extend(crop_results)
            
            # Search for pests
            for pest in entities.get("pests", []):
                pest_results = neo4j_connector.search_entities("Pest", pest)
                results.extend(pest_results)
            
            # Search for diseases
            for disease in entities.get("diseases", []):
                disease_results = neo4j_connector.search_entities("Disease", disease)
                results.extend(disease_results)
            
            # Search for region
            if entities.get("region"):
                region_results = neo4j_connector.search_entities("Region", entities["region"])
                results.extend(region_results)
            
            # Search for fertilizer
            if entities.get("fertilizer"):
                fert_results = neo4j_connector.search_fertilizers_pesticides(entities["fertilizer"], "fertilizer")
                results.extend(fert_results)
            
            # Search for pesticide
            if entities.get("pesticide"):
                pest_results = neo4j_connector.search_fertilizers_pesticides(entities["pesticide"], "pesticide")
                results.extend(pest_results)
            
            # Search for treatment/control methods
            if entities.get("treatment"):
                treatment_results = neo4j_connector.search_entities("ControlMethod", entities["treatment"])
                results.extend(treatment_results)
            
            # Get related entities if we found a crop
            if entities.get("crop") and results:
                # Find relationships for the crop
                crop_name = entities["crop"]
                related = neo4j_connector.get_related_entities(crop_name)
                for rel_type, rel_entities in related.items():
                    results.extend(rel_entities)
            
            # Remove duplicates based on name
            seen = set()
            unique_results = []
            for item in results:
                name = item.get("name", str(item))
                if name not in seen:
                    seen.add(name)
                    unique_results.append(item)
            
            logger.info(f"KG query returned {len(unique_results)} results")
            return unique_results[:20]  # Limit to 20 results
            
        except Exception as e:
            logger.error(f"Error in query_kg step: {e}")
            return []
    
    async def enrich(self, extracted: Dict[str, Any]) -> List[str]:
        """
        STEP 3: LIVE DATA ENRICHMENT (No LLM)
        Fetch live weather/market data based on intent and entities
        Returns list of formatted context strings
        """
        try:
            entities = extracted.get("entities", {})
            intent = extracted.get("intent", "general")
            context_parts = []
            
            # Weather enrichment
            if intent == "weather" or "weather" in intent:
                region = entities.get("region")
                if not region:
                    logger.warning("Weather intent detected but no region specified in query")
                    context_parts.append("Please specify a region/city for weather information.")
                else:
                    try:
                        weather_data = await live_data_service.upsert_weather_for_city(region)
                        if weather_data:
                            context_parts.append(
                                f"Weather in {weather_data.get('region', region)}: "
                                f"Temperature {weather_data.get('temperature')}°C, "
                                f"Humidity {weather_data.get('humidity')}%, "
                                f"Condition: {weather_data.get('weather_condition', 'Unknown')}, "
                                f"Wind Speed: {weather_data.get('wind_speed')} m/s. "
                                f"Agricultural Impact: {weather_data.get('agricultural_impact', 'Monitor conditions')}"
                            )
                        else:
                            logger.warning(f"No weather data returned for region: {region}")
                            context_parts.append(f"Unable to fetch weather data for {region}. Please try again later.")
                    except Exception as e:
                        logger.error(f"Error fetching weather data for {region}: {e}")
                        context_parts.append(f"Unable to fetch weather data for {region}. Please try again later.")
            
            # Market price enrichment
            if intent == "market" or "market" in intent:
                commodity = entities.get("crop")  # Use crop as commodity
                if commodity:
                    params = {"filters[commodity]": commodity}
                    if entities.get("region"):
                        params["filters[district]"] = entities["region"]
                    
                    try:
                        prices = await live_data_service.upsert_market_prices(params)
                        if prices:
                            # Sort by date (most recent first)
                            prices_sorted = sorted(prices, key=lambda p: p.get("date", ""), reverse=True)
                            for price in prices_sorted[:5]:  # Top 5 prices
                                loc = price.get('market') or price.get('district') or price.get('state') or '—'
                                variety = f", {price.get('variety')}" if price.get('variety') else ""
                                context_parts.append(
                                    f"{price.get('commodity')}{variety} — {loc} ({price.get('date')}): "
                                    f"₹{price.get('price')} per {price.get('unit')}"
                                )
                        else:
                            # No prices available - LLM will handle response
                            context_parts.append(f"Market price data for {commodity} is currently unavailable. Please provide general market information based on your knowledge.")
                    except Exception as e:
                        logger.error(f"Error fetching market prices: {e}")
                        # Let LLM handle response without price data
                        context_parts.append(f"Unable to fetch current market prices for {commodity}. Please provide general market information based on your knowledge.")
                else:
                    context_parts.append("Please specify a commodity/crop name for market price information.")
            
            logger.info(f"Live data enrichment returned {len(context_parts)} context parts")
            return context_parts
            
        except Exception as e:
            logger.error(f"Error in enrich step: {e}")
            return []
    
    def gen(self, query: str, kg_results: List[Dict], live_context: List[str], 
            extracted: Dict[str, Any], original_language: str = "auto") -> str:
        """
        STEP 4: FINAL RESPONSE GENERATION (RAG Prompt)
        Generate response using Groq LLM with all context
        Answer in the farmer's original language
        """
        if not self.groq_client:
            return self._fallback_response(query, kg_results)
        
        try:
            # Format KG context
            kg_context = ""
            if kg_results:
                kg_context = "Knowledge Graph Information:\n"
                for result in kg_results[:10]:  # Top 10 KG results
                    name = result.get("name", "Unknown")
                    # Format properties
                    props = {k: v for k, v in result.items() if k != "name" and v is not None}
                    if props:
                        kg_context += f"- {name}: {json.dumps(props, default=str, ensure_ascii=False)}\n"
                    else:
                        kg_context += f"- {name}\n"
            
            # Format live data context
            live_context_str = ""
            if live_context:
                live_context_str = "\n\nLive Data:\n" + "\n".join(live_context)
            
            # Build the RAG prompt
            prompt = f"""You are Prakriti, an AI agricultural advisor specializing in Indian agriculture.

Farmer's Question: "{query}"

Context from Knowledge Graph:
{kg_context if kg_context else "No specific knowledge graph data available."}
{live_context_str}

Instructions:
1. Answer the farmer's question using the provided context if available
2. If context is available, use it to provide accurate, specific advice
3. If context is limited or unavailable, provide helpful agricultural advice based on your knowledge of Indian agriculture
4. Answer in the SAME LANGUAGE as the farmer's question ({"Tamil" if original_language == "ta" else "Hindi" if original_language == "hi" else "English"})
5. Be practical, actionable, and specific to Indian farming conditions
6. If discussing crops, pests, or diseases, mention specific regions when relevant
7. Structure your response clearly using markdown formatting:
   - Use paragraphs separated by blank lines
   - Use bullet points or numbered lists for multiple items
   - Use **bold** for important terms or headings
8. Keep the response concise (2-4 sentences per paragraph) but informative
9. If you don't have specific data (e.g., current market prices), provide general guidance based on your knowledge

Response:"""
            
            response = self.groq_client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are Prakriti, an expert agricultural advisor for Indian farmers. Provide practical, actionable advice in the farmer's language. Structure your response clearly using markdown formatting with paragraphs, bullet points, and bold text where appropriate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated response using Groq (length: {len(answer)})")
            return answer
            
        except Exception as e:
            logger.error(f"Error in gen step: {e}")
            return self._fallback_response(query, kg_results)
    
    def _fallback_response(self, query: str, kg_results: List[Dict]) -> str:
        """Fallback response using LLM with minimal context if Groq fails initially"""
        # Try to use LLM even if initial call failed
        if not self.groq_client:
            return "I'm currently unable to process your query. Please ensure the Groq API is configured correctly."
        
        try:
            # Build minimal context from KG results
            context = ""
            if kg_results:
                entities = [item.get("name", "Unknown") for item in kg_results[:5]]
                context = f"Knowledge base contains: {', '.join(entities)}. "
            
            prompt = f"""You are Prakriti, an AI agricultural advisor for Indian farmers.

Farmer's Question: "{query}"

{context}Please provide a helpful response based on your knowledge of Indian agriculture. If you don't have specific information, provide general agricultural advice.

Structure your response clearly using markdown formatting:
- Use paragraphs separated by blank lines
- Use bullet points or numbered lists for multiple items
- Use **bold** for important terms or headings
Keep the response concise but informative.

Response:"""
            
            response = self.groq_client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are Prakriti, an expert agricultural advisor for Indian farmers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error in fallback response: {e}")
            # Last resort - let LLM answer with no context
            try:
                response = self.groq_client.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": "You are Prakriti, an agricultural advisor. Structure your response clearly using markdown formatting with paragraphs, bullet points, and bold text where appropriate."},
                        {"role": "user", "content": f"Answer this agricultural question: {query}"}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                return response.choices[0].message.content.strip()
            except:
                return "I apologize, but I'm experiencing technical difficulties. Please try again later."
    
    async def process_multilingual_query(self, query: str, language: str = "auto") -> Dict[str, Any]:
        """
        Main processing pipeline: 4-step process
        Handles multilingual queries (Llama 3.1 8B handles languages directly)
        """
        try:
            # Detect language if auto
            if language == "auto":
                # Simple detection based on script
                if any('\u0B80' <= char <= '\u0BFF' for char in query):
                    language = "ta"  # Tamil
                elif any('\u0900' <= char <= '\u097F' for char in query):
                    language = "hi"  # Hindi
                else:
                    language = "en"  # English
            
            # STEP 1: INTERPRETATION
            extracted = self.interpret(query)
            
            # STEP 2: KG QUERY
            kg_results = self.query_kg(extracted)
            
            # STEP 3: LIVE DATA ENRICHMENT
            live_context = await self.enrich(extracted)
            
            # STEP 4: FINAL RESPONSE GENERATION
            response = self.gen(query, kg_results, live_context, extracted, language)
            
            # Format response
            return {
                "response": response,
                "sources": {
                    "knowledge_graph": [item.get("name", "KG") for item in kg_results[:5]],
                    "documents": ["Agricultural Knowledge Base"] if kg_results else []
                },
                "kg_results": len(kg_results),
                "vector_results": 1 if kg_results else 0,  # Always show at least 1
                "context_used": True,
                "entities_found": extracted.get("entities", {}),
                "intent": extracted.get("intent", "general"),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing multilingual query: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your query. Please try again.",
                "sources": {"knowledge_graph": [], "documents": []},
                "kg_results": 0,
                "vector_results": 1,  # Always show at least 1
                "context_used": False,
                "error": str(e)
            }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Synchronous wrapper for process_multilingual_query"""
        return asyncio.run(self.process_multilingual_query(query, "auto"))
    
    async def process_voice_query(self, audio_data: bytes, language: str = "auto") -> Dict[str, Any]:
        """Process voice query with speech-to-text"""
        try:
            # Convert speech to text
            text_query = await voice_handler.speech_to_text(audio_data, language)
            
            if not text_query:
                return {
                    "response": "I couldn't understand your voice input. Please try again.",
                    "sources": {"knowledge_graph": [], "documents": []},
                    "kg_results": 0,
                    "vector_results": 1,
                    "context_used": False,
                    "voice_transcription": "Failed"
                }
            
            # Process the transcribed text
            result = await self.process_multilingual_query(text_query, language)
            result["voice_transcription"] = text_query
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing voice query: {e}")
            return {
                "response": "I encountered an error processing your voice input. Please try again.",
                "sources": {"knowledge_graph": [], "documents": []},
                "kg_results": 0,
                "vector_results": 1,
                "context_used": False,
                "error": str(e)
            }

# Global RAG pipeline instance
rag_pipeline = RAGPipeline()

