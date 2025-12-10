"""
Agent Router - Handles Agent mode configuration and orchestration
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import aiosqlite
import json

from models import DATABASE_PATH, AgentConfig
from utils import generate_id
from services.agent import run_agent_pipeline

router = APIRouter()


@router.get("/config", response_model=AgentConfig)
async def get_agent_config():
    """Get agent mode configuration."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM agent_config WHERE id = 'default'") as cursor:
            row = await cursor.fetchone()
            if not row:
                # Return default config
                return AgentConfig()
            # Convert row to dict for safe access with defaults
            row_dict = dict(row)
            return AgentConfig(
                enabled=bool(row_dict.get("enabled", False)),
                director_llm_config_id=row_dict.get("director_llm_config_id"),
                director_preset_id=row_dict.get("director_preset_id"),
                writer_llm_config_id=row_dict.get("writer_llm_config_id"),
                writer_preset_id=row_dict.get("writer_preset_id"),
                enable_paint=bool(row_dict.get("enable_paint", 1)),
                painter_llm_config_id=row_dict.get("painter_llm_config_id"),
                painter_preset_id=row_dict.get("painter_preset_id"),
                image_config_id=row_dict.get("image_config_id"),
                enable_tts=bool(row_dict.get("enable_tts", 1)),
                tts_config_id=row_dict.get("tts_config_id"),
                tts_llm_config_id=row_dict.get("tts_llm_config_id"),
                tts_preset_id=row_dict.get("tts_preset_id"),
            )


@router.put("/config", response_model=AgentConfig)
async def update_agent_config(config: AgentConfig):
    """Update agent mode configuration."""
    now = datetime.utcnow().isoformat()
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if config exists
        async with db.execute("SELECT id FROM agent_config WHERE id = 'default'") as cursor:
            exists = await cursor.fetchone()
        
        if exists:
            await db.execute(
                """
                UPDATE agent_config SET
                    enabled = ?, director_llm_config_id = ?, director_preset_id = ?,
                    writer_llm_config_id = ?, writer_preset_id = ?,
                    enable_paint = ?, painter_llm_config_id = ?, painter_preset_id = ?,
                    image_config_id = ?, enable_tts = ?, tts_config_id = ?,
                    tts_llm_config_id = ?, tts_preset_id = ?, updated_at = ?
                WHERE id = 'default'
                """,
                (1 if config.enabled else 0,
                 config.director_llm_config_id, config.director_preset_id,
                 config.writer_llm_config_id, config.writer_preset_id,
                 1 if config.enable_paint else 0, config.painter_llm_config_id, config.painter_preset_id,
                 config.image_config_id, 1 if config.enable_tts else 0, config.tts_config_id,
                 config.tts_llm_config_id, config.tts_preset_id, now)
            )
        else:
            await db.execute(
                """
                INSERT INTO agent_config 
                (id, enabled, director_llm_config_id, director_preset_id,
                 writer_llm_config_id, writer_preset_id,
                 enable_paint, painter_llm_config_id, painter_preset_id,
                 image_config_id, enable_tts, tts_config_id, tts_llm_config_id, tts_preset_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ('default', 1 if config.enabled else 0,
                 config.director_llm_config_id, config.director_preset_id,
                 config.writer_llm_config_id, config.writer_preset_id,
                 1 if config.enable_paint else 0, config.painter_llm_config_id, config.painter_preset_id,
                 config.image_config_id, 1 if config.enable_tts else 0, config.tts_config_id,
                 config.tts_llm_config_id, config.tts_preset_id, now)
            )
        
        await db.commit()
    
    return config


@router.put("/toggle")
async def toggle_agent_mode():
    """Toggle agent mode on/off."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT enabled FROM agent_config WHERE id = 'default'") as cursor:
            row = await cursor.fetchone()
            if row:
                new_state = 0 if row[0] else 1
                await db.execute(
                    "UPDATE agent_config SET enabled = ?, updated_at = ? WHERE id = 'default'",
                    (new_state, datetime.utcnow().isoformat())
                )
            else:
                new_state = 1
                await db.execute(
                    "INSERT INTO agent_config (id, enabled, updated_at) VALUES (?, ?, ?)",
                    ('default', 1, datetime.utcnow().isoformat())
                )
        await db.commit()
    
    return {"enabled": bool(new_state)}


