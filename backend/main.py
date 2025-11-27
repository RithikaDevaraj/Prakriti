from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import uvicorn
import io
import asyncio
import os
from datetime import datetime
from config import config
from kg_connector import neo4j_connector
from ragpipeline import rag_pipeline
from voice_handler import voice_handler
from live_data_service import live_data_service
from fertilizer_service import fertilizer_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Agentic KG-RAG System for Indian Agriculture",
    description="AI-powered agricultural advisory system with voice, multilingual support, and live data",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced Pydantic models
class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    region: Optional[str] = None
    language: Optional[str] = "en"
    include_live_data: Optional[bool] = True

class VoiceQueryRequest(BaseModel):
    language: Optional[str] = "auto"

class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en"

class RecommendationRequest(BaseModel):
    crop_name: str
    soil_type: str
    nitrogen: float
    phosphorus: float
    potassium: float
    moisture: float
    temperature: float
    humidity: Optional[float] = None

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    try:
        if not config.validate_config():
            logger.error("Configuration validation failed")
            return
        
        # Auto-load data if database is empty
        neo4j_connector.auto_load_data()
        
        # Note: Fertilizer ML model should be trained first using train_model.py
        # The model will be loaded automatically by fertilizer_service on first use
        
        # Start live data updates
        asyncio.create_task(start_live_data_updates())
        
        logger.info("Enhanced application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

async def start_live_data_updates():
    """Start periodic live data updates"""
    while True:
        try:
            await live_data_service.update_knowledge_graph_with_live_data()
            await asyncio.sleep(3600)  # Update every hour
        except Exception as e:
            logger.error(f"Live data update error: {e}")
            await asyncio.sleep(300)  # Retry after 5 minutes on error

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Enhanced Agentic KG-RAG System for Indian Agriculture",
        "status": "healthy",
        "version": "2.0.0",
        "features": ["speech_to_text", "text_to_speech", "multilingual", "live_data"]
    }

# Add a dedicated health check endpoint for Render and other monitoring services
@app.get("/health")
async def health_check():
    """Dedicated health check endpoint for deployment platforms"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Enhanced query endpoint (uses Groq LLM)
@app.post("/query")
async def process_query(request: QueryRequest):
    """Process agricultural query with 4-step RAG pipeline (interpret, query_kg, enrich, gen)"""
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Process query - always uses multilingual support and live data
        # Llama 3.1 8B handles languages directly, no translation needed
        result = await rag_pipeline.process_multilingual_query(
            request.query, request.language if request.language != "auto" else "auto"
        )
        
        # Add timestamp and metadata
        from datetime import datetime
        result["timestamp"] = datetime.now().isoformat()
        result["features_used"] = {
            "multilingual": True,  # Always supported via Llama 3.1 8B
            "live_data": request.include_live_data,
            "voice": False,
            "model": "groq-llama-3.1-8b"
        }
        
        logger.info(f"Processed query: {request.query[:50]}...")
        return result
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# Voice query endpoint
@app.post("/voice-query")
async def process_voice_query(
    audio: UploadFile = File(...),
    language: str = Form("auto")
):
    """Process voice query with speech-to-text"""
    try:
        if not audio.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await audio.read()
        
        # Process voice query
        result = await rag_pipeline.process_voice_query(audio_data, language)
        
        # Add metadata
        from datetime import datetime
        result["timestamp"] = datetime.now().isoformat()
        result["features_used"] = {
            "voice": True,
            "multilingual": language != "en",
            "live_data": True
        }
        
        logger.info(f"Processed voice query in {language}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing voice query: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing voice query: {str(e)}")

# Text-to-speech endpoint
@app.post("/text-to-speech")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using gTTS"""
    try:
        # Generate speech file
        audio_file_path = await voice_handler.text_to_speech(
            request.text, request.language
        )
        
        if not audio_file_path:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Return the audio file with cleanup
        background_tasks = BackgroundTasks()
        background_tasks.add_task(os.remove, audio_file_path)
        
        return FileResponse(
            path=audio_file_path,
            media_type="audio/mpeg",
            filename="response.mp3",
            background=background_tasks
        )
        
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

# Translation removed - Llama 3.1 8B handles languages directly

