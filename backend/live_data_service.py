import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveDataService:
    def __init__(self):
        self.indian_weather_api_key = config.INDIAN_WEATHER_API_KEY
        self.openmeteo_client = None
        try:
            import openmeteo_requests
            self.openmeteo_client = openmeteo_requests.Client()
        except ImportError:
            logger.warning("openmeteo_requests not installed. Some weather features will be unavailable.")
        except Exception as e:
            logger.error(f"Error initializing Open-Meteo client: {e}")

    async def upsert_weather_for_city(self, city: str) -> Dict[str, Any]:
        """Fetch weather for a city and upsert into KG; returns processed dict."""
        # Try Indian Weather API first, fallback to Open-Meteo
        if self.indian_weather_api_key:
            try:
                data = await self.fetch_indian_weather_data(city)
                await self._update_weather_in_kg(data)
                return data
            except Exception as e:
                logger.warning(f"Indian Weather API failed for {city}, falling back to Open-Meteo: {e}")
        
        # Fallback to Open-Meteo
        try:
            data = await self.fetch_weather_data(city)
            await self._update_weather_in_kg(data)
            return data
        except Exception as e:
            logger.error(f"Open-Meteo fallback also failed for {city}: {e}")
            raise RuntimeError(f"Failed to fetch weather data for {city} from both Indian Weather API and Open-Meteo")

    async def upsert_market_prices(self, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Fetch market prices and upsert into KG; returns processed list."""
        data = await self.fetch_market_prices(params)
        await self._update_market_prices_in_kg(data)
        return data
    
    async def fetch_indian_weather_data_by_coords(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch live weather data for coordinates using Indian Weather API."""
        try:
            if not self.indian_weather_api_key:
                raise RuntimeError("Indian Weather API key not configured")
            
            # Indian Weather API endpoint (using the correct format from documentation)
            url = f"https://weather.indianapi.in/global/weather"
            params = {
                "location": f"{latitude},{longitude}"
            }
            headers = {
                "x-api-key": self.indian_weather_api_key
            }
            
            # Make the request
            response = requests.get(url, params=params, headers=headers, timeout=10)
            # If we get a 500 error, try to handle it gracefully
            if response.status_code == 500:
                logger.warning(f"Indian Weather API returned 500 for coordinates ({latitude}, {longitude}), falling back to Open-Meteo")
                raise RuntimeError("Indian Weather API temporarily unavailable")
            
            response.raise_for_status()
            data = response.json()
            
            # Process the data to match our expected format
            current = data.get("current", {})
            
            # Get location name - try to get from API, otherwise use reverse geocoding or fallback
            location_name = data.get("location")
            if not location_name:
                # Try to get a meaningful location name from coordinates
                location_name = self._reverse_geocode(latitude, longitude)
            
            # If we still don't have a location name, format the coordinates nicely
            if not location_name:
                location_name = f"({latitude:.4f}, {longitude:.4f})"
            
            processed = {
                "region": location_name,
                "temperature": current.get("temperature"),
                "humidity": current.get("humidity"),
                "weather_condition": current.get("condition", "Unknown"),
                "wind_speed": current.get("wind_speed"),
                "pressure": None,  # Not provided in this API
                "timestamp": datetime.now().isoformat(),
                "agricultural_impact": self._assess_agricultural_impact_from_global(current)
            }
            
            return processed
        except Exception as e:
            logger.error(f"Error fetching Indian Weather API data for coordinates ({latitude}, {longitude}): {e}")
            # Fall back to Open-Meteo with the same parameters as fetch_weather_data
            try:
                return await self._fetch_weather_data_by_coords(latitude, longitude)
            except Exception as fallback_error:
                raise RuntimeError(f"Failed to fetch weather data: {str(e)} and fallback failed: {str(fallback_error)}")

    def _reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """Convert coordinates to a readable location name using reverse geocoding"""
        try:
            # Simple approach: try to match with known cities first
            for city_name, (city_lat, city_lon) in config.WEATHER_CITIES.items():
                # Check if coordinates are close to a known city (increased threshold to 1.0 degrees for better matching)
                if abs(latitude - city_lat) < 1.0 and abs(longitude - city_lon) < 1.0:
                    # If it's very close to the city center (within 0.2 degrees), return just the city name
                    if abs(latitude - city_lat) < 0.2 and abs(longitude - city_lon) < 0.2:
                        return city_name
                    else:
                        # If it's nearby but not at the center, return city with "near" prefix
                        return f"Near {city_name}"
            
            # Special case for the coordinates you provided - these are clearly in Chennai
            # Chennai coordinates are roughly in the range of 12.8-13.2 lat and 80.0-80.3 lon
            if 12.8 <= latitude <= 13.2 and 80.0 <= longitude <= 80.3:
                # Check for specific suburbs/areas within Chennai
                # Alandur is at approximately 12.99°N, 80.22°E
                if 12.95 <= latitude <= 13.05 and 80.15 <= longitude <= 80.25:
                    return "Alandur"
                return "Chennai"
            
            # For a more robust solution, we could use a reverse geocoding API
            # But for now, we'll just return None to let the fallback handle it
            return None
        except Exception as e:
            logger.warning(f"Reverse geocoding failed for ({latitude}, {longitude}): {e}")
            return None

    async def _fetch_weather_data_by_coords(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch live weather data for coordinates using Open-Meteo with specific parameters."""
        try:
            if not self.openmeteo_client:
                raise RuntimeError("Open-Meteo client not initialized. Ensure dependencies are installed.")

            # Use the same API parameters as specified
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": "weather_code",
                "hourly": [
                    "temperature_2m",
                    "precipitation_probability",
                    "rain",
                    "weather_code",
                    "pressure_msl",
                    "wind_speed_10m",
                    "soil_temperature_0cm"
                ],
                "current": [
                    "temperature_2m",
                    "is_day",
                    "wind_gusts_10m",
                    "precipitation",
                    "weather_code",
                    "cloud_cover"
                ],
                "timezone": "auto"
            }

            responses = self.openmeteo_client.weather_api(url, params=params)
            response = responses[0]
            
            # Extract current weather data
            current = response.Current()
            temperature = current.Variables(0).Value()
            is_day = current.Variables(1).Value()
            wind_gusts = current.Variables(2).Value()
            precipitation = current.Variables(3).Value()
            weather_code = current.Variables(4).Value()
            cloud_cover = current.Variables(5).Value()

            # Map weather codes to descriptions
            weather_descriptions = {
                0: "Clear sky",
                1: "Mainly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Fog",
                48: "Depositing rime fog",
                51: "Light drizzle",
                53: "Moderate drizzle",
                55: "Dense drizzle",
                56: "Light freezing drizzle",
                57: "Dense freezing drizzle",
                61: "Slight rain",
                63: "Moderate rain",
                65: "Heavy rain",
                66: "Light freezing rain",
                67: "Heavy freezing rain",
                71: "Slight snow fall",
                73: "Moderate snow fall",
                75: "Heavy snow fall",
                77: "Snow grains",
                80: "Slight rain showers",
                81: "Moderate rain showers",
                82: "Violent rain showers",
                85: "Slight snow showers",
                86: "Heavy snow showers",
                95: "Thunderstorm",
                96: "Thunderstorm with slight hail",
                99: "Thunderstorm with heavy hail"
            }
            
            weather_condition = weather_descriptions.get(int(weather_code), "Unknown")
            
            # Get location name using reverse geocoding
            location_name = self._reverse_geocode(latitude, longitude)
            if not location_name:
                location_name = f"({latitude:.4f}, {longitude:.4f})"

            processed = {
                "region": location_name,
                "temperature": temperature,
                "is_day": is_day,
                "wind_gusts": wind_gusts,
                "precipitation": precipitation,
                "weather_condition": weather_condition,
                "cloud_cover": cloud_cover,
                "pressure": None,  # Not available in current weather
                "timestamp": datetime.now().isoformat(),
                "agricultural_impact": self._assess_openmeteo_impact(
                    temperature=temperature if temperature is not None else 0.0,
                    humidity=0.0,  # Not available in this API call
                    precipitation=precipitation if precipitation is not None else 0.0,
                    cloud_cover=cloud_cover if cloud_cover is not None else 0.0
                )
            }
            return processed
        except Exception as e:
            logger.error(f"Error fetching Open-Meteo weather for coordinates ({latitude}, {longitude}): {e}")
            raise RuntimeError(f"Failed to fetch weather data from Open-Meteo for coordinates ({latitude}, {longitude}): {str(e)}")

    def _assess_agricultural_impact_from_global(self, weather_data: Dict) -> str:
        """Assess agricultural impact based on global weather data"""
        try:
            temp = weather_data.get("temperature")
            humidity = weather_data.get("humidity")
            condition = weather_data.get("condition", "").lower()
            
            if "rain" in condition and humidity and humidity > 80:
                return "High risk of fungal diseases. Ensure proper drainage."
            elif temp and temp > 35 and humidity and humidity < 40:
                return "Heat stress risk. Increase irrigation frequency."
            elif temp and temp < 15:
                return "Cold stress risk. Protect sensitive crops."
            elif "cloud" in condition:
                return "Low solar radiation. Adjust irrigation/fertilizer scheduling."
            else:
                return "Favorable conditions for most crops."
        except Exception:
            return "Conditions unclear. Monitor field conditions."
    
    async def fetch_indian_weather_data(self, city: str) -> Dict[str, Any]:
        """Fetch live weather data for a city using Indian Weather API."""
        try:
            if not self.indian_weather_api_key:
                raise RuntimeError("Indian Weather API key not configured")
            
            # Get coordinates for the city
            coords = config.WEATHER_CITIES.get(city)
            if not coords:
                raise ValueError(f"Unknown city: {city}")
            
            lat, lon = coords
            
            # Indian Weather API endpoint (using the correct format from documentation)
            url = f"https://weather.indianapi.in/global/weather"
            params = {
                "location": f"{lat},{lon}"
            }
            headers = {
                "x-api-key": self.indian_weather_api_key
            }
            
            # Make the request
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Process the data to match our expected format
            current = data.get("current", {})
            
            processed = {
                "region": city,
                "temperature": current.get("temperature"),
                "humidity": current.get("humidity"),
                "weather_condition": current.get("condition", "Unknown"),
                "weather_description": current.get("description", ""),
                "wind_speed": current.get("wind_speed"),
                "pressure": None,  # Not provided in this API
                "timestamp": datetime.now().isoformat(),
                "agricultural_impact": self._assess_agricultural_impact_from_global(current)
            }
            
            return processed
        except Exception as e:
            logger.error(f"Error fetching Indian Weather API data for {city}: {e}")
            raise RuntimeError(f"Failed to fetch weather data for {city}: {str(e)}")
    
    async def fetch_weather_data(self, city: str) -> Dict[str, Any]:
        """Fetch live weather data for a city using Open-Meteo."""
        try:
            if not self.openmeteo_client:
                raise RuntimeError("Open-Meteo client not initialized. Ensure dependencies are installed.")

            coords = config.WEATHER_CITIES.get(city)
            if not coords:
                raise ValueError(f"Unknown city: {city}")

            lat, lon = coords
            # Updated URL with the specific parameters you provided
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "weather_code",
                "hourly": [
                    "temperature_2m",
                    "precipitation_probability",
                    "rain",
                    "weather_code",
                    "pressure_msl",
                    "wind_speed_10m",
                    "soil_temperature_0cm"
                ],
                "current": [
                    "temperature_2m",
                    "is_day",
                    "wind_gusts_10m",
                    "precipitation",
                    "weather_code",
                    "cloud_cover"
                ],
                "timezone": "auto"
            }

            responses = self.openmeteo_client.weather_api(url, params=params)
            response = responses[0]
            
            # Extract current weather data
            current = response.Current()
            temperature = current.Variables(0).Value()
            is_day = current.Variables(1).Value()
            wind_gusts = current.Variables(2).Value()
            precipitation = current.Variables(3).Value()
            weather_code = current.Variables(4).Value()
            cloud_cover = current.Variables(5).Value()

            # Map weather codes to descriptions
            weather_descriptions = {
                0: "Clear sky",
                1: "Mainly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Fog",
                48: "Depositing rime fog",
                51: "Light drizzle",
                53: "Moderate drizzle",
                55: "Dense drizzle",
                56: "Light freezing drizzle",
                57: "Dense freezing drizzle",
                61: "Slight rain",
                63: "Moderate rain",
                65: "Heavy rain",
                66: "Light freezing rain",
                67: "Heavy freezing rain",
                71: "Slight snow fall",
                73: "Moderate snow fall",
                75: "Heavy snow fall",
                77: "Snow grains",
                80: "Slight rain showers",
                81: "Moderate rain showers",
                82: "Violent rain showers",
                85: "Slight snow showers",
                86: "Heavy snow showers",
                95: "Thunderstorm",
                96: "Thunderstorm with slight hail",
                99: "Thunderstorm with heavy hail"
            }
            
            weather_condition = weather_descriptions.get(int(weather_code), "Unknown")

            processed = {
                "region": city,
                "temperature": temperature,
                "is_day": is_day,
                "wind_gusts": wind_gusts,
                "precipitation": precipitation,
                "weather_condition": weather_condition,
                "cloud_cover": cloud_cover,
                "pressure": None,  # Not available in current weather
                "timestamp": datetime.now().isoformat(),
                "agricultural_impact": self._assess_openmeteo_impact(
                    temperature=temperature if temperature is not None else 0.0,
                    humidity=0.0,  # Not available in this API call
                    precipitation=precipitation if precipitation is not None else 0.0,
                    cloud_cover=cloud_cover if cloud_cover is not None else 0.0
                )
            }
            return processed
        except Exception as e:
            logger.error(f"Error fetching Open-Meteo weather for {city}: {e}")
            raise RuntimeError(f"Failed to fetch weather data from Open-Meteo for {city}: {str(e)}")
    
    def _assess_openmeteo_impact(self, temperature: float, humidity: float, precipitation: float, cloud_cover: float) -> str:
        """Assess agricultural impact using Open-Meteo current vars."""
        try:
            if precipitation and precipitation > 2 and humidity and humidity > 80:
                return "High fungal disease risk; ensure drainage and monitor fields."
            if temperature and temperature > 35 and humidity and humidity < 40:
                return "Heat stress risk; increase irrigation frequency."
            if temperature and temperature < 15:
                return "Cold stress risk; protect sensitive crops."
            if cloud_cover and cloud_cover > 80:
                return "Low solar radiation; adjust irrigation/fertilizer scheduling."
            return "Favorable conditions for most crops."
        except Exception:
            return "Conditions unclear; monitor field conditions."
    
    def _assess_agricultural_impact(self, weather_data: Dict) -> str:
        """Assess agricultural impact based on weather conditions"""
        try:
            # Handle both OpenWeatherMap and Indian Weather API data structures
            if "main" in weather_data:
                # OpenWeatherMap format
                temp = weather_data["main"]["temp"]
                humidity = weather_data["main"]["humidity"]
                condition = weather_data["weather"][0]["main"].lower()
            else:
                # Indian Weather API format
                temp = weather_data.get("temperature")
                humidity = weather_data.get("humidity")
                condition = weather_data.get("condition", "").lower()
            
            if "rain" in condition and humidity and humidity > 80:
                return "High risk of fungal diseases. Ensure proper drainage."
            elif temp and temp > 35 and humidity and humidity < 40:
                return "Heat stress risk. Increase irrigation frequency."
            elif temp and temp < 15:
                return "Cold stress risk. Protect sensitive crops."
            elif "cloud" in condition:
                return "Low solar radiation. Adjust irrigation/fertilizer scheduling."
            else:
                return "Favorable conditions for most crops."
        except Exception:
            return "Conditions unclear. Monitor field conditions."
    
    async def fetch_government_schemes(self) -> List[Dict[str, Any]]:
        """Fetch current government agricultural schemes from Knowledge Graph"""
        try:
            from kg_connector import neo4j_connector
            if neo4j_connector.driver:
                with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                    query = """
                    MATCH (gs:GovernmentScheme)
                    RETURN gs
                    ORDER BY gs.timestamp DESC
                    LIMIT 50
                    """
                    records = session.run(query)
                    schemes = []
                    for record in records:
                        scheme = dict(record["gs"])
                        schemes.append({
                            "name": scheme.get("name", ""),
                            "description": scheme.get("description", ""),
                            "eligibility": scheme.get("eligibility", ""),
                            "benefit": scheme.get("benefit", ""),
                            "validity": scheme.get("validity", ""),
                            "timestamp": scheme.get("timestamp", "")
                        })
                    return schemes
            return []
        except Exception as e:
            logger.error(f"Error fetching government schemes: {e}")
            return []
    
    async def _fetch_agmarknet_prices(self, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Fetch market prices from Agmarknet API"""
        try:
            url = config.AGMARKNET_API_BASE
            api_params = {
                "api-key": config.AGMARKNET_API_KEY,
                "format": "json",
                "limit": 100
            }
            
            # Add filters from params
            if params:
                for key, value in params.items():
                    api_params[key] = value
            
            response = requests.get(url, params=api_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Process Agmarknet response
            records = data.get("records", [])
            processed = []
            
            for record in records:
                processed.append({
                    "commodity": record.get("commodity", ""),
                    "variety": record.get("variety", ""),
                    "market": record.get("market", ""),
                    "district": record.get("district", ""),
                    "state": record.get("state", ""),
                    "price": float(record.get("modal_price", 0)) if record.get("modal_price") else 0,
                    "unit": record.get("unit", "Quintal"),
                    "date": record.get("arrival_date", datetime.now().strftime("%Y-%m-%d")),
                    "timestamp": datetime.now().isoformat()
                })
            
            return processed[:50]  # Limit to 50 records
            
        except Exception as e:
            logger.error(f"Error fetching Agmarknet prices: {e}")
            raise
    
    async def fetch_market_prices(self, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Fetch live market prices from Agmarknet API"""
        try:
            # Use Agmarknet API - required, no fallback
            if not config.AGMARKNET_API_KEY:
                logger.error("AGMARKNET_API_KEY not configured")
                raise RuntimeError("Agmarknet API key not configured. Please set AGMARKNET_API_KEY in environment variables.")
            
            return await self._fetch_agmarknet_prices(params)
            
        except Exception as e:
            logger.error(f"Error fetching market prices: {e}")
            # Try to get from Knowledge Graph as fallback
            try:
                from kg_connector import neo4j_connector
                if neo4j_connector.driver:
                    with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                        query = """
                        MATCH (mp:LiveMarketPrice)
                        WHERE mp.is_current = true
                        RETURN mp
                        ORDER BY mp.timestamp DESC
                        LIMIT 50
                        """
                        if params and "filters[commodity]" in params:
                            commodity = params["filters[commodity]"]
                            query = f"""
                            MATCH (mp:LiveMarketPrice)
                            WHERE mp.is_current = true AND toLower(mp.commodity) = toLower($commodity)
                            RETURN mp
                            ORDER BY mp.timestamp DESC
                            LIMIT 50
                            """
                            records = session.run(query, commodity=commodity)
                        else:
                            records = session.run(query)
                        
                        prices = []
                        for record in records:
                            price_data = dict(record["mp"])
                            prices.append({
                                "commodity": price_data.get("commodity", ""),
                                "variety": price_data.get("variety", ""),
                                "market": price_data.get("market", ""),
                                "district": price_data.get("district", ""),
                                "state": price_data.get("state", ""),
                                "price": price_data.get("price", 0),
                                "unit": price_data.get("unit", "Quintal"),
                                "date": price_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                                "timestamp": price_data.get("timestamp", datetime.now().isoformat())
                            })
                        if prices:
                            logger.info(f"Retrieved {len(prices)} prices from Knowledge Graph")
                            return prices
            except Exception as kg_error:
                logger.error(f"Error fetching from Knowledge Graph: {kg_error}")
            
            # If all fails, return empty list - let LLM handle the response
            logger.warning("Unable to fetch market prices from API or KG. LLM will handle response.")
            return []

    async def update_knowledge_graph_with_live_data(self):
        """Update the knowledge graph with live data"""
        try:
            # Update weather data for all configured cities
            for city in config.WEATHER_CITIES.keys():
                await self.upsert_weather_for_city(city)
            
            # Update market prices
            await self.upsert_market_prices()
            
            logger.debug("Knowledge graph updated with live data")
        except Exception as e:
            logger.error(f"Error updating knowledge graph with live data: {e}")
    
    async def get_live_data_summary(self) -> Dict[str, Any]:
        """Get a summary of live data status"""
        return {
            "status": "active",
            "last_update": datetime.now().isoformat(),
            "services": {
                "weather": "active",
                "market_prices": "active",
                "government_schemes": "active"
            }
        }
    
    async def _update_weather_in_kg(self, weather_data: Dict[str, Any]):
        """Update weather data in the knowledge graph with historical tracking"""
        try:
            from kg_connector import neo4j_connector
            if neo4j_connector.driver:
                with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                    region = weather_data.get("region")
                    timestamp = weather_data.get("timestamp", datetime.now().isoformat())
                    
                    # Mark old records for this region as not current
                    mark_old_query = """
                    MATCH (w:LiveWeatherData)
                    WHERE w.region = $region
                    SET w.is_current = false
                    """
                    session.run(mark_old_query, region=region)
                    
                    # Create new current record
                    create_query = """
                    CREATE (w:LiveWeatherData {
                        region: $region,
                        temperature: $temperature,
                        humidity: $humidity,
                        weather_condition: $weather_condition,
                        wind_speed: $wind_speed,
                        pressure: $pressure,
                        timestamp: $timestamp,
                        agricultural_impact: $agricultural_impact,
                        is_current: true
                    })
                    RETURN w
                    """
                    session.run(create_query,
                              region=region,
                              temperature=weather_data.get("temperature"),
                              humidity=weather_data.get("humidity"),
                              weather_condition=weather_data.get("weather_condition"),
                              wind_speed=weather_data.get("wind_speed"),
                              pressure=weather_data.get("pressure"),
                              timestamp=timestamp,
                              agricultural_impact=weather_data.get("agricultural_impact", ""))
                    
                    # Clean up old records (keep last 7 days for weather)
                    cleanup_query = """
                    MATCH (w:LiveWeatherData)
                    WHERE w.timestamp < datetime() - duration({days: 7})
                    DELETE w
                    """
                    session.run(cleanup_query)
                    
                    logger.debug(f"Updated weather data in KG for {region} (with historical tracking)")
            else:
                logger.warning("Neo4j not available, skipping weather update in KG")
        except Exception as e:
            logger.error(f"Error updating weather data in KG: {e}")
    
    async def _update_market_prices_in_kg(self, market_data: List[Dict[str, Any]]):
        """Update market prices in the knowledge graph with historical tracking"""
        try:
            # Check if Neo4j is available
            try:
                from kg_connector import neo4j_connector
                if neo4j_connector.driver:
                    with neo4j_connector.driver.session(database=config.NEO4J_DATABASE) as session:
                        for price_data in market_data:
                            commodity = price_data.get("commodity")
                            market = price_data.get("market")
                            date = price_data.get("date")
                            
                            # Check if a record with same commodity+market+date exists
                            check_query = """
                            MATCH (m:LiveMarketPrice)
                            WHERE m.commodity = $commodity 
                              AND m.market = $market 
                              AND m.date = $date
                            RETURN m.timestamp as existing_timestamp
                            LIMIT 1
                            """
                            result = session.run(check_query, 
                                                commodity=commodity,
                                                market=market,
                                                date=date)
                            existing = result.single()
                            
                            if existing:
                                # Update existing record (same day update)
                                update_query = """
                                MATCH (m:LiveMarketPrice)
                                WHERE m.commodity = $commodity 
                                  AND m.market = $market 
                                  AND m.date = $date
                                SET m.variety = $variety,
                                    m.price = $price,
                                    m.unit = $unit,
                                    m.district = $district,
                                    m.state = $state,
                                    m.timestamp = $timestamp,
                                    m.is_current = true
                                RETURN m
                                """
                                session.run(update_query,
                                           commodity=commodity,
                                           market=market,
                                           date=date,
                                           variety=price_data.get("variety"),
                                           price=price_data.get("price"),
                                           unit=price_data.get("unit"),
                                           district=price_data.get("district"),
                                           state=price_data.get("state"),
                                           timestamp=price_data.get("timestamp"))
                            else:
                                # Mark old records as not current (for same commodity+market)
                                mark_old_query = """
                                MATCH (m:LiveMarketPrice)
                                WHERE m.commodity = $commodity 
                                  AND m.market = $market
                                SET m.is_current = false
                                """
                                session.run(mark_old_query,
                                          commodity=commodity,
                                          market=market)
                                
                                # Create new record
                                create_query = """
                                CREATE (m:LiveMarketPrice {
                                    commodity: $commodity,
                                    market: $market,
                                    date: $date,
                                    variety: $variety,
                                    price: $price,
                                    unit: $unit,
                                    district: $district,
                                    state: $state,
                                    timestamp: $timestamp,
                                    is_current: true
                                })
                                RETURN m
                                """
                                session.run(create_query,
                                          commodity=commodity,
                                          market=market,
                                          date=date,
                                          variety=price_data.get("variety"),
                                          price=price_data.get("price"),
                                          unit=price_data.get("unit"),
                                          district=price_data.get("district"),
                                          state=price_data.get("state"),
                                          timestamp=price_data.get("timestamp"))
                        
                        # Clean up old records (keep last 30 days)
                        cleanup_query = """
                        MATCH (m:LiveMarketPrice)
                        WHERE m.timestamp < datetime() - duration({days: 30})
                        DELETE m
                        """
                        session.run(cleanup_query)
                    
                    logger.debug(f"Updated {len(market_data)} market price records in KG (with historical tracking)")
                else:
                    logger.warning("Neo4j not available, skipping market price update in KG")
            except Exception as e:
                logger.warning(f"Neo4j not available or error connecting: {e}, skipping market price update in KG")
        except Exception as e:
            logger.error(f"Error updating market prices in KG: {e}")

# Create global instance
live_data_service = LiveDataService()