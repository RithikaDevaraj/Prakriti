import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the Agricultural AI System"""
    
    # Neo4j Configuration
    NEO4J_URI: str = os.getenv("NEO4J_URI", "")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    
    # Groq Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Dataset URLs (automatically loaded)
    CROP_CSV_URL: str = os.getenv("CROP_CSV_URL", "https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Crop.csv")
    PEST_CSV_URL: str = os.getenv("PEST_CSV_URL", "https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Pest.csv")
    DISEASE_CSV_URL: str = os.getenv("DISEASE_CSV_URL", "https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Disease.csv")
    CONTROL_METHOD_CSV_URL: str = os.getenv("CONTROL_METHOD_CSV_URL", "https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/ControlMethod.csv")
    REGION_CSV_URL: str = os.getenv("REGION_CSV_URL", "https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Region.csv")
    RELATIONS_CSV_URL: str = os.getenv("RELATIONS_CSV_URL", "https://raw.githubusercontent.com/RithikaDevaraj/agri-kg-csv/main/Relations.csv")
    
    # Redis Configuration (for caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # File paths
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./vector_store")

    # Market Prices (Agmarknet)
    AGMARKNET_API_BASE: str = os.getenv(
        "AGMARKNET_API_BASE",
        "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    )
    AGMARKNET_API_KEY: str = os.getenv("AGMARKNET_API_KEY", "")
    
    # Indian Weather API
    INDIAN_WEATHER_API_KEY: str = os.getenv("INDIAN_WEATHER_API_KEY", "")
    
    # Weather (Open-Meteo) preset city coordinates (lat, lon)
    WEATHER_CITIES: dict = {
        # Chennai, Madurai, Coimbatore (TN)
        "Chennai": (13.0878, 80.2785),
        "Madurai": (9.9190, 78.1195),
        "Coimbatore": (11.0055, 76.9661),
        # Added Hosur
        "Hosur": (12.7183, 77.8229),
    }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present"""
        required_fields = [
            cls.NEO4J_URI,
            cls.NEO4J_USERNAME,
            cls.NEO4J_PASSWORD,
        ]
        
        # Check if any required field is missing or empty
        for field in required_fields:
            if not field or field == "":
                return False
        
        return True
    
    @classmethod
    def get_missing_config(cls) -> list:
        """Get list of missing configuration fields"""
        missing = []
        
        if not cls.NEO4J_URI or cls.NEO4J_URI == "":
            missing.append("NEO4J_URI")
        if not cls.NEO4J_USERNAME or cls.NEO4J_USERNAME == "":
            missing.append("NEO4J_USERNAME")
        if not cls.NEO4J_PASSWORD or cls.NEO4J_PASSWORD == "":
            missing.append("NEO4J_PASSWORD")
        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == "":
            missing.append("OPENAI_API_KEY")
            
        return missing

# Create global config instance
config = Config()