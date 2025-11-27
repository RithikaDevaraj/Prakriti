import io
import logging
import tempfile
import os
from typing import Optional, Dict, Any
import speech_recognition as sr
from config import config

# Try to import gTTS for text-to-speech
try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logging.warning("gTTS not available for text-to-speech")

# Initialize speech recognizer
recognizer = sr.Recognizer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        # No initialization needed for SpeechRecognition
        pass
        
    
    async def speech_to_text(self, audio_data: bytes, language: str = "auto") -> Optional[str]:
        """Convert speech to text using SpeechRecognition"""
        try:
            # Convert to AudioData object
            audio = sr.AudioData(audio_data, 16000, 2)  # Assuming 16kHz mono audio
            
            # Map language codes to SpeechRecognition codes
            lang_mapping = {
                "en": "en-US",
                "hi": "hi-IN",
                "ta": "ta-IN",
                "te": "te-IN",
                "bn": "bn-IN",
                "mr": "mr-IN",
                "gu": "gu-IN",
                "kn": "kn-IN",
                "ml": "ml-IN",
                "or": "or-IN",
                "pa": "pa-IN",
                "ur": "ur-PK"
            }
            
            # Use English as fallback if language not supported
            recognize_lang = lang_mapping.get(language, "en-US")
            
            # Recognize speech
            text = recognizer.recognize_google(audio, language=recognize_lang)
            
            logger.info(f"Speech transcribed: {text[:50]}...")
            return text
            
        except sr.UnknownValueError:
            logger.warning("Speech Recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")
            return None
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
        """Get list of supported languages for speech-to-text (using Google Speech Recognition)"""
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