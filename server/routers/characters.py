"""
Characters Router - Handles character card management
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import json
import base64
import aiosqlite
from PIL import Image
import io

from config import settings
from utils import save_json, load_json, list_json_files, generate_id

router = APIRouter()
DATABASE_PATH = settings.data_dir / "deeprp.db"


class CharacterData(BaseModel):
    name: str
    description: str = ""
    personality: str = ""
    scenario: str = ""
    first_mes: str = ""
    mes_example: str = ""
    creator_notes: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    alternate_greetings: list[str] = []
    tags: list[str] = []
    creator: str = ""
    character_version: str = "1.0"


class CharacterExtensions(BaseModel):
    worldbook_id: Optional[str] = None
    tts_voice_id: Optional[str] = None


class Character(BaseModel):
    id: str
    spec: str = "chara_card_v2"
    spec_version: str = "2.0"
    data: CharacterData
    extensions: CharacterExtensions = CharacterExtensions()
    avatar_url: Optional[str] = None
    created_at: str
    updated_at: str


class CharacterCreate(BaseModel):
    name: str
    description: str = ""
    personality: str = ""
    scenario: str = ""
    first_mes: str = ""
    mes_example: str = ""
    creator_notes: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    alternate_greetings: list[str] = []
    tags: list[str] = []
    creator: str = ""
    worldbook_id: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    scenario: Optional[str] = None
    first_mes: Optional[str] = None
    mes_example: Optional[str] = None
    creator_notes: Optional[str] = None
    system_prompt: Optional[str] = None
    post_history_instructions: Optional[str] = None
    alternate_greetings: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    creator: Optional[str] = None
    worldbook_id: Optional[str] = None
    tts_voice_id: Optional[str] = None


def get_character_path(character_id: str):
    return settings.data_dir / "characters" / f"{character_id}.json"


def get_avatar_path(character_id: str):
    return settings.data_dir / "characters" / f"{character_id}.png"


@router.get("/", response_model=list[Character])
async def list_characters():
    """List all characters."""
    characters = await list_json_files(settings.data_dir / "characters")
    return [Character(**c) for c in characters]


@router.get("/{character_id}", response_model=Character)
async def get_character(character_id: str):
    """Get a specific character."""
    data = await load_json(get_character_path(character_id))
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    return Character(**data)


@router.post("/", response_model=Character)
async def create_character(request: CharacterCreate):
    """Create a new character."""
    character_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    character = Character(
        id=character_id,
        data=CharacterData(
            name=request.name,
            description=request.description,
            personality=request.personality,
            scenario=request.scenario,
            first_mes=request.first_mes,
            mes_example=request.mes_example,
            creator_notes=request.creator_notes,
            system_prompt=request.system_prompt,
            post_history_instructions=request.post_history_instructions,
            alternate_greetings=request.alternate_greetings,
            tags=request.tags,
            creator=request.creator,
        ),
        extensions=CharacterExtensions(worldbook_id=request.worldbook_id),
        created_at=now,
        updated_at=now,
    )
    
    await save_json(get_character_path(character_id), character.model_dump())
    return character


@router.put("/{character_id}", response_model=Character)
async def update_character(character_id: str, update: CharacterUpdate):
    """Update a character."""
    data = await load_json(get_character_path(character_id))
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    
    character = Character(**data)
    
    # Update data fields
    if update.name is not None:
        character.data.name = update.name
    if update.description is not None:
        character.data.description = update.description
    if update.personality is not None:
        character.data.personality = update.personality
    if update.scenario is not None:
        character.data.scenario = update.scenario
    if update.first_mes is not None:
        character.data.first_mes = update.first_mes
    if update.mes_example is not None:
        character.data.mes_example = update.mes_example
    if update.creator_notes is not None:
        character.data.creator_notes = update.creator_notes
    if update.system_prompt is not None:
        character.data.system_prompt = update.system_prompt
    if update.post_history_instructions is not None:
        character.data.post_history_instructions = update.post_history_instructions
    if update.alternate_greetings is not None:
        character.data.alternate_greetings = update.alternate_greetings
    if update.tags is not None:
        character.data.tags = update.tags
    if update.creator is not None:
        character.data.creator = update.creator
    
    # Update extensions
    if update.worldbook_id is not None:
        character.extensions.worldbook_id = update.worldbook_id
    if update.tts_voice_id is not None:
        character.extensions.tts_voice_id = update.tts_voice_id
    
    character.updated_at = datetime.utcnow().isoformat()
    await save_json(get_character_path(character_id), character.model_dump())
    return character


@router.delete("/{character_id}")
async def delete_character(character_id: str):
    """Delete a character."""
    path = get_character_path(character_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Character not found")
    
    path.unlink()
    
    # Also delete avatar if exists
    avatar_path = get_avatar_path(character_id)
    if avatar_path.exists():
        avatar_path.unlink()
    
    return {"status": "deleted"}


@router.post("/{character_id}/avatar")
async def upload_avatar(character_id: str, file: UploadFile = File(...)):
    """Upload a character avatar."""
    data = await load_json(get_character_path(character_id))
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Read and save avatar
    content = await file.read()
    avatar_path = get_avatar_path(character_id)
    
    # Resize if needed (max 512x512)
    img = Image.open(io.BytesIO(content))
    img.thumbnail((512, 512), Image.Resampling.LANCZOS)
    img.save(avatar_path, "PNG")
    
    # Update character with avatar URL
    character = Character(**data)
    character.avatar_url = f"/api/characters/{character_id}/avatar"
    character.updated_at = datetime.utcnow().isoformat()
    await save_json(get_character_path(character_id), character.model_dump())
    
    return {"status": "uploaded", "url": character.avatar_url}


@router.get("/{character_id}/avatar")
async def get_avatar(character_id: str):
    """Get a character's avatar."""
    avatar_path = get_avatar_path(character_id)
    if not avatar_path.exists():
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(avatar_path, media_type="image/png")


