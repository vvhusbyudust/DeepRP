"""
LLM Configuration Router
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import aiosqlite
import httpx

from models import (
    DATABASE_PATH,
    LLMConfig,
    LLMConfigCreate,
    LLMConfigUpdate,
    mask_api_key,
)
from utils import encrypt_api_key, decrypt_api_key, generate_id

router = APIRouter()


@router.get("/llm", response_model=list[LLMConfig])
async def list_llm_configs():
    """List all LLM configurations."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM llm_configs ORDER BY name") as cursor:
            rows = await cursor.fetchall()
            return [
                LLMConfig(
                    id=row["id"],
                    name=row["name"],
                    base_url=row["base_url"],
                    api_key_masked=mask_api_key(decrypt_api_key(row["api_key_encrypted"])),
                    default_model=row["default_model"],
                    is_active=bool(row["is_active"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]


@router.post("/llm", response_model=LLMConfig)
async def create_llm_config(config: LLMConfigCreate):
    """Create a new LLM configuration."""
    config_id = generate_id()
    now = datetime.utcnow().isoformat()
    encrypted_key = encrypt_api_key(config.api_key)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO llm_configs (id, name, base_url, api_key_encrypted, default_model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (config_id, config.name, config.base_url, encrypted_key, config.default_model, now, now)
        )
        await db.commit()
    
    return LLMConfig(
        id=config_id,
        name=config.name,
        base_url=config.base_url,
        api_key_masked=mask_api_key(config.api_key),
        default_model=config.default_model,
        is_active=False,
        created_at=now,
        updated_at=now,
    )


@router.put("/llm/{config_id}", response_model=LLMConfig)
async def update_llm_config(config_id: str, update: LLMConfigUpdate):
    """Update an LLM configuration."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get existing config
        async with db.execute("SELECT * FROM llm_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Config not found")
        
        # Build update query
        updates = []
        values = []
        
        if update.name is not None:
            updates.append("name = ?")
            values.append(update.name)
        if update.base_url is not None:
            updates.append("base_url = ?")
            values.append(update.base_url)
        if update.api_key is not None:
            updates.append("api_key_encrypted = ?")
            values.append(encrypt_api_key(update.api_key))
        if update.default_model is not None:
            updates.append("default_model = ?")
            values.append(update.default_model)
        if update.is_active is not None:
            # If setting active, deactivate others first
            if update.is_active:
                await db.execute("UPDATE llm_configs SET is_active = 0")
            updates.append("is_active = ?")
            values.append(1 if update.is_active else 0)
        
        now = datetime.utcnow().isoformat()
        updates.append("updated_at = ?")
        values.append(now)
        values.append(config_id)
        
        await db.execute(
            f"UPDATE llm_configs SET {', '.join(updates)} WHERE id = ?",
            values
        )
        await db.commit()
        
        # Return updated config
        async with db.execute("SELECT * FROM llm_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            return LLMConfig(
                id=row["id"],
                name=row["name"],
                base_url=row["base_url"],
                api_key_masked=mask_api_key(decrypt_api_key(row["api_key_encrypted"])),
                default_model=row["default_model"],
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


@router.delete("/llm/{config_id}")
async def delete_llm_config(config_id: str):
    """Delete an LLM configuration."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        result = await db.execute("DELETE FROM llm_configs WHERE id = ?", (config_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Config not found")
    return {"status": "deleted"}


@router.get("/llm/{config_id}/models")
async def fetch_models(config_id: str):
    """Fetch available models from the LLM API and cache them in the database."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM llm_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Config not found")
    
    api_key = decrypt_api_key(row["api_key_encrypted"])
    base_url = row["base_url"].rstrip("/")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Handle both OpenAI and other formats
            if "data" in data:
                models = [m.get("id", m.get("name")) for m in data["data"]]
            elif isinstance(data, list):
                models = [m.get("id", m.get("name", str(m))) for m in data]
            else:
                models = []
            
            # Filter out None values and sort
            models = sorted([m for m in models if m])
            
            # Save to database for caching
            import json
            now = datetime.utcnow().isoformat()
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    "UPDATE llm_configs SET cached_models = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(models), now, config_id)
                )
                await db.commit()
            
            return {"models": models, "cached_at": now}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch models: {str(e)}")


@router.get("/llm/{config_id}/cached-models")
async def get_cached_models(config_id: str):
    """Get cached models for a config without fetching from API."""
    import json
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT cached_models, updated_at FROM llm_configs WHERE id = ?", (config_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Config not found")
            
            cached_models_str = row["cached_models"] if "cached_models" in row.keys() else "[]"
            try:
                models = json.loads(cached_models_str) if cached_models_str else []
            except json.JSONDecodeError:
                models = []
            
            return {"models": models, "cached_at": row["updated_at"]}


@router.get("/llm/active")
async def get_active_config():
    """Get the currently active LLM configuration."""
    import json
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM llm_configs WHERE is_active = 1") as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            # Parse cached_models if available
            cached_models_str = row["cached_models"] if "cached_models" in row.keys() else "[]"
            try:
                cached_models = json.loads(cached_models_str) if cached_models_str else []
            except json.JSONDecodeError:
                cached_models = []
            
            return LLMConfig(
                id=row["id"],
                name=row["name"],
                base_url=row["base_url"],
                api_key_masked=mask_api_key(decrypt_api_key(row["api_key_encrypted"])),
                default_model=row["default_model"],
                is_active=True,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                cached_models=cached_models,
            )
