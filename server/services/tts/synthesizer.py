"""
TTS Synthesis Service
"""
import httpx
import aiosqlite
import re
from typing import Optional

from models import DATABASE_PATH
from utils import decrypt_api_key, save_audio, generate_id


async def get_tts_config(config_id: Optional[str] = None) -> Optional[dict]:
    """Get TTS configuration by ID or get active config."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if config_id:
            query = "SELECT * FROM tts_configs WHERE id = ?"
            params = (config_id,)
        else:
            query = "SELECT * FROM tts_configs WHERE is_active = 1"
            params = ()
        
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            return {
                "id": row["id"],
                "type": row["type"],
                "api_key": decrypt_api_key(row["api_key_encrypted"]),
                "default_voice_id": row["default_voice_id"],
                # Extended parameters (with fallbacks)
                "model_id": row["model_id"] if "model_id" in row.keys() else "",
                "stability": row["stability"] if "stability" in row.keys() else 0.5,
                "similarity_boost": row["similarity_boost"] if "similarity_boost" in row.keys() else 0.75,
                "speed": row["speed"] if "speed" in row.keys() else 1.0,
                "dialogue_wrap_pattern": row["dialogue_wrap_pattern"] if "dialogue_wrap_pattern" in row.keys() else "",
            }


async def get_voice_for_character(config_id: str, character_name: str) -> Optional[str]:
    """Get the voice ID for a specific character."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT voice_id FROM character_voices WHERE tts_config_id = ? AND character_name = ?",
            (config_id, character_name)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


def apply_dialogue_wrap(text: str, pattern: str) -> str:
    """
    Apply dialogue wrapping pattern to text before synthesis.
    
    Pattern uses {text} placeholder for the dialogue content.
    Common patterns:
    - "<speak>{text}</speak>" - SSML wrapper
    - "「{text}」" - Japanese quotes
    - "*{text}*" - Emphasis markers
    """
    if not pattern or "{text}" not in pattern:
        return text
    return pattern.replace("{text}", text)


async def synthesize_speech(
    text: str,
    chat_session_id: str,
    voice_id: Optional[str] = None,
    character_name: Optional[str] = None,
    config_id: Optional[str] = None
) -> str:
    """
    Synthesize speech from text.
    
    Args:
        text: Text to synthesize
        chat_session_id: Chat session ID for saving audio
        voice_id: Optional specific voice ID
        character_name: Optional character name to look up voice
        config_id: Optional specific config ID
    
    Returns:
        URL path to the saved audio file
    """
    config = await get_tts_config(config_id)
    if not config:
        raise Exception("No TTS configuration found")
    
    # Apply dialogue wrap pattern if configured
    wrap_pattern = config.get("dialogue_wrap_pattern", "")
    if wrap_pattern:
        text = apply_dialogue_wrap(text, wrap_pattern)
    
    # Resolve voice ID
    if voice_id is None:
        if character_name:
            voice_id = await get_voice_for_character(config["id"], character_name)
        if voice_id is None:
            voice_id = config.get("default_voice_id")
    
    if not voice_id:
        raise Exception("No voice ID specified or configured")
    
    if config["type"] == "elevenlabs":
        return await synthesize_elevenlabs(text, voice_id, chat_session_id, config)
    elif config["type"] == "openai":
        return await synthesize_openai(text, voice_id, chat_session_id, config)
    else:
        raise Exception(f"Unknown TTS type: {config['type']}")


async def synthesize_elevenlabs(
    text: str,
    voice_id: str,
    chat_session_id: str,
    config: dict
) -> str:
    """Synthesize using ElevenLabs API."""
    api_key = config["api_key"]
    
    # Use configured model or default
    model_id = config.get("model_id", "") or "eleven_multilingual_v2"
    stability = config.get("stability", 0.5)
    similarity_boost = config.get("similarity_boost", 0.75)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": model_id,
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                }
            },
            timeout=60.0
        )
        
        if response.status_code != 200:
            raise Exception(f"ElevenLabs API error: {response.text}")
        
        audio_data = response.content
        filename = f"{generate_id()}.mp3"
        audio_url = await save_audio(audio_data, chat_session_id, filename)
        return audio_url


async def synthesize_openai(
    text: str,
    voice_id: str,
    chat_session_id: str,
    config: dict
) -> str:
    """Synthesize using OpenAI TTS API."""
    api_key = config["api_key"]
    
    # Use configured model and speed
    model = config.get("model_id", "") or "tts-1"
    speed = config.get("speed", 1.0)
    
    # Clamp speed to OpenAI limits
    speed = max(0.25, min(4.0, speed))
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": text,
                "voice": voice_id,  # alloy, echo, fable, onyx, nova, shimmer
                "speed": speed,
            },
            timeout=60.0
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI TTS API error: {response.text}")
        
        audio_data = response.content
        filename = f"{generate_id()}.mp3"
        audio_url = await save_audio(audio_data, chat_session_id, filename)
        return audio_url


async def get_available_voices(type: str, api_key: str) -> list[dict]:
    """Fetch available voices from the TTS provider."""
    if type == "elevenlabs":
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": api_key},
                timeout=30.0
            )
            if response.status_code != 200:
                raise Exception(f"Failed to fetch voices: {response.text}")
            
            data = response.json()
            return [
                {"id": v["voice_id"], "name": v["name"], "preview_url": v.get("preview_url")}
                for v in data.get("voices", [])
            ]
    
    elif type == "openai":
        # OpenAI has fixed voices
        return [
            {"id": "alloy", "name": "Alloy"},
            {"id": "echo", "name": "Echo"},
            {"id": "fable", "name": "Fable"},
            {"id": "onyx", "name": "Onyx"},
            {"id": "nova", "name": "Nova"},
            {"id": "shimmer", "name": "Shimmer"},
        ]
    
    else:
        return []
