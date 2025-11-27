import io
import logging
import numpy as np
from typing import Optional, Dict, Any
import soundfile as sf
from config import config
from faster_whisper import WhisperModel
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    TTS = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        # Initialize faster-whisper model for STT
        self.whisper_model = None
        self.initialize_whisper_model()
        
        # Initialize Coqui-TTS for TTS
        self.tts_model = None
        self.initialize_coqui_tts()
    
    def initialize_whisper_model(self):
        """Initialize the faster-whisper model for speech-to-text"""
        try:
            # Using the medium model for better accuracy
            self.whisper_model = WhisperModel("medium", device="cpu", compute_type="int8")
            logger.info("Faster-Whisper model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Faster-Whisper model: {e}")
            # Fallback to small model if medium fails
            try:
                self.whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
                logger.info("Faster-Whisper small model initialized as fallback")
            except Exception as e2:
                logger.error(f"Error initializing Faster-Whisper small model: {e2}")
    
    def initialize_coqui_tts(self):
        """Initialize Coqui-TTS for text-to-speech"""
        if not TTS_AVAILABLE:
            logger.warning("Coqui-TTS not available (requires Python 3.9-3.11). TTS features will be disabled.")
            self.tts_model = None
            return
        
        try:
            # Initialize Coqui-TTS with multilingual support
            # Using XTTS-v2 which supports multiple languages including Indian languages
            self.tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", 
                                progress_bar=False, 
                                gpu=False)
            logger.info("Coqui-TTS model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Coqui-TTS: {e}")
            # Fallback to a simpler model if XTTS fails
            try:
                self.tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", 
                                    progress_bar=False, 
                                    gpu=False)
                logger.info("Coqui-TTS fallback model initialized")
            except Exception as e2:
                logger.error(f"Error initializing Coqui-TTS fallback: {e2}")
                self.tts_model = None
    
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
    
    async def text_to_speech(self, text: str, language: str = "en", voice: str = None) -> Optional[bytes]:
        """Convert text to speech using Coqui-TTS"""
        try:
            if not self.tts_model:
                logger.error("Coqui-TTS model not initialized")
                return None
            
            # Map language codes to Coqui-TTS language codes
            language_mapping = {
                "en": "en",
                "hi": "hi",  # Hindi
                "ta": "ta",  # Tamil
                "te": "te",  # Telugu
                "bn": "bn",  # Bengali
                "mr": "mr",  # Marathi
                "gu": "gu",  # Gujarati
                "kn": "kn",  # Kannada
                "ml": "ml",  # Malayalam
                "or": "or",  # Odia
                "pa": "pa",  # Punjabi
                "ur": "ur"   # Urdu
            }
            
            # Get the language code for Coqui-TTS
            tts_language = language_mapping.get(language, "en")
            
            # Generate speech using Coqui-TTS
            try:
                # Coqui-TTS API: tts() returns numpy array
                # For XTTS-v2 multilingual model, we can specify language
                if "xtts" in str(self.tts_model.model_name).lower():
                    # XTTS-v2 supports language parameter
                    wav = self.tts_model.tts(text=text, language=tts_language)
                else:
                    # For other models, use default
                    wav = self.tts_model.tts(text=text)
                
                # Convert numpy array to WAV bytes
                if isinstance(wav, np.ndarray):
                    output_buffer = io.BytesIO()
                    # XTTS typically uses 22050 Hz sample rate
                    sample_rate = 22050
                    sf.write(output_buffer, wav, sample_rate, format='WAV')
                    output_buffer.seek(0)
                    audio_bytes = output_buffer.getvalue()
                    logger.info(f"Text-to-speech generated for: {text[:30]}... (language: {language})")
                    return audio_bytes
                else:
                    # If it's already bytes
                    logger.info(f"Text-to-speech generated for: {text[:30]}... (language: {language})")
                    return wav if isinstance(wav, bytes) else None
                    
            except Exception as e:
                logger.error(f"Error generating speech with Coqui-TTS: {e}")
                # Try with English as fallback
                try:
                    wav = self.tts_model.tts(text=text, language="en")
                    if isinstance(wav, np.ndarray):
                        output_buffer = io.BytesIO()
                        sf.write(output_buffer, wav, 22050, format='WAV')
                        output_buffer.seek(0)
                        return output_buffer.getvalue()
                    return wav if isinstance(wav, bytes) else None
                except Exception as e2:
                    logger.error(f"Error in Coqui-TTS fallback: {e2}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
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
