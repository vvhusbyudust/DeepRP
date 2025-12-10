"""
TTS Router - Handles Text-to-Speech API configuration and synthesis
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import aiosqlite

from models import DATABASE_PATH, TTSConfig, TTSConfigCreate, mask_api_key
from utils import encrypt_api_key, decrypt_api_key, generate_id
from services.tts import synthesize_speech

router = APIRouter()


@router.get("/configs", response_model=list[TTSConfig])
async def list_tts_configs():
    """List all TTS configurations."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tts_configs ORDER BY name") as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                # Handle backwards compatibility for old schemas
                result.append(TTSConfig(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    api_key_masked=mask_api_key(decrypt_api_key(row["api_key_encrypted"])),
                    default_voice_id=row["default_voice_id"],
                    model_id=row["model_id"] if "model_id" in row.keys() else "",
                    stability=row["stability"] if "stability" in row.keys() else 0.5,
                    similarity_boost=row["similarity_boost"] if "similarity_boost" in row.keys() else 0.75,
                    speed=row["speed"] if "speed" in row.keys() else 1.0,
                    dialogue_wrap_pattern=row["dialogue_wrap_pattern"] if "dialogue_wrap_pattern" in row.keys() else "",
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                ))
            return result


@router.post("/configs", response_model=TTSConfig)
async def create_tts_config(config: TTSConfigCreate):
    """Create a new TTS configuration."""
    config_id = generate_id()
    now = datetime.utcnow().isoformat()
    encrypted_key = encrypt_api_key(config.api_key)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO tts_configs 
            (id, name, type, api_key_encrypted, default_voice_id, model_id,
             stability, similarity_boost, speed, dialogue_wrap_pattern, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (config_id, config.name, config.type, encrypted_key, 
             config.default_voice_id, config.model_id, config.stability,
             config.similarity_boost, config.speed, config.dialogue_wrap_pattern, now, now)
        )
        await db.commit()
    
    return TTSConfig(
        id=config_id,
        name=config.name,
        type=config.type,
        api_key_masked=mask_api_key(config.api_key),
        default_voice_id=config.default_voice_id,
        model_id=config.model_id,
        stability=config.stability,
        similarity_boost=config.similarity_boost,
        speed=config.speed,
        dialogue_wrap_pattern=config.dialogue_wrap_pattern,
        is_active=False,
        created_at=now,
        updated_at=now,
    )


@router.delete("/configs/{config_id}")
async def delete_tts_config(config_id: str):
    """Delete a TTS configuration."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        result = await db.execute("DELETE FROM tts_configs WHERE id = ?", (config_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Config not found")
    return {"status": "deleted"}


@router.put("/configs/{config_id}/activate")
async def activate_tts_config(config_id: str):
    """Set a TTS config as active."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE tts_configs SET is_active = 0")
        await db.execute(
            "UPDATE tts_configs SET is_active = 1, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), config_id)
        )
        await db.commit()
    return {"status": "activated"}


class CharacterVoiceMapping(BaseModel):
    character_name: str
    voice_id: str


@router.post("/configs/{config_id}/voices")
async def set_character_voice(config_id: str, mapping: CharacterVoiceMapping):
    """Set a voice ID for a character."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if mapping exists
        async with db.execute(
            "SELECT id FROM character_voices WHERE tts_config_id = ? AND character_name = ?",
            (config_id, mapping.character_name)
        ) as cursor:
            existing = await cursor.fetchone()
        
        if existing:
            await db.execute(
                "UPDATE character_voices SET voice_id = ? WHERE id = ?",
                (mapping.voice_id, existing[0])
            )
        else:
            await db.execute(
                """
                INSERT INTO character_voices (id, tts_config_id, character_name, voice_id)
                VALUES (?, ?, ?, ?)
                """,
                (generate_id(), config_id, mapping.character_name, mapping.voice_id)
            )
        
        await db.commit()
    return {"status": "saved"}


@router.get("/configs/{config_id}/voices")
async def get_character_voices(config_id: str):
    """Get all character voice mappings for a config."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT character_name, voice_id FROM character_voices WHERE tts_config_id = ?",
            (config_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row["character_name"]: row["voice_id"] for row in rows}


class SynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None  # Use default if not specified
    character_name: Optional[str] = None  # Look up voice from mapping
    chat_session_id: str
    config_id: Optional[str] = None


@router.post("/synthesize")
async def synthesize_endpoint(request: SynthesizeRequest):
    """Synthesize speech from text."""
    try:
        audio_url = await synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            character_name=request.character_name,
            chat_session_id=request.chat_session_id,
            config_id=request.config_id
        )
        return {"audio_url": audio_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{config_id}/voices/available")
async def get_available_voices(config_id: str):
    """Fetch available voices from the TTS provider."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tts_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Config not found")
    
    # Fetch voices based on provider type
    from services.tts import get_available_voices
    try:
        voices = await get_available_voices(
            type=row["type"],
            api_key=decrypt_api_key(row["api_key_encrypted"])
        )
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{config_id}/test")
async def test_tts_config(config_id: str):
    """Test the TTS API connection."""
    import httpx
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tts_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Config not found")
    
    tts_type = row["type"]
    api_key = decrypt_api_key(row["api_key_encrypted"])
    
    try:
        async with httpx.AsyncClient() as client:
            if tts_type == "elevenlabs":
                # Test by fetching user info
                response = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": api_key},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "connected", "message": "ElevenLabs API connection successful"}
                elif response.status_code == 401:
                    return {"status": "error", "message": "Invalid API key"}
                else:
                    return {"status": "error", "message": f"API returned status {response.status_code}"}
            elif tts_type == "openai":
                # Test by listing models
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "connected", "message": "OpenAI API connection successful"}
                elif response.status_code == 401:
                    return {"status": "error", "message": "Invalid API key"}
                else:
                    return {"status": "error", "message": f"API returned status {response.status_code}"}
            else:
                return {"status": "unknown", "message": f"Unknown TTS type: {tts_type}"}
    except httpx.ConnectError:
        return {"status": "error", "message": "Connection failed - check network"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "Connection timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

