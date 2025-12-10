"""
Presets Router - Handles preset configurations for LLM generation
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from config import settings
from utils import save_json, load_json, list_json_files, generate_id

router = APIRouter()


class PromptEntry(BaseModel):
    id: str
    name: str
    content: str
    enabled: bool = True
    depth: int = 0
    role: str = "system"  # system, user, assistant
    position: str = "normal"  # normal, before_char, after_char, post_history, jailbreak
    deletable: bool = True


class Preset(BaseModel):
    id: str
    name: str
    context_length: int = 8192
    max_tokens: int = 2048
    temperature: float = 0.9
    top_k: int = 40
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    # Advanced SillyTavern sampling parameters
    min_p: float = 0.0  # Minimum probability threshold
    repetition_penalty: float = 1.0  # 1.0 = disabled, >1.0 = penalize repetition
    mirostat_mode: int = 0  # 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0
    mirostat_tau: float = 5.0  # Target entropy
    mirostat_eta: float = 0.1  # Learning rate
    tail_free_sampling: float = 1.0  # 1.0 = disabled, <1.0 = enable TFS
    typical_p: float = 1.0  # Typical sampling, 1.0 = disabled
    # Features
    enable_cot: bool = False
    prompt_entries: list[PromptEntry] = []
    created_at: str
    updated_at: str


class PresetCreate(BaseModel):
    name: str
    context_length: int = 8192
    max_tokens: int = 2048
    temperature: float = 0.9
    top_k: int = 40
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    min_p: float = 0.0
    repetition_penalty: float = 1.0
    mirostat_mode: int = 0
    mirostat_tau: float = 5.0
    mirostat_eta: float = 0.1
    tail_free_sampling: float = 1.0
    typical_p: float = 1.0
    enable_cot: bool = False


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    min_p: Optional[float] = None
    repetition_penalty: Optional[float] = None
    mirostat_mode: Optional[int] = None
    mirostat_tau: Optional[float] = None
    mirostat_eta: Optional[float] = None
    tail_free_sampling: Optional[float] = None
    typical_p: Optional[float] = None
    enable_cot: Optional[bool] = None
    prompt_entries: Optional[list[PromptEntry]] = None


def get_preset_path(preset_id: str):
    return settings.data_dir / "presets" / f"{preset_id}.json"


def get_default_entries() -> list[PromptEntry]:
    """Get default SillyTavern-style prompt entries."""
    return [
        PromptEntry(
            id="main_prompt",
            name="Main Prompt",
            content="You are an expert creative writing AI, crafting immersive roleplay experiences. Write detailed, vivid, and engaging prose. Stay in character at all times.",
            enabled=True,
            depth=0,
            role="system",
            position="normal",
            deletable=False,
        ),
        PromptEntry(
            id="world_info_before",
            name="World Info (Before)",
            content="{{wiBefore}}",
            enabled=True,
            depth=1,
            role="system",
            position="before_char",
            deletable=False,
        ),
        PromptEntry(
            id="character",
            name="Character Persona",
            content="{{character}}",
            enabled=True,
            depth=2,
            role="system",
            position="normal",
            deletable=False,
        ),
        PromptEntry(
            id="scenario",
            name="Scenario",
            content="{{scenario}}",
            enabled=True,
            depth=3,
            role="system",
            position="normal",
            deletable=False,
        ),
        PromptEntry(
            id="world_info_after",
            name="World Info (After)",
            content="{{wiAfter}}",
            enabled=True,
            depth=4,
            role="system",
            position="after_char",
            deletable=False,
        ),
        PromptEntry(
            id="chat_history",
            name="Chat History",
            content="{{chatHistory}}",
            enabled=True,
            depth=50,
            role="system",
            position="chat_history",  # Special position marker
            deletable=False,
        ),
        PromptEntry(
            id="post_history",
            name="Post-History Instructions",
            content="[Continue the roleplay naturally. Maintain character consistency.]",
            enabled=True,
            depth=100,
            role="system",
            position="post_history",
            deletable=False,
        ),
        PromptEntry(
            id="jailbreak",
            name="Jailbreak",
            content="",
            enabled=False,
            depth=999,
            role="system",
            position="jailbreak",
            deletable=False,
        ),
    ]


# Essential entry IDs that must exist in all presets (like SillyTavern's pinned prompts)
ESSENTIAL_ENTRY_IDS = [
    "main_prompt",
    "world_info_before",
    "character",
    "scenario",
    "world_info_after",
    "chat_history",
    "post_history",
    "jailbreak",
]


def ensure_essential_entries(preset_data: dict) -> dict:
    """
    Ensure all essential macro entries exist in a preset.
    Missing entries are injected from defaults (SillyTavern-style pinned prompts).
    User's custom order is preserved.
    """
    if "prompt_entries" not in preset_data:
        preset_data["prompt_entries"] = []
    
    existing_ids = {e.get("id") for e in preset_data["prompt_entries"]}
    default_entries = {e.id: e for e in get_default_entries()}
    
    # Add missing essential entries at the end (preserving existing order)
    for entry_id in ESSENTIAL_ENTRY_IDS:
        if entry_id not in existing_ids and entry_id in default_entries:
            entry = default_entries[entry_id]
            preset_data["prompt_entries"].append(entry.model_dump())
    
    # NOTE: Removed auto-sort by depth to preserve user's custom order
    # User can manually reorder entries via drag-and-drop in the UI
    
    return preset_data


@router.get("/", response_model=list[Preset])
async def list_presets():
    """List all presets with essential entries ensured."""
    presets = await list_json_files(settings.data_dir / "presets")
    return [Preset(**ensure_essential_entries(p)) for p in presets]


@router.get("/{preset_id}", response_model=Preset)
async def get_preset(preset_id: str):
    """Get a specific preset with essential entries ensured."""
    data = await load_json(get_preset_path(preset_id))
    if not data:
        raise HTTPException(status_code=404, detail="Preset not found")
    return Preset(**ensure_essential_entries(data))


@router.post("/", response_model=Preset)
async def create_preset(request: PresetCreate):
    """Create a new preset with default entries."""
    preset_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    preset = Preset(
        id=preset_id,
        name=request.name,
        context_length=request.context_length,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        top_k=request.top_k,
        top_p=request.top_p,
        frequency_penalty=request.frequency_penalty,
        presence_penalty=request.presence_penalty,
        enable_cot=request.enable_cot,
        prompt_entries=get_default_entries(),
        created_at=now,
        updated_at=now,
    )
    
    await save_json(get_preset_path(preset_id), preset.model_dump())
    return preset


@router.put("/{preset_id}", response_model=Preset)
async def update_preset(preset_id: str, update: PresetUpdate):
    """Update a preset."""
    data = await load_json(get_preset_path(preset_id))
    if not data:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    preset = Preset(**data)
    
    # Update fields
    if update.name is not None:
        preset.name = update.name
    if update.context_length is not None:
        preset.context_length = update.context_length
    if update.max_tokens is not None:
        preset.max_tokens = update.max_tokens
    if update.temperature is not None:
        preset.temperature = update.temperature
    if update.top_k is not None:
        preset.top_k = update.top_k
    if update.top_p is not None:
        preset.top_p = update.top_p
    if update.frequency_penalty is not None:
        preset.frequency_penalty = update.frequency_penalty
    if update.presence_penalty is not None:
        preset.presence_penalty = update.presence_penalty
    if update.enable_cot is not None:
        preset.enable_cot = update.enable_cot
    if update.prompt_entries is not None:
        # Ensure non-deletable entries are preserved
        non_deletable = {e.id for e in get_default_entries()}
        new_entries = []
        
        for entry in update.prompt_entries:
            if entry.id in non_deletable:
                entry.deletable = False
            new_entries.append(entry)
        
        preset.prompt_entries = new_entries
    
    preset.updated_at = datetime.utcnow().isoformat()
    await save_json(get_preset_path(preset_id), preset.model_dump())
    return preset


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str):
    """Delete a preset."""
    path = get_preset_path(preset_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preset not found")
    path.unlink()
    return {"status": "deleted"}


@router.post("/{preset_id}/reset-entries", response_model=Preset)
async def reset_entries(preset_id: str):
    """Reset preset entries to SillyTavern defaults."""
    data = await load_json(get_preset_path(preset_id))
    if not data:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    preset = Preset(**data)
    preset.prompt_entries = get_default_entries()
    preset.updated_at = datetime.utcnow().isoformat()
    
    await save_json(get_preset_path(preset_id), preset.model_dump())
    return preset


@router.post("/{preset_id}/entries", response_model=Preset)
async def add_entry(preset_id: str, entry: PromptEntry):
    """Add a new entry to a preset."""
    data = await load_json(get_preset_path(preset_id))
    if not data:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    preset = Preset(**data)
    
    # Generate ID if not provided
    if not entry.id:
        entry.id = generate_id()
    
    entry.deletable = True  # New entries are always deletable
    preset.prompt_entries.append(entry)
    preset.updated_at = datetime.utcnow().isoformat()
    
    await save_json(get_preset_path(preset_id), preset.model_dump())
    return preset


@router.delete("/{preset_id}/entries/{entry_id}")
async def delete_entry(preset_id: str, entry_id: str):
    """Delete an entry from a preset."""
    data = await load_json(get_preset_path(preset_id))
    if not data:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    preset = Preset(**data)
    
    # Find and remove entry
    for i, entry in enumerate(preset.prompt_entries):
        if entry.id == entry_id:
            if not entry.deletable:
                raise HTTPException(status_code=400, detail="Cannot delete non-deletable entry")
            preset.prompt_entries.pop(i)
            break
    else:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    preset.updated_at = datetime.utcnow().isoformat()
    await save_json(get_preset_path(preset_id), preset.model_dump())
    return {"status": "deleted"}


@router.get("/{preset_id}/export")
async def export_sillytavern_preset(preset_id: str):
    """Export preset in SillyTavern TextGen Settings format."""
    data = await load_json(get_preset_path(preset_id))
    if not data:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    preset = Preset(**data)
    
    # Convert to SillyTavern TextGen format
    return {
        "preset_name": preset.name,
        "temp": preset.temperature,
        "top_p": preset.top_p,
        "top_k": preset.top_k,
        "min_p": preset.min_p,
        "rep_pen": preset.repetition_penalty,
        "rep_pen_range": 1024,  # Default
        "typical_p": preset.typical_p,
        "tfs": preset.tail_free_sampling,
        "mirostat_mode": preset.mirostat_mode,
        "mirostat_tau": preset.mirostat_tau,
        "mirostat_eta": preset.mirostat_eta,
        "max_tokens": preset.max_tokens,
        "frequency_penalty": preset.frequency_penalty,
        "presence_penalty": preset.presence_penalty,
    }


@router.post("/import")
async def import_sillytavern_preset(data: dict):
    """Import a preset from SillyTavern TextGen Settings format."""
    preset_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    # Import prompt entries from SillyTavern's "prompts" array
    prompt_entries = []
    st_prompts = data.get("prompts", [])
    
    if st_prompts:
        for i, p in enumerate(st_prompts):
            # Skip marker entries that have no content
            if p.get("marker", False) and not p.get("content"):
                continue
            
            # Map injection_position to our position
            inj_pos = p.get("injection_position", 0)
            position = "after_char" if inj_pos == 1 else "normal"
            
            entry = PromptEntry(
                id=p.get("identifier", generate_id()),
                name=p.get("name", f"Prompt {i+1}"),
                content=p.get("content", ""),
                enabled=p.get("enabled", p.get("system_prompt", True)),
                depth=p.get("injection_depth", 4),
                role=p.get("role", "system"),
                position=position,
                deletable=not p.get("forbid_overrides", False),
            )
            prompt_entries.append(entry)
    
    # If no prompts found, use defaults
    if not prompt_entries:
        prompt_entries = get_default_entries()
    
    preset = Preset(
        id=preset_id,
        name=data.get("preset_name", data.get("name", "Imported Preset")),
        context_length=data.get("openai_max_context", data.get("context_length", 8192)),
        max_tokens=data.get("openai_max_tokens", data.get("max_tokens", 2048)),
        temperature=data.get("temperature", data.get("temp", 0.9)),
        top_k=data.get("top_k", 40),
        top_p=data.get("top_p", 0.95),
        frequency_penalty=data.get("frequency_penalty", data.get("freq_pen", 0.0)),
        presence_penalty=data.get("presence_penalty", data.get("presence_pen", 0.0)),
        min_p=data.get("min_p", 0.0),
        repetition_penalty=data.get("repetition_penalty", data.get("rep_pen", 1.0)),
        mirostat_mode=data.get("mirostat_mode", 0),
        mirostat_tau=data.get("mirostat_tau", 5.0),
        mirostat_eta=data.get("mirostat_eta", 0.1),
        tail_free_sampling=data.get("tfs", data.get("tail_free_sampling", 1.0)),
        typical_p=data.get("typical_p", 1.0),
        prompt_entries=prompt_entries,
        created_at=now,
        updated_at=now,
    )
    
    await save_json(get_preset_path(preset_id), preset.model_dump())
    return preset

