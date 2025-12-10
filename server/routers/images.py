"""
Images Router - Handles image generation API configuration and requests
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import aiosqlite

from models import DATABASE_PATH, ImageConfig, ImageConfigCreate, mask_api_key
from utils import encrypt_api_key, decrypt_api_key, generate_id
from services.image import generate_image

router = APIRouter()


@router.get("/configs", response_model=list[ImageConfig])
async def list_image_configs():
    """List all image generation configurations."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM image_configs ORDER BY name") as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                # Handle missing columns for backwards compatibility
                result.append(ImageConfig(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    base_url=row["base_url"],
                    api_key_masked=mask_api_key(decrypt_api_key(row["api_key_encrypted"])),
                    model=row["model"],
                    size=row["size"] or "1024x1024",
                    quality=row["quality"] or "standard",
                    negative_prompt=row["negative_prompt"] if "negative_prompt" in row.keys() else "",
                    steps=row["steps"] if "steps" in row.keys() else 28,
                    cfg_scale=row["cfg_scale"] if "cfg_scale" in row.keys() else 7.0,
                    sampler=row["sampler"] if "sampler" in row.keys() else "",
                    workflow_json=row["workflow_json"] if "workflow_json" in row.keys() else "",
                    prompt_node_id=row["prompt_node_id"] if "prompt_node_id" in row.keys() else None,
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                ))
            return result


@router.post("/configs", response_model=ImageConfig)
async def create_image_config(config: ImageConfigCreate):
    """Create a new image generation configuration."""
    config_id = generate_id()
    now = datetime.utcnow().isoformat()
    encrypted_key = encrypt_api_key(config.api_key)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO image_configs 
            (id, name, type, base_url, api_key_encrypted, model, size, quality,
             negative_prompt, steps, cfg_scale, sampler, workflow_json, prompt_node_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (config_id, config.name, config.type, config.base_url, encrypted_key,
             config.model, config.size, config.quality, config.negative_prompt,
             config.steps, config.cfg_scale, config.sampler, config.workflow_json, 
             config.prompt_node_id, now, now)
        )
        await db.commit()
    
    return ImageConfig(
        id=config_id,
        name=config.name,
        type=config.type,
        base_url=config.base_url,
        api_key_masked=mask_api_key(config.api_key),
        model=config.model,
        size=config.size,
        quality=config.quality,
        negative_prompt=config.negative_prompt,
        steps=config.steps,
        cfg_scale=config.cfg_scale,
        sampler=config.sampler,
        workflow_json=config.workflow_json,
        prompt_node_id=config.prompt_node_id,
        is_active=False,
        created_at=now,
        updated_at=now,
    )


@router.put("/configs/{config_id}", response_model=ImageConfig)
async def update_image_config(config_id: str, config: ImageConfigCreate):
    """Update an existing image configuration."""
    now = datetime.utcnow().isoformat()
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check if config exists
        async with db.execute("SELECT id FROM image_configs WHERE id = ?", (config_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=404, detail="Config not found")
        
        # Encrypt API key if provided
        encrypted_key = encrypt_api_key(config.api_key) if config.api_key else ""
        
        # Update config
        await db.execute("""
            UPDATE image_configs SET
                name = ?, type = ?, base_url = ?, api_key_encrypted = ?,
                model = ?, size = ?, quality = ?, negative_prompt = ?,
                steps = ?, cfg_scale = ?, sampler = ?, workflow_json = ?,
                prompt_node_id = ?, updated_at = ?
            WHERE id = ?
        """, (
            config.name, config.type, config.base_url, encrypted_key,
            config.model or "", config.size or "1024x1024", config.quality or "standard",
            config.negative_prompt or "", config.steps or 28, config.cfg_scale or 7.0,
            config.sampler or "", config.workflow_json or "", config.prompt_node_id or "",
            now, config_id
        ))
        await db.commit()
        
        # Return updated config
        async with db.execute("SELECT * FROM image_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            return ImageConfig(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                base_url=row["base_url"],
                api_key_masked=mask_api_key(decrypt_api_key(row["api_key_encrypted"])),
                model=row["model"],
                size=row["size"] or "1024x1024",
                quality=row["quality"] or "standard",
                negative_prompt=row["negative_prompt"] if "negative_prompt" in row.keys() else "",
                steps=row["steps"] if "steps" in row.keys() else 28,
                cfg_scale=row["cfg_scale"] if "cfg_scale" in row.keys() else 7.0,
                sampler=row["sampler"] if "sampler" in row.keys() else "",
                workflow_json=row["workflow_json"] if "workflow_json" in row.keys() else "",
                prompt_node_id=row["prompt_node_id"] if "prompt_node_id" in row.keys() else None,
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


@router.delete("/configs/{config_id}")
async def delete_image_config(config_id: str):
    """Delete an image configuration."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        result = await db.execute("DELETE FROM image_configs WHERE id = ?", (config_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Config not found")
    return {"status": "deleted"}


@router.put("/configs/{config_id}/activate")
async def activate_image_config(config_id: str):
    """Set an image config as active."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE image_configs SET is_active = 0")
        await db.execute(
            "UPDATE image_configs SET is_active = 1, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), config_id)
        )
        await db.commit()
    return {"status": "activated"}


class GenerateImageRequest(BaseModel):
    prompt: str
    chat_session_id: str
    config_id: Optional[str] = None  # Use active if not specified


@router.post("/generate")
async def generate_image_endpoint(request: GenerateImageRequest):
    """Generate an image using the configured API."""
    try:
        image_url = await generate_image(
            prompt=request.prompt,
            chat_session_id=request.chat_session_id,
            config_id=request.config_id
        )
        return {"image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{config_id}/test")
async def test_image_config(config_id: str):
    """Test the image generation API connection."""
    import httpx
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM image_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Config not found")
    
    api_type = row["type"]
    base_url = row["base_url"].rstrip("/")
    api_key = decrypt_api_key(row["api_key_encrypted"])
    
    try:
        async with httpx.AsyncClient() as client:
            if api_type == "openai":
                # Test by listing models
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "connected", "message": "API connection successful"}
                else:
                    return {"status": "error", "message": f"API returned status {response.status_code}"}
            elif api_type == "stable_diffusion":
                # Test SD API health
                response = await client.get(f"{base_url}/health", timeout=10.0)
                if response.status_code == 200:
                    return {"status": "connected", "message": "Stable Diffusion API is healthy"}
                else:
                    return {"status": "error", "message": f"SD API returned status {response.status_code}"}
            elif api_type == "comfyui":
                # Test ComfyUI system info
                response = await client.get(f"{base_url}/system_stats", timeout=10.0)
                if response.status_code == 200:
                    return {"status": "connected", "message": "ComfyUI API is healthy"}
                else:
                    return {"status": "error", "message": f"ComfyUI returned status {response.status_code}"}
            elif api_type == "novelai":
                # Test NovelAI by checking user subscription info
                response = await client.get(
                    "https://api.novelai.net/user/subscription",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    tier = data.get("tier", 0)
                    tier_names = {0: "Free", 1: "Tablet", 2: "Scroll", 3: "Opus"}
                    return {"status": "connected", "message": f"NovelAI connected - Tier: {tier_names.get(tier, tier)}"}
                elif response.status_code == 401:
                    return {"status": "error", "message": "Invalid NovelAI API token"}
                else:
                    return {"status": "error", "message": f"NovelAI returned status {response.status_code}"}
            else:
                return {"status": "unknown", "message": f"Unknown API type: {api_type}"}
    except httpx.ConnectError:
        return {"status": "error", "message": "Connection failed - check URL"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "Connection timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