# Live data endpoints
@app.get("/live-data/weather/gps/{latitude}/{longitude}")
async def get_weather_data_by_gps(latitude: float, longitude: float):
    """Get current weather data for GPS coordinates"""
    try:
        # Try to fetch weather data using Indian Weather API
        try:
            weather_data = await live_data_service.fetch_indian_weather_data_by_coords(latitude, longitude)
            return weather_data
        except Exception as indian_api_error:
            logger.warning(f"Indian Weather API failed for coordinates ({latitude}, {longitude}), trying Open-Meteo: {indian_api_error}")
            
            # Fallback to Open-Meteo
            # First, we need to find the closest city to these coordinates
            closest_city = None
            min_distance = float('inf')
            
            logger.debug(f"Finding closest city for coordinates: ({latitude}, {longitude})")
            
            for city_name, (city_lat, city_lon) in config.WEATHER_CITIES.items():
                # Calculate distance (simplified)
                distance = ((latitude - city_lat) ** 2 + (longitude - city_lon) ** 2) ** 0.5
                logger.debug(f"Distance from ({latitude}, {longitude}) to {city_name} ({city_lat}, {city_lon}): {distance}")
                if distance < min_distance:
                    min_distance = distance
                    closest_city = city_name
            
            logger.debug(f"Closest city found: {closest_city} with distance {min_distance}")
            
            if closest_city:
                weather_data = await live_data_service.fetch_weather_data(closest_city)
                # Update the region name to reflect it's based on coordinates
                weather_data["region"] = f"Near {closest_city} ({latitude:.4f}, {longitude:.4f})"
                return weather_data
            else:
                raise HTTPException(status_code=404, detail="No nearby city found for weather data")
                
    except Exception as e:
        logger.error(f"Error fetching weather data by GPS: {e}")
        raise HTTPException(status_code=500, detail=f"Weather data error: {str(e)}")

@app.get("/live-data/weather/{region}")
async def get_weather_data(region: str):
    """Get current weather data for a region"""
    try:
        weather_data = await live_data_service.fetch_weather_data(region)
        return weather_data
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        raise HTTPException(status_code=500, detail=f"Weather data error: {str(e)}")

@app.get("/live-data/schemes")
async def get_government_schemes():
    """Get current government agricultural schemes"""
    try:
        schemes = await live_data_service.fetch_government_schemes()
        return {"schemes": schemes, "count": len(schemes)}
    except Exception as e:
        logger.error(f"Error fetching schemes: {e}")
        raise HTTPException(status_code=500, detail=f"Schemes data error: {str(e)}")

@app.get("/live-data/market-prices")
async def get_market_prices():
    """Get current market prices"""
    try:
        prices = await live_data_service.fetch_market_prices()
        return {"market_prices": prices, "count": len(prices)}
    except Exception as e:
        logger.error(f"Error fetching market prices: {e}")
        raise HTTPException(status_code=500, detail=f"Market data error: {str(e)}")

@app.post("/live-data/update")
async def update_live_data():
    """Manually trigger live data update"""
    try:
        await live_data_service.update_knowledge_graph_with_live_data()
        return {"status": "success", "message": "Live data updated successfully"}
    except Exception as e:
        logger.error(f"Error updating live data: {e}")
        raise HTTPException(status_code=500, detail=f"Live data update error: {str(e)}")

# Language support endpoints
@app.get("/languages/supported")
async def get_supported_languages():
    """Get list of supported languages (handled by Llama 3.1 8B)"""
    return {
        "stt_languages": voice_handler.get_supported_languages(),
        "tts_languages": voice_handler.get_supported_languages(),
        "llm_languages": ["en", "hi", "ta", "te", "bn", "gu", "kn", "ml"]  # Languages supported by Llama 3.1 8B
    }

# Enhanced graph endpoint
@app.get("/graph")
async def get_graph_data():
    """Get enhanced graph data including live data nodes"""
    try:
        # Get basic graph data
        sample_nodes = neo4j_connector.get_sample_nodes(limit=20)
        sample_relationships = neo4j_connector.get_sample_relationships(limit=30)
        
        # Get live data summary
        live_summary = await live_data_service.get_live_data_summary()
        
        # Format for visualization
        nodes = []
        links = []
        node_counter = 0
        
        # Add regular nodes
        for node_type, node_list in sample_nodes.items():
            for node in node_list:
                node_id = f"{node_type}_{node_counter}"
                nodes.append({
                    "id": node_id,
                    "name": node.get('name', f"Unknown {node_type}"),
                    "type": node_type,
                    "group": node_type,
                    "properties": {k: v for k, v in node.items() if k not in ['id', 'name']}
                })
                node_counter += 1
        
        # Skipping live data augmentation in /graph per request
        
        # Add relationships
        for rel in sample_relationships:
            source_name = rel.get('source_name', 'Unknown')
            target_name = rel.get('target_name', 'Unknown')
            
            source_id = None
            target_id = None
            
            for node in nodes:
                if node['name'] == source_name:
                    source_id = node['id']
                if node['name'] == target_name:
                    target_id = node['id']
            
            if source_id and target_id:
                links.append({
                    "source": source_id,
                    "target": target_id,
                    "relationship": rel.get('relationship_type', 'RELATED_TO'),
                    "value": 1
                })
        
        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "total_nodes": len(nodes),
                "total_relationships": len(links),
                "live_data_status": live_summary.get("status", "Unknown")
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting enhanced graph data: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving graph data: {str(e)}")

