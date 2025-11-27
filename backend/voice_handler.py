import io
import logging
import numpy as np
import tempfile
import os
from typing import Optional, Dict, Any
from config import config
from faster_whisper import WhisperModel

# Try to import gTTS for text-to-speech
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logging.warning("gTTS not available for text-to-speech")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        # Initialize faster-whisper model for STT
        self.whisper_model = None
        self.initialize_whisper_model()
        
    
    def initialize_whisper_model(self):
        """Initialize the faster-whisper model for speech-to-text"""
        try:
            # Using the small model for better memory efficiency on Render free tier
            self.whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("Faster-Whisper small model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Faster-Whisper small model: {e}")
            # Fallback to tiny model if small fails
            try:
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                logger.info("Faster-Whisper tiny model initialized as fallback")
            except Exception as e2:
                logger.error(f"Error initializing Faster-Whisper tiny model: {e2}")
    
    async def speech_to_text(self, audio_data: bytes, language: str = "auto") -> Optional[str]:
        """Convert speech to text using faster-whisper"""
        try:
            if not self.whisper_model:
                logger.error("Whisper model not initialized")
                return None
            
            # Convert audio bytes to numpy array
            audio_buffer = io.BytesIO(audio_data)
            
            # Use faster-whisper to transcribe
            # If language is auto, let Whisper detect it
            segments, info = self.whisper_model.transcribe(
                audio_buffer, 
                language=None if language == "auto" else language
            )
            transcription = " ".join([segment.text for segment in segments])
            
            logger.info(f"Speech transcribed: {transcription[:50]}...")
            return transcription
            
        except Exception as e:
            logger.error(f"Error in speech-to-text: {e}")
            return None
    
    async def text_to_speech(self, text: str, language: str = "en") -> Optional[str]:
        """Convert text to speech using gTTS and return the path to the audio file"""
        if not TTS_AVAILABLE:
            logger.warning("Text-to-speech is not available as gTTS is not installed")
            return None
        
        try:
            # Map language codes to gTTS compatible codes
            lang_mapping = {
                "en": "en",
                "hi": "hi",
                "ta": "ta",
                "te": "te",
                "bn": "bn",
                "mr": "mr",
                "gu": "gu",
                "kn": "kn",
                "ml": "ml",
                "or": "or",
                "pa": "pa",
                "ur": "ur"
            }
            
            # Use English as fallback if language not supported
            tts_lang = lang_mapping.get(language, "en")
            
            # Generate speech
            tts = gTTS(text=text, lang=tts_lang)
            
            # Save to temporary file
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tmp_file.name)
            
            logger.info(f"Text-to-speech generated successfully for language {tts_lang}")
            return tmp_file.name
            
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages for speech-to-text"""
        return {
            "en": "English",
            "hi": "हिंदी (Hindi)",
            "ta": "தமிழ் (Tamil)",
            "te": "తెలుగు (Telugu)",
            "bn": "বাংলা (Bengali)",
            "mr": "मराठी (Marathi)",
            "gu": "ગુજરાટી (Gujarati)",
            "kn": "ಕನ್ನಡ (Kannada)",
            "ml": "മലയാളം (Malayalam)",
            "or": "ଓଡ଼ିଆ (Odia)",
            "pa": "ਪੰਜਾਬੀ (Punjabi)",
            "ur": "اردو (Urdu)"
        }

# Global voice handler instance
voice_handler = VoiceHandler()