class AgentPreviewRequest(BaseModel):
    character_id: Optional[str] = None
    worldbook_ids: list[str] = []
    sample_message: str = "Hello, how are you?"
    session_id: Optional[str] = None  # Optional: load chat history from session


@router.post("/preview")
async def preview_agent_prompts(request: AgentPreviewRequest):
    """
    Preview the complete prompt structure that will be sent to each agent.
    Returns expanded prompts with placeholders for inter-agent data.
    """
    from services.agent.pipeline import build_agent_system_prompt, get_preset, get_character, get_session
    from routers.chat import load_worldbooks
    
    # Get agent config
    config = await get_agent_config()
    
    # Load context
    character = await get_character(request.character_id) if request.character_id else None
    worldbook = await load_worldbooks(request.worldbook_ids) if request.worldbook_ids else None
    
    # Load chat history from session if provided
    chat_history = []
    if request.session_id:
        session = await get_session(request.session_id)
        if session:
            chat_history = session.get("messages", [])
    
    # Build preview for each agent
    previews = {}
    
    # === DIRECTOR PREVIEW ===
    director_preset = await get_preset(config.director_preset_id) if config.director_preset_id else None
    director_system = build_agent_system_prompt(director_preset, character, worldbook, chat_history)
    
    # Build Director messages with placeholders
    director_messages = [
        {"role": "system", "content": director_system or "[No preset configured]"}
    ]
    if chat_history:
        # Show ALL chat history messages
        for msg in chat_history:
            director_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    director_messages.append({"role": "user", "content": request.sample_message or "{USER_MESSAGE}"})
    
    previews["director"] = {
        "preset_name": director_preset.get("name") if director_preset else None,
        "system_prompt": director_system or "[No preset configured]",
        "messages": director_messages
    }
    
    # === WRITER PREVIEW ===
    writer_preset = await get_preset(config.writer_preset_id) if config.writer_preset_id else None
    writer_system = build_agent_system_prompt(writer_preset, character, worldbook, chat_history)
    
    writer_messages = [
        {"role": "system", "content": writer_system or "[No preset configured]"}
    ]
    if chat_history:
        # Show ALL chat history messages
        for msg in chat_history:
            writer_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    writer_messages.append({"role": "user", "content": "Based on this scene outline, write the narrative:\n\n{DIRECTOR_OUTLINE}"})
    
    previews["writer"] = {
        "preset_name": writer_preset.get("name") if writer_preset else None,
        "system_prompt": writer_system or "[No preset configured]",
        "messages": writer_messages
    }
    
    # === PAINT DIRECTOR PREVIEW ===
    painter_preset = await get_preset(config.painter_preset_id) if config.painter_preset_id else None
    painter_system = build_agent_system_prompt(painter_preset, character, worldbook, chat_history)
    
    paint_messages = [
        {"role": "system", "content": painter_system or "[No preset configured - using default image prompt generator]"}
    ]
    if chat_history:
        # Show ALL chat history messages
        for msg in chat_history:
            paint_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    paint_messages.append({"role": "user", "content": "{DIRECTOR_OUTLINE}"})    
    previews["paint_director"] = {
        "preset_name": painter_preset.get("name") if painter_preset else None,
        "system_prompt": painter_system or "[No preset configured]",
        "messages": paint_messages
    }
    
    return {
        "previews": previews,
        "context": {
            "character_name": character.get("data", {}).get("name") if character else None,
            "worldbook_name": worldbook.get("name") if worldbook else None,
            "chat_history_length": len(chat_history)
        }
    }


class AgentMessageRequest(BaseModel):
    content: str
    session_id: str
    character_id: Optional[str] = None
    worldbook_ids: list[str] = []  # Changed from worldbook_id (singular) to worldbook_ids (list)


@router.post("/generate")
async def generate_with_agent(request: AgentMessageRequest):
    """Generate a response using the full agent pipeline (Director → Writer → Painter → TTS)."""
    # Get agent config
    config = await get_agent_config()
    if not config.enabled:
        raise HTTPException(status_code=400, detail="Agent mode is not enabled")
    
    async def generate():
        try:
            async for event in run_agent_pipeline(
                user_message=request.content,
                session_id=request.session_id,
                character_id=request.character_id,
                worldbook_ids=request.worldbook_ids,  # Now passing list
                config=config
            ):
                yield f"data: {json.dumps(event)}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