# Neighborhood graph endpoint
@app.get("/graph/neighbors")
async def get_graph_neighbors(name: str, limit: int = 24):
    """Return a 1-hop neighborhood subgraph for the given node name, excluding WeatherData and MarketPrice nodes."""
    try:
        nodes_map: Dict[str, Dict[str, Any]] = {}
        links: List[Dict[str, Any]] = []
        # Also exclude Live* per request
        exclude_labels = {"WeatherData", "MarketPrice", "LiveMarketPrice", "LiveWeatherData"}
        with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
            query = (
                "MATCH (a {name: $name})-[r]-(b) "
                "RETURN labels(a) AS a_labels, a AS a_node, labels(b) AS b_labels, b AS b_node, type(r) AS rel "
                "LIMIT $limit"
            )
            records = session.run(query, name=name, limit=limit)
            for rec in records:
                a_node = dict(rec["a_node"])  # type: ignore
                b_node = dict(rec["b_node"])  # type: ignore
                a_labels = rec["a_labels"]
                b_labels = rec["b_labels"]
                rel = rec["rel"]

                def add_node(n: Dict[str, Any], labels: List[str]):
                    node_name = n.get("name") or "Unknown"
                    node_type = (labels[0] if labels else "Node")
                    if node_type in exclude_labels:
                        return None
                    if node_name not in nodes_map:
                        nodes_map[node_name] = {
                            "id": node_name,
                            "name": node_name,
                            "type": node_type.lower(),
                            "properties": {k: v for k, v in n.items() if k not in ["id", "name"]},
                        }
                    return node_name

                src = add_node(a_node, a_labels)
                dst = add_node(b_node, b_labels)
                if src and dst:
                    links.append({"source": src, "target": dst, "relationship": rel})

        return {"nodes": list(nodes_map.values()), "links": links}
    except Exception as e:
        logger.error(f"Error getting neighbors for {name}: {e}")
        raise HTTPException(status_code=500, detail=f"Neighborhood error: {str(e)}")

# Enhanced status endpoint
@app.get("/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        # Check Neo4j connection
        neo4j_status = "connected"
        try:
            with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                session.run("RETURN 1")
        except:
            neo4j_status = "disconnected"
        
        # Get component statuses
        live_data_summary = await live_data_service.get_live_data_summary()
        
        return {
            "neo4j": neo4j_status,
            "rag_pipeline": "initialized",
            "live_data_service": live_data_summary,
            "voice_handler": "ready (STT and TTS)",
            "config_valid": config.validate_config(),
            "features": {
                "voice_support": "Full (STT and TTS)",
                "multilingual": True,  # Via Llama 3.1 8B
                "live_data": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {str(e)}")

# Events and agent updater endpoints removed - not part of core RAG workflow

# Fertilizer endpoints (ML-based)
@app.post("/fertilizer/recommendation")
async def get_fertilizer_recommendation(request: RecommendationRequest):
    """Get fertilizer recommendations for a crop using ML model"""
    try:
        if not request.crop_name.strip():
            raise HTTPException(status_code=400, detail="Crop name is required")
        
        if not request.soil_type.strip():
            raise HTTPException(status_code=400, detail="Soil type is required")
        
        # Generate recommendation report
        report = fertilizer_service.generate_recommendation_report(
            crop_name=request.crop_name,
            soil_type=request.soil_type,
            n=request.nitrogen,
            p=request.phosphorus,
            k=request.potassium,
            moisture=request.moisture,
            temperature=request.temperature,
            humidity=request.humidity
        )
        
        return {
            "report": report,
            "crop_name": request.crop_name,
            "soil_type": request.soil_type,
            "timestamp": datetime.now().isoformat(),
            "model_version": fertilizer_service.model_version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating recommendation: {str(e)}")

@app.get("/fertilizer/search")
async def search_fertilizers(search_term: str = ""):
    """Search for fertilizers in KG"""
    try:
        products = neo4j_connector.search_fertilizers_pesticides(search_term, "fertilizer")
        return {
            "fertilizers": products,
            "count": len(products)
        }
    except Exception as e:
        logger.error(f"Error searching fertilizers: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching fertilizers: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG
    )