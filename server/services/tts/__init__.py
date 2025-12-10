"""
TTS services.
"""
from .synthesizer import synthesize_speech, get_tts_config, get_available_voices

__all__ = ["synthesize_speech", "get_tts_config", "get_available_voices"]