@router.post("/import")
async def import_character(file: UploadFile = File(...)):
    """Import a character from a SillyTavern-format PNG or JSON file."""
    content = await file.read()
    character_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    char_data = None
    
    if file.filename.endswith(".json"):
        # Direct JSON import
        char_data = json.loads(content.decode())
    elif file.filename.endswith(".png"):
        # Extract JSON from PNG metadata
        try:
            img = Image.open(io.BytesIO(content))
            
            # Try to get character data from tEXt chunk
            if hasattr(img, 'info') and 'chara' in img.info:
                encoded = img.info['chara']
                char_data = json.loads(base64.b64decode(encoded).decode())
            elif hasattr(img, 'text') and 'chara' in img.text:
                encoded = img.text['chara']
                char_data = json.loads(base64.b64decode(encoded).decode())
            
            # Save avatar
            img.save(get_avatar_path(character_id), "PNG")
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PNG: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    if not char_data:
        raise HTTPException(status_code=400, detail="No character data found in file")
    
    # Handle different format versions
    if "data" in char_data:
        # V2 format
        data = char_data["data"]
    else:
        # V1 format
        data = char_data
    
    # Extract embedded worldbook if present
    embedded_worldbook_id = None
    character_book = data.get("character_book")
    if character_book and character_book.get("entries"):
        # Create a worldbook from embedded data
        worldbook_id = generate_id()
        worldbook_entries = []
        
        for entry in character_book.get("entries", []):
            # SillyTavern stores position as number in extensions.position
            ext = entry.get("extensions", {})
            st_position = ext.get("position", entry.get("position", 0))
            # Map: 0=before_char, 1=after_char (at_depth), 4=after_char (at_end)
            position = "after_char" if st_position in [1, 4] else "before_char"
            
            worldbook_entries.append({
                "id": generate_id(),
                "key": entry.get("keys", entry.get("key", [])),
                "secondary_key": entry.get("secondary_keys", []),
                "content": entry.get("content", ""),
                "enabled": entry.get("enabled", True),
                "constant": entry.get("constant", False),
                "scan_depth": ext.get("scan_depth") or ext.get("depth") or 5,
                "order": entry.get("insertion_order", 100),
                "position": position,
                "recursive": not ext.get("exclude_recursion", False),
                "inclusion_group": ext.get("group", ""),
            })
        
        worldbook_data = {
            "id": worldbook_id,
            "name": f"{data.get('name', 'Unknown')}'s Lorebook",
            "description": character_book.get("description", "Imported from character card"),
            "entries": worldbook_entries,
            "created_at": now,
            "updated_at": now,
        }
        
        await save_json(settings.data_dir / "worldbooks" / f"{worldbook_id}.json", worldbook_data)
        embedded_worldbook_id = worldbook_id
    
    character = Character(
        id=character_id,
        spec=char_data.get("spec", "chara_card_v2"),
        spec_version=char_data.get("spec_version", "2.0"),
        data=CharacterData(
            name=data.get("name", data.get("char_name", "Unknown")),
            description=data.get("description", data.get("char_persona", "")),
            personality=data.get("personality", ""),
            scenario=data.get("scenario", data.get("world_scenario", "")),
            first_mes=data.get("first_mes", data.get("char_greeting", "")),
            mes_example=data.get("mes_example", data.get("example_dialogue", "")),
            creator_notes=data.get("creator_notes", ""),
            system_prompt=data.get("system_prompt", ""),
            post_history_instructions=data.get("post_history_instructions", ""),
            alternate_greetings=data.get("alternate_greetings", []),
            tags=data.get("tags", []),
            creator=data.get("creator", ""),
            character_version=data.get("character_version", "1.0"),
        ),
        extensions=CharacterExtensions(
            worldbook_id=embedded_worldbook_id,
        ),
        avatar_url=f"/api/characters/{character_id}/avatar" if get_avatar_path(character_id).exists() else None,
        created_at=now,
        updated_at=now,
    )
    
    await save_json(get_character_path(character_id), character.model_dump())
    
    # Extract embedded regex scripts from extensions
    imported_regex_count = 0
    extensions = data.get("extensions", {})
    regex_scripts = extensions.get("regex_scripts", [])
    
    if regex_scripts:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            for i, script in enumerate(regex_scripts):
                script_id = generate_id()
                
                # Map placement array to affect_display/affect_prompt
                placement = script.get("placement", [])
                affect_display = 1 in placement or 2 in placement
                affect_prompt = script.get("promptOnly", False) or 2 in placement
                
                await db.execute(
                    """
                    INSERT INTO regex_scripts 
                    (id, name, enabled, find_regex, replace_with, affect_display, affect_prompt,
                     min_depth, max_depth, flags, order_index, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (script_id, 
                     script.get("scriptName", f"Imported Script {i+1}"),
                     0 if script.get("disabled", False) else 1,
                     script.get("findRegex", ""),
                     script.get("replaceString", ""),
                     1 if affect_display else 0,
                     1 if affect_prompt else 0,
                     script.get("minDepth") if script.get("minDepth") is not None else 0,
                     script.get("maxDepth") if script.get("maxDepth") is not None else -1,
                     "g",
                     i,
                     now, now)
                )
                imported_regex_count += 1
            
            await db.commit()
    
    # Get linked worldbook name (reference only, not imported)
    linked_worldbook_name = extensions.get("world", None)
    
    # Return with info about what was imported
    result = character.model_dump()
    if embedded_worldbook_id:
        result["imported_worldbook_id"] = embedded_worldbook_id
    if imported_regex_count > 0:
        result["imported_regex_count"] = imported_regex_count
    if linked_worldbook_name:
        result["linked_worldbook_name"] = linked_worldbook_name
    
    return result


@router.get("/{character_id}/export")
async def export_character(character_id: str, format: str = "json"):
    """Export a character in SillyTavern-compatible format."""
    data = await load_json(get_character_path(character_id))
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    
    character = Character(**data)
    
    if format == "json":
        # Return as JSON
        export_data = {
            "spec": character.spec,
            "spec_version": character.spec_version,
            "data": character.data.model_dump()
        }
        return export_data
    elif format == "png":
        # Embed in PNG
        avatar_path = get_avatar_path(character_id)
        
        if avatar_path.exists():
            img = Image.open(avatar_path)
        else:
            # Create default avatar
            img = Image.new('RGB', (512, 512), color=(50, 50, 50))
        
        # Add character data as PNG metadata
        from PIL import PngImagePlugin
        meta = PngImagePlugin.PngInfo()
        char_json = json.dumps({
            "spec": character.spec,
            "spec_version": character.spec_version,
            "data": character.data.model_dump()
        })
        meta.add_text("chara", base64.b64encode(char_json.encode()).decode())
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", pnginfo=meta)
        buffer.seek(0)
        
        return FileResponse(
            buffer,
            media_type="image/png",
            filename=f"{character.data.name}.png"
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
