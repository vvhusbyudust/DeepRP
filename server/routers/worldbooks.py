"""
World Books Router - Handles world book/lorebook management
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from config import settings
from utils import save_json, load_json, list_json_files, generate_id

router = APIRouter()


class WorldBookEntry(BaseModel):
    id: str
    key: list[str] = []  # Primary keywords
    secondary_key: list[str] = []  # Secondary keywords (AND logic)
    content: str
    enabled: bool = True
    constant: bool = False  # Always active
    scan_depth: int = 5  # How many messages to scan
    order: int = 100  # Priority order (lower = higher priority)
    position: str = "before_char"  # before_char, after_char, at_depth
    depth: int = 0  # Insertion depth (0 = system prompt, N = N messages from bottom)
    role: str = "system"  # Role for depth insertion: system, user, assistant
    recursive: bool = False  # Enable recursive activation (content triggers other entries)
    inclusion_group: str = ""  # Group name for mutual exclusivity
    # NEW: SillyTavern compatibility fields
    case_sensitive: bool = False  # Case-sensitive keyword matching
    match_whole_words: bool = False  # Match whole words only
    probability: int = 100  # Trigger probability (0-100)
    use_probability: bool = False  # Enable probability check
    selective_logic: str = "and"  # and, or, not - logic for secondary keys
    comment: str = ""  # Entry title/name (ST compatibility)


class WorldBook(BaseModel):
    id: str
    name: str
    description: str = ""
    entries: list[WorldBookEntry] = []
    scan_depth: int = 2  # Global default scan depth
    recursive_scanning: bool = True  # Enable recursive scanning globally
    created_at: str
    updated_at: str


class WorldBookCreate(BaseModel):
    name: str
    description: str = ""


class WorldBookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entries: Optional[list[WorldBookEntry]] = None
    scan_depth: Optional[int] = None
    recursive_scanning: Optional[bool] = None


class WorldBookEntryCreate(BaseModel):
    key: list[str] = []
    secondary_key: list[str] = []
    content: str
    enabled: bool = True
    constant: bool = False
    scan_depth: int = 5
    order: int = 100
    position: str = "before_char"
    depth: int = 0  # Insertion depth for at_depth position
    role: str = "system"  # Role for depth insertion
    recursive: bool = False
    inclusion_group: str = ""
    # NEW: SillyTavern compatibility fields
    case_sensitive: bool = False
    match_whole_words: bool = False
    probability: int = 100
    use_probability: bool = False
    selective_logic: str = "and"
    comment: str = ""


def get_worldbook_path(worldbook_id: str):
    return settings.data_dir / "worldbooks" / f"{worldbook_id}.json"


@router.get("/", response_model=list[WorldBook])
async def list_worldbooks():
    """List all world books."""
    worldbooks = await list_json_files(settings.data_dir / "worldbooks")
    return [WorldBook(**wb) for wb in worldbooks]


@router.get("/{worldbook_id}", response_model=WorldBook)
async def get_worldbook(worldbook_id: str):
    """Get a specific world book."""
    data = await load_json(get_worldbook_path(worldbook_id))
    if not data:
        raise HTTPException(status_code=404, detail="World book not found")
    return WorldBook(**data)


@router.post("/", response_model=WorldBook)
async def create_worldbook(request: WorldBookCreate):
    """Create a new world book."""
    worldbook_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    worldbook = WorldBook(
        id=worldbook_id,
        name=request.name,
        description=request.description,
        entries=[],
        created_at=now,
        updated_at=now,
    )
    
    await save_json(get_worldbook_path(worldbook_id), worldbook.model_dump())
    return worldbook


@router.put("/{worldbook_id}", response_model=WorldBook)
async def update_worldbook(worldbook_id: str, update: WorldBookUpdate):
    """Update a world book."""
    data = await load_json(get_worldbook_path(worldbook_id))
    if not data:
        raise HTTPException(status_code=404, detail="World book not found")
    
    worldbook = WorldBook(**data)
    
    if update.name is not None:
        worldbook.name = update.name
    if update.description is not None:
        worldbook.description = update.description
    if update.entries is not None:
        worldbook.entries = update.entries
    
    worldbook.updated_at = datetime.utcnow().isoformat()
    await save_json(get_worldbook_path(worldbook_id), worldbook.model_dump())
    return worldbook


@router.delete("/{worldbook_id}")
async def delete_worldbook(worldbook_id: str):
    """Delete a world book."""
    path = get_worldbook_path(worldbook_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="World book not found")
    path.unlink()
    return {"status": "deleted"}


@router.post("/{worldbook_id}/entries", response_model=WorldBook)
async def add_entry(worldbook_id: str, entry: WorldBookEntryCreate):
    """Add a new entry to a world book."""
    data = await load_json(get_worldbook_path(worldbook_id))
    if not data:
        raise HTTPException(status_code=404, detail="World book not found")
    
    worldbook = WorldBook(**data)
    
    new_entry = WorldBookEntry(
        id=generate_id(),
        key=entry.key,
        secondary_key=entry.secondary_key,
        content=entry.content,
        enabled=entry.enabled,
        constant=entry.constant,
        scan_depth=entry.scan_depth,
        order=entry.order,
        position=entry.position,
        depth=entry.depth,
        role=entry.role,
        recursive=entry.recursive,
        inclusion_group=entry.inclusion_group,
        # SillyTavern compatibility fields
        case_sensitive=entry.case_sensitive,
        match_whole_words=entry.match_whole_words,
        probability=entry.probability,
        use_probability=entry.use_probability,
        selective_logic=entry.selective_logic,
        comment=entry.comment,
    )
    
    worldbook.entries.append(new_entry)
    worldbook.updated_at = datetime.utcnow().isoformat()
    
    await save_json(get_worldbook_path(worldbook_id), worldbook.model_dump())
    return worldbook


@router.put("/{worldbook_id}/entries/{entry_id}", response_model=WorldBook)
async def update_entry(worldbook_id: str, entry_id: str, update: WorldBookEntryCreate):
    """Update an entry in a world book."""
    data = await load_json(get_worldbook_path(worldbook_id))
    if not data:
        raise HTTPException(status_code=404, detail="World book not found")
    
    worldbook = WorldBook(**data)
    
    for i, entry in enumerate(worldbook.entries):
        if entry.id == entry_id:
            worldbook.entries[i] = WorldBookEntry(
                id=entry_id,
                key=update.key,
                secondary_key=update.secondary_key,
                content=update.content,
                enabled=update.enabled,
                constant=update.constant,
                scan_depth=update.scan_depth,
                order=update.order,
                position=update.position,
                depth=update.depth,
                role=update.role,
                recursive=update.recursive,
                inclusion_group=update.inclusion_group,
                # SillyTavern compatibility fields
                case_sensitive=update.case_sensitive,
                match_whole_words=update.match_whole_words,
                probability=update.probability,
                use_probability=update.use_probability,
                selective_logic=update.selective_logic,
                comment=update.comment,
            )
            break
    else:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    worldbook.updated_at = datetime.utcnow().isoformat()
    await save_json(get_worldbook_path(worldbook_id), worldbook.model_dump())
    return worldbook


@router.delete("/{worldbook_id}/entries/{entry_id}")
async def delete_entry(worldbook_id: str, entry_id: str):
    """Delete an entry from a world book."""
    data = await load_json(get_worldbook_path(worldbook_id))
    if not data:
        raise HTTPException(status_code=404, detail="World book not found")
    
    worldbook = WorldBook(**data)
    
    for i, entry in enumerate(worldbook.entries):
        if entry.id == entry_id:
            worldbook.entries.pop(i)
            break
    else:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    worldbook.updated_at = datetime.utcnow().isoformat()
    await save_json(get_worldbook_path(worldbook_id), worldbook.model_dump())
    return {"status": "deleted"}


@router.post("/{worldbook_id}/import")
async def import_sillytavern_worldbook(worldbook_id: str, data: dict):
    """Import a SillyTavern format world book."""
    # Handle SillyTavern JSON format
    entries = []
    
    if "entries" in data:
        for key, entry in data["entries"].items():
            entries.append(WorldBookEntry(
                id=generate_id(),
                key=entry.get("key", []) if isinstance(entry.get("key"), list) else [entry.get("key", "")],
                secondary_key=entry.get("secondary_keys", []),
                content=entry.get("content", ""),
                enabled=not entry.get("disable", False),
                constant=entry.get("constant", False),
                scan_depth=entry.get("scanDepth", 5),
                order=entry.get("order", 100),
                position=entry.get("position", "before_char"),
            ))
    
    path = get_worldbook_path(worldbook_id)
    if path.exists():
        existing = await load_json(path)
        worldbook = WorldBook(**existing)
        worldbook.entries.extend(entries)
    else:
        worldbook = WorldBook(
            id=worldbook_id,
            name=data.get("name", "Imported World Book"),
            description=data.get("description", ""),
            entries=entries,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
    
    worldbook.updated_at = datetime.utcnow().isoformat()
    await save_json(path, worldbook.model_dump())
    return worldbook


@router.get("/{worldbook_id}/export")
async def export_sillytavern_worldbook(worldbook_id: str):
    """Export world book in SillyTavern-compatible format."""
    data = await load_json(get_worldbook_path(worldbook_id))
    if not data:
        raise HTTPException(status_code=404, detail="World book not found")
    
    worldbook = WorldBook(**data)
    
    # Convert to SillyTavern format
    st_entries = {}
    for i, entry in enumerate(worldbook.entries):
        # Map position: before_char=0, after_char=1, at_depth=6
        if entry.position == "at_depth":
            st_position = 6  # @ D
        elif entry.position == "after_char":
            st_position = 1  # After Char Defs
        else:
            st_position = 0  # Before Char Defs
        
        # Map role: system=0, user=1, assistant=2
        role_map = {"system": 0, "user": 1, "assistant": 2}
        st_role = role_map.get(entry.role, 0)
        
        st_entries[str(i)] = {
            "uid": i,
            "key": entry.key,
            "keysecondary": entry.secondary_key,
            "comment": entry.id,  # Use ID as comment/title
            "content": entry.content,
            "constant": entry.constant,
            "selective": len(entry.secondary_key) > 0,
            "selectiveLogic": 0,  # AND logic
            "order": entry.order,
            "position": st_position,
            "depth": entry.depth if entry.position == "at_depth" else 0,
            "role": st_role,
            "disable": not entry.enabled,
            "excludeRecursion": not entry.recursive,
            "probability": 100,
            "group": entry.inclusion_group,
            "scanDepth": entry.scan_depth if entry.scan_depth != 5 else None,
            "caseSensitive": False,
            # Extensions block for newer SillyTavern format
            "extensions": {
                "position": st_position,
                "depth": entry.depth if entry.position == "at_depth" else 0,
                "role": st_role,
                "scan_depth": entry.scan_depth,
                "exclude_recursion": not entry.recursive,
                "group": entry.inclusion_group,
            }
        }
    
    return {
        "entries": st_entries,
        "name": worldbook.name,
        "description": worldbook.description,
    }


@router.post("/import-new")
async def import_new_worldbook(data: dict):
    """Import a new world book from SillyTavern format and create new ID."""
    worldbook_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    entries = []
    raw_entries = data.get("entries", [])
    
    # Handle both dict format (SillyTavern lorebook export) and array format (character card)
    if isinstance(raw_entries, dict):
        entry_list = list(raw_entries.values())
    else:
        entry_list = raw_entries
    
    for entry in entry_list:
        # SillyTavern stores position as number in extensions.position or top-level position
        ext = entry.get("extensions", {})
        st_position = ext.get("position", entry.get("position", 0))
        st_depth = ext.get("depth", entry.get("depth", 0))  # Depth for @ D insertion
        
        # SillyTavern role mapping: 0=system, 1=user, 2=assistant
        st_role = ext.get("role", entry.get("role", 0))
        if isinstance(st_role, int):
            role_map = {0: "system", 1: "user", 2: "assistant"}
            role = role_map.get(st_role, "system")
        else:
            role = st_role if st_role in ["system", "user", "assistant"] else "system"
        
        # Map position: 
        # 0 = Before Char Defs
        # 1 = After Char Defs  
        # 2 = Before Example Messages
        # 3 = After Example Messages
        # 4 = Top of AN
        # 5 = Bottom of AN
        # 6 = @ D (depth-based)
        if isinstance(st_position, str):
            position = st_position  # Already a string like "before_char"
            depth = st_depth
        elif st_position == 6:  # @ D = depth-based insertion
            position = "at_depth"
            depth = st_depth
        elif st_position in [1, 3, 5]:  # After positions
            position = "after_char"
            depth = 0
        else:
            position = "before_char"
            depth = 0
        
        entries.append(WorldBookEntry(
            id=generate_id(),
            key=entry.get("keys", entry.get("key", [])) if isinstance(entry.get("keys", entry.get("key", [])), list) else [entry.get("keys", entry.get("key", ""))],
            secondary_key=entry.get("secondary_keys", entry.get("keysecondary", [])) if isinstance(entry.get("secondary_keys", entry.get("keysecondary", [])), list) else [],
            content=entry.get("content", ""),
            enabled=entry.get("enabled", not entry.get("disable", False)),  # Handle both formats
            constant=entry.get("constant", False),
            scan_depth=ext.get("scan_depth") or entry.get("scanDepth") or 5,
            order=entry.get("insertion_order", entry.get("order", 100)),
            position=position,
            depth=depth,
            role=role,
            recursive=not ext.get("exclude_recursion", entry.get("excludeRecursion", False)),
            inclusion_group=ext.get("group", entry.get("group", "")),
        ))
    
    worldbook = WorldBook(
        id=worldbook_id,
        name=data.get("name", "Imported World Book"),
        description=data.get("description", ""),
        entries=entries,
        created_at=now,
        updated_at=now,
    )
    
    await save_json(get_worldbook_path(worldbook_id), worldbook.model_dump())
    return worldbook
