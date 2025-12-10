"""
Chat Router - Handles chat sessions and streaming responses
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import json
import asyncio

from config import settings
from utils import save_json, load_json, list_json_files, generate_id
from services.llm.stream_handler import stream_completion, get_llm_config
from services.regex import process_for_display, process_for_prompt

router = APIRouter()


async def load_preset(preset_id: str) -> Optional[dict]:
    """Load a preset from file."""
    if not preset_id:
        return None
    path = settings.data_dir / "presets" / f"{preset_id}.json"
    return await load_json(path)


async def load_character(character_id: str) -> Optional[dict]:
    """Load a character from file."""
    if not character_id:
        return None
    path = settings.data_dir / "characters" / f"{character_id}.json"
    return await load_json(path)


async def load_worldbook(worldbook_id: str) -> Optional[dict]:
    """Load a worldbook from file."""
    if not worldbook_id:
        return None
    path = settings.data_dir / "worldbooks" / f"{worldbook_id}.json"
    return await load_json(path)


async def load_worldbooks(worldbook_ids: list[str]) -> Optional[dict]:
    """
    Load multiple worldbooks and combine them into a single virtual worldbook.
    Entries from all worldbooks are combined and sorted by order (priority).
    """
    print(f"[Worldbook] load_worldbooks called with ids: {worldbook_ids}")
    if not worldbook_ids:
        print(f"[Worldbook] No worldbook_ids provided")
        return None
    
    combined_entries = []
    global_scan_depth = 2
    global_recursive = True
    
    for wb_id in worldbook_ids:
        wb = await load_worldbook(wb_id)
        if wb:
            print(f"[Worldbook] Loaded {wb.get('name')} with {len(wb.get('entries', []))} entries")
            # Take the minimum scan_depth across all worldbooks
            if wb.get("scan_depth"):
                global_scan_depth = max(global_scan_depth, wb.get("scan_depth", 2))
            if not wb.get("recursive_scanning", True):
                global_recursive = False
            # Add entries from this worldbook
            for entry in wb.get("entries", []):
                if entry.get("enabled", True):
                    combined_entries.append(entry)
        else:
            print(f"[Worldbook] Could not load worldbook {wb_id}")
    
    if not combined_entries:
        print(f"[Worldbook] No enabled entries found")
        return None
    
    print(f"[Worldbook] Combined {len(combined_entries)} enabled entries")
    
    # Sort all entries by order (priority) - lower order = higher priority = earlier insertion
    combined_entries.sort(key=lambda x: x.get("order", 100))
    
    return {
        "id": "combined",
        "name": "Combined Worldbooks",
        "entries": combined_entries,
        "scan_depth": global_scan_depth,
        "recursive_scanning": global_recursive,
    }


def process_macros(
    text: str,
    character: Optional[dict] = None,
    user_name: str = "User",
    user_persona: str = "",
    worldbook_before: str = "",
    worldbook_after: str = "",
    example_messages: str = "",
    chat_history: list = None,  # NEW: for message-related macros
) -> str:
    """
    Process SillyTavern-style macros in text.
    
    Supported macros (case-insensitive):
    - {{char}} / <BOT> - Character's name
    - {{user}} / <USER> - User's name
    - {{description}} - Character description
    - {{personality}} - Character personality
    - {{scenario}} - Scenario text
    - {{persona}} - User's persona description
    - {{wiBefore}} / {{loreBefore}} - World Info entries before character
    - {{wiAfter}} / {{loreAfter}} - World Info entries after character
    - {{mesExamples}} / {{mesExamplesRaw}} - Example messages
    - {{system}} - Character's system prompt
    - {{charPrompt}} - Character's main prompt override
    - {{charJailbreak}} - Character's post-history instructions
    - {{charVersion}} - Character's version
    - {{time}} - Current time
    - {{date}} - Current date
    - {{newline}} - Newline character
    - {{trim}} - Empty string (trims surrounding whitespace)
    - {{noop}} - No operation (empty string)
    - {{lastCharMessage}} - Last character message
    - {{lastUserMessage}} - Last user message
    - {{roll:XdY}} - Dice roll (e.g., {{roll:2d6}})
    - {{random:a,b,c}} - Random selection
    """
    import re
    import random as rand_module
    
    if not text:
        return ""
    
    # Get character data
    char_data = character.get("data", {}) if character else {}
    char_name = char_data.get("name", "Assistant")
    
    # Build character persona for {{character}} macro
    char_persona_parts = []
    if char_data.get("name"):
        char_persona_parts.append(f"Character: {char_data['name']}")
    if char_data.get("description"):
        char_persona_parts.append(char_data["description"])
    if char_data.get("personality"):
        char_persona_parts.append(f"Personality: {char_data['personality']}")
    char_persona = "\n".join(char_persona_parts) if char_persona_parts else ""
    
    # Get last messages from chat history
    chat_history = chat_history or []
    last_char_msg = ""
    last_user_msg = ""
    for msg in reversed(chat_history):
        if msg.get("role") == "assistant" and not last_char_msg:
            last_char_msg = msg.get("content", "")[:500]  # Limit length
        elif msg.get("role") == "user" and not last_user_msg:
            last_user_msg = msg.get("content", "")[:500]
        if last_char_msg and last_user_msg:
            break
    
    # Build replacement map with SillyTavern-compatible macros
    replacements = {
        # Character macros
        "{{char}}": char_name,
        "<BOT>": char_name,  # ST alias
        "{{user}}": user_name,
        "<USER>": user_name,  # ST alias
        "{{description}}": char_data.get("description", ""),
        "{{personality}}": char_data.get("personality", ""),
        "{{scenario}}": char_data.get("scenario", ""),
        "{{persona}}": user_persona,
        "{{system}}": char_data.get("system_prompt", ""),
        "{{first_mes}}": char_data.get("first_mes", ""),
        
        # Character V2 specific macros
        "{{charPrompt}}": char_data.get("system_prompt", ""),  # Main prompt override
        "{{charJailbreak}}": char_data.get("post_history_instructions", ""),  # Post-history
        "{{charVersion}}": char_data.get("character_version", "1.0"),
        
        # World Info macros with SillyTavern aliases
        "{{wiBefore}}": worldbook_before,
        "{{loreBefore}}": worldbook_before,
        "{{wiAfter}}": worldbook_after,
        "{{loreAfter}}": worldbook_after,
        "{{worldbook}}": worldbook_before,
        
        # Example messages with aliases
        "{{mesExamples}}": example_messages or char_data.get("mes_example", ""),
        "{{mesExamplesRaw}}": example_messages or char_data.get("mes_example", ""),
        "{{example_dialogue}}": example_messages or char_data.get("mes_example", ""),
        
        # Date/time macros
        "{{time}}": datetime.now().strftime("%H:%M"),
        "{{date}}": datetime.now().strftime("%Y-%m-%d"),
        "{{weekday}}": datetime.now().strftime("%A"),
        "{{isotime}}": datetime.now().isoformat(),
        
        # Full character card macros
        "{{character}}": char_persona,
        "{{charCard}}": char_persona,
        
        # Utility macros
        "{{newline}}": "\n",
        "{{trim}}": "",  # Will be handled specially
        "{{noop}}": "",
        
        # Message history macros
        "{{lastCharMessage}}": last_char_msg,
        "{{lastUserMessage}}": last_user_msg,
    }
    
    # Apply replacements (case-insensitive)
    result = text
    for macro, value in replacements.items():
        # Case-insensitive replacement using lambda to prevent backslash interpretation
        pattern = re.compile(re.escape(macro), re.IGNORECASE)
        replacement_value = value or ""
        result = pattern.sub(lambda m: replacement_value, result)
    
    # Handle {{trim}} - removes surrounding whitespace
    result = re.sub(r'\s*\{\{trim\}\}\s*', '', result, flags=re.IGNORECASE)
    
    # Handle {{roll:XdY+Z}} dice macro
    def roll_dice(match):
        dice_str = match.group(1)
        try:
            # Parse XdY+Z format
            parts = re.match(r'(\d*)d(\d+)([+-]\d+)?', dice_str, re.IGNORECASE)
            if parts:
                num_dice = int(parts.group(1)) if parts.group(1) else 1
                sides = int(parts.group(2))
                modifier = int(parts.group(3)) if parts.group(3) else 0
                total = sum(rand_module.randint(1, sides) for _ in range(num_dice)) + modifier
                return str(total)
        except:
            pass
        return match.group(0)
    
    result = re.sub(r'\{\{roll:([^}]+)\}\}', roll_dice, result, flags=re.IGNORECASE)
    
    # Handle {{random:a,b,c}} macro
    def random_choice(match):
        options = match.group(1).split(",")
        if options:
            return rand_module.choice(options).strip()
        return ""
    
    result = re.sub(r'\{\{random:([^}]+)\}\}', random_choice, result, flags=re.IGNORECASE)
    
    # Clean up empty sections
    result = result.replace("\n\n\n", "\n\n")
    
    return result.strip()


def scan_worldbook_entries(
    worldbook: dict, 
    messages: list, 
    scan_depth: int = 5,
    max_recursion: int = 3
) -> list[dict]:
    """
    Scan recent messages for worldbook keyword triggers with recursive activation.
    
    SillyTavern-compatible recursive scanning:
    - Keywords in entry content can trigger other entries
    - Inclusion groups handle mutual exclusivity
    - Returns entries sorted by order
    """
    if not worldbook or not worldbook.get("entries"):
        return []
    
    # Use worldbook's global scan_depth if available
    wb_scan_depth = worldbook.get("scan_depth", scan_depth)
    recursive_enabled = worldbook.get("recursive_scanning", True)
    
    # Combine recent messages for scanning
    recent_text = " ".join([
        m.get("content", "") for m in messages[-wb_scan_depth:]
    ]).lower() if wb_scan_depth > 0 else ""
    
    entries = worldbook.get("entries", [])
    triggered = {}  # id -> entry
    inclusion_groups = {}  # group -> best entry
    
    def check_keywords(entry: dict, text: str) -> bool:
        """Check if entry's keywords match in text with ST-compatible options."""
        import re
        import random
        
        keywords = entry.get("key", [])
        secondary = entry.get("secondary_key", [])
        
        # Get ST-compatible options with defaults
        case_sensitive = entry.get("case_sensitive", False)
        match_whole_words = entry.get("match_whole_words", False)
        use_probability = entry.get("use_probability", False)
        probability = entry.get("probability", 100)
        selective_logic = entry.get("selective_logic", "and")  # and, or, not
        
        # Probability check (if enabled)
        if use_probability and probability < 100:
            if random.randint(1, 100) > probability:
                return False
        
        # Prepare text for matching
        search_text = text if case_sensitive else text.lower()
        
        def keyword_matches(kw: str) -> bool:
            """Check if a single keyword matches."""
            if not kw:
                return False
            check_kw = kw if case_sensitive else kw.lower()
            
            if match_whole_words:
                # Use word boundary regex
                pattern = r'\b' + re.escape(check_kw) + r'\b'
                return bool(re.search(pattern, search_text, 0 if case_sensitive else re.IGNORECASE))
            else:
                return check_kw in search_text
        
        # Primary keywords (OR logic) - any one must match
        primary_match = any(keyword_matches(kw) for kw in keywords if kw)
        
        if not primary_match:
            return False
        
        # Secondary keywords with selective logic
        if secondary:
            if selective_logic == "not":
                # NOT logic: none of the secondary keys should match
                secondary_match = not any(keyword_matches(kw) for kw in secondary if kw)
            elif selective_logic == "or":
                # OR logic: any secondary key matches
                secondary_match = any(keyword_matches(kw) for kw in secondary if kw)
            else:
                # AND logic (default): all must match
                secondary_match = all(keyword_matches(kw) for kw in secondary if kw)
            
            return primary_match and secondary_match
        
        return primary_match
    
    def trigger_entry(entry: dict, recursion_level: int = 0):
        """Trigger an entry and handle recursive activation."""
        entry_id = entry.get("id")
        if entry_id in triggered:
            return
        
        # Handle inclusion groups (mutual exclusivity)
        group = entry.get("inclusion_group", "")
        if group:
            if group in inclusion_groups:
                existing = inclusion_groups[group]
                # Keep the one with higher priority (lower order number)
                if entry.get("order", 100) >= existing.get("order", 100):
                    return
                # Remove existing entry from triggered
                del triggered[existing.get("id")]
            inclusion_groups[group] = entry
        
        triggered[entry_id] = entry
        
        # Recursive activation: scan entry content for other entry keywords
        if recursive_enabled and entry.get("recursive", False) and recursion_level < max_recursion:
            entry_content = entry.get("content", "").lower()
            for other_entry in entries:
                if other_entry.get("id") != entry_id and other_entry.get("enabled", True):
                    if check_keywords(other_entry, entry_content):
                        trigger_entry(other_entry, recursion_level + 1)
    
    # First pass: constant entries and direct keyword matches
    for entry in entries:
        if not entry.get("enabled", True):
            continue
        
        entry_name = entry.get("comment", entry.get("id", "unknown"))[:30]
        
        # Constant entries always included
        if entry.get("constant", False):
            print(f"[Worldbook] Entry '{entry_name}' triggered: constant=True")
            trigger_entry(entry)
            continue
        
        # Check keywords in recent messages
        if check_keywords(entry, recent_text):
            keys = entry.get("key", []) or entry.get("keys", [])
            print(f"[Worldbook] Entry '{entry_name}' triggered: keyword match in {keys}")
            trigger_entry(entry)
        else:
            keys = entry.get("key", []) or entry.get("keys", [])
            if keys:
                print(f"[Worldbook] Entry '{entry_name}' NOT triggered: no keyword match for {keys}")
            else:
                print(f"[Worldbook] Entry '{entry_name}' NOT triggered: no keywords defined, constant=False")
    
    # Sort by order and return
    result = sorted(triggered.values(), key=lambda x: x.get("order", 100))
    print(f"[Worldbook] scan_worldbook_entries returning {len(result)} entries")
    return result


def build_system_prompt(
    character: Optional[dict],
    worldbook: Optional[dict],
    preset: Optional[dict],
    messages: list,
    user_name: str = "User",
    user_persona: str = "",
) -> tuple[str, str, list[dict]]:
    """
    Build a SillyTavern-compatible system prompt with macro processing.
    
    Returns a tuple: (pre_history_prompt, post_history_prompt, depth_entries)
    Pre-history: Main Prompt → World Info (Before) → Character → Scenario → World Info (After)
    Post-history: Post-History Instructions → Jailbreak
    
    depth_entries: List of {content, depth, role} dicts for injection into chat history
    This allows proper insertion at specific depths like SillyTavern's @ D feature.
    """
    # Get worldbook entries first (needed for macros)
    wb_before_list = []
    wb_after_list = []
    depth_entries = []  # Entries to inject at specific depths
    
    if worldbook:
        triggered_entries = scan_worldbook_entries(worldbook, messages)
        print(f"[Worldbook] Scanned {len(triggered_entries)} triggered entries from worldbook")
        for entry in triggered_entries:
            content = entry.get("content", "")
            if not content:
                continue
            pos = entry.get("position", "before_char")
            entry_id = entry.get("id", "unknown")[:8]
            is_constant = entry.get("constant", False)
            print(f"[Worldbook] Entry {entry_id} position={pos} constant={is_constant} content_len={len(content)}")
            if pos == "at_depth":
                # Depth-based insertion - to be injected into chat history
                depth_entries.append({
                    "content": content,
                    "depth": entry.get("depth", 0),
                    "role": entry.get("role", "system"),
                    "order": entry.get("order", 100),
                })
            elif pos == "after_char":
                wb_after_list.append(content)
            else:
                wb_before_list.append(content)
    
    # Sort depth entries by depth (ascending) then by order
    depth_entries.sort(key=lambda x: (x["depth"], x["order"]))
    
    wb_before = "\n\n".join(wb_before_list) if wb_before_list else ""
    wb_after = "\n\n".join(wb_after_list) if wb_after_list else ""
    print(f"[Worldbook] Final: wb_before_len={len(wb_before)} wb_after_len={len(wb_after)}")
    
    # Get example messages from character
    char_data = character.get("data", {}) if character else {}
    example_messages = char_data.get("mes_example", "")
    char_name = char_data.get("name", "Assistant")
    
    # Build character persona for {{character}} macro
    char_persona_parts = []
    if char_data.get("name"):
        char_persona_parts.append(f"Character: {char_data['name']}")
    if char_data.get("description"):
        char_persona_parts.append(char_data["description"])
    if char_data.get("personality"):
        char_persona_parts.append(f"Personality: {char_data['personality']}")
    char_persona = "\n".join(char_persona_parts) if char_persona_parts else ""
    
    # Debug: Log worldbook values
    print(f"[Macros] build_system_prompt: wb_before_len={len(wb_before)}, wb_after_len={len(wb_after)}")
    
    # Helper to process macros on any text
    def apply_macros(text: str) -> str:
        result = process_macros(
            text,
            character=character,
            user_name=user_name,
            user_persona=user_persona,
            worldbook_before=wb_before,
            worldbook_after=wb_after,
            example_messages=example_messages,
            chat_history=messages,  # Pass messages for {{lastCharMessage}}, {{lastUserMessage}}
        )
        # Debug: Check for unexpanded macros
        if "{{wi" in text or "{{lore" in text:
            print(f"[Macros] Input has WI macro, wb_before_len={len(wb_before)}, output_len={len(result)}")
        return result
    
    # PURE MACRO-DRIVEN ASSEMBLY
    # Process all preset entries by position, macros are expanded inline
    # No hardcoded character/worldbook insertion - it's all controlled by macros in the preset
    
    pre_history_parts = []  # Everything before chat history
    post_history_parts = [] # Everything after chat history (post_history + jailbreak)
    
    if preset and preset.get("prompt_entries"):
        # Sort entries by depth for proper ordering
        sorted_entries = sorted(preset.get("prompt_entries", []), key=lambda x: x.get("depth", 0))
        print(f"[Preset] Processing {len(sorted_entries)} entries from preset '{preset.get('name', 'unknown')}'")
        
        for entry in sorted_entries:
            entry_name = entry.get("name", entry.get("id", "unknown"))
            
            if not entry.get("enabled", True):
                print(f"[Preset] Entry '{entry_name}': SKIPPED (disabled)")
                continue
            
            raw_content = entry.get("content", "")
            if not raw_content:
                print(f"[Preset] Entry '{entry_name}': SKIPPED (empty content)")
                continue
                
            # Skip the chat history marker - it's just a position indicator
            if entry.get("position") == "chat_history" or "{{chatHistory}}" in raw_content:
                print(f"[Preset] Entry '{entry_name}': SKIPPED (chat_history marker)")
                continue
            
            # Apply macros to expand {{char}}, {{wiBefore}}, {{character}}, etc.
            content = apply_macros(raw_content)
            
            # Debug logging - show what macros were in input and what remained
            if "{{" in raw_content:
                import re
                input_macros = re.findall(r'\{\{[^}]+\}\}', raw_content)
                output_macros = re.findall(r'\{\{[^}]+\}\}', content) if content else []
                print(f"[Macros] Entry '{entry_name}': input_macros={input_macros}, output_macros={output_macros}")
                print(f"[Macros] Entry '{entry_name}': raw_len={len(raw_content)}, result_len={len(content)}")
            
            # Skip entries that become empty after macro expansion
            if not content.strip():
                print(f"[Preset] Entry '{entry_name}': SKIPPED (empty after expansion)")
                continue
            
            # Place content based on position
            pos = entry.get("position", "normal")
            if pos in ("post_history", "jailbreak"):
                post_history_parts.append(content)
                print(f"[Preset] Entry '{entry_name}': added to POST_HISTORY (len={len(content)})")
            else:
                # normal, before_char, after_char all go to pre-history
                pre_history_parts.append(content)
                print(f"[Preset] Entry '{entry_name}': added to PRE_HISTORY (len={len(content)})")
    else:
        print(f"[Preset] No preset or no prompt_entries found!")
    
    pre_history_prompt = "\n\n".join(filter(None, pre_history_parts))
    post_history_prompt = "\n\n".join(filter(None, post_history_parts))
    
    print(f"[Prompt] Final: pre_history_len={len(pre_history_prompt)}, post_history_len={len(post_history_prompt)}, depth_entries={len(depth_entries)}")
    
    return (pre_history_prompt, post_history_prompt, depth_entries)



class Message(BaseModel):
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None


class ChatSession(BaseModel):
    id: str
    character_id: Optional[str] = None
    character_name: Optional[str] = None  # For display purposes
    worldbook_ids: list[str] = []  # Support multiple worldbooks
    preset_id: Optional[str] = None
    messages: list[Message] = []
    created_at: str
    updated_at: str


class ChatSessionCreate(BaseModel):
    character_id: Optional[str] = None
    worldbook_ids: list[str] = []  # Support multiple worldbooks
    preset_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., max_length=50000)  # Max 50k chars
    session_id: str = Field(..., max_length=100)


def get_session_path(session_id: str):
    return settings.data_dir / "chats" / f"{session_id}.json"


@router.get("/sessions", response_model=list[ChatSession])
async def list_sessions():
    """List all chat sessions with backwards compatibility."""
    sessions = await list_json_files(settings.data_dir / "chats")
    result = []
    for s in sessions:
        # Migrate old worldbook_id to worldbook_ids if needed
        if "worldbook_id" in s and "worldbook_ids" not in s:
            s["worldbook_ids"] = [s["worldbook_id"]] if s["worldbook_id"] else []
        elif "worldbook_ids" not in s:
            s["worldbook_ids"] = []
        result.append(ChatSession(**s))
    return result


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(session_id: str):
    """Get a specific chat session with backwards compatibility."""
    data = await load_json(get_session_path(session_id))
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    # Migrate old worldbook_id to worldbook_ids if needed
    if "worldbook_id" in data and "worldbook_ids" not in data:
        data["worldbook_ids"] = [data["worldbook_id"]] if data["worldbook_id"] else []
    elif "worldbook_ids" not in data:
        data["worldbook_ids"] = []
    return ChatSession(**data)


@router.post("/sessions", response_model=ChatSession)
async def create_session(request: ChatSessionCreate):
    """Create a new chat session."""
    session_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    # Load character to get name and first message
    character = await load_character(request.character_id)
    character_name = character.get("data", {}).get("name") if character else None
    
    # Build initial messages - if character has a first_mes, add it as assistant greeting
    initial_messages = []
    if character:
        char_data = character.get("data", {})
        first_mes = char_data.get("first_mes", "")
        if first_mes:
            # Expand basic macros in first_mes ({{char}}, {{user}})
            expanded_first_mes = first_mes.replace("{{char}}", char_data.get("name", "Assistant"))
            expanded_first_mes = expanded_first_mes.replace("{{user}}", "User")
            
            greeting = Message(
                id=generate_id(),
                role="assistant",
                content=expanded_first_mes,
                timestamp=now,
            )
            initial_messages.append(greeting)
            print(f"[Chat] Added first_mes from character '{character_name}' (len={len(expanded_first_mes)})")
    
    session = ChatSession(
        id=session_id,
        character_id=request.character_id,
        character_name=character_name,
        worldbook_ids=request.worldbook_ids,
        preset_id=request.preset_id,
        messages=initial_messages,
        created_at=now,
        updated_at=now,
    )
    
    await save_json(get_session_path(session_id), session.model_dump())
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    path = get_session_path(session_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    path.unlink()
    return {"status": "deleted"}


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, request: SendMessageRequest):
    """Send a message and get streaming response."""
    # Load session
    session_data = await load_json(get_session_path(session_id))
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = ChatSession(**session_data)
    
    # Add user message
    user_msg = Message(
        id=generate_id(),
        role="user",
        content=request.content,
        timestamp=datetime.utcnow().isoformat(),
    )
    session.messages.append(user_msg)
    
    # Save with user message
    session.updated_at = datetime.utcnow().isoformat()
    await save_json(get_session_path(session_id), session.model_dump())
    
    # Get LLM config
    llm_config = await get_llm_config()
    if not llm_config:
        raise HTTPException(status_code=400, detail="No active LLM configuration")
    
    # Load preset, character, worldbook for context
    preset = await load_preset(session.preset_id)
    character = await load_character(session.character_id)
    worldbook = await load_worldbooks(session.worldbook_ids)
    
    # Build system prompt from character/worldbook/preset
    messages_for_scan = [{"content": m.content} for m in session.messages]
    
    # DEBUG: Log what we're building with
    print(f"[Chat] Session preset_id: {session.preset_id}")
    print(f"[Chat] Loaded preset: {preset.get('name') if preset else 'None'}")
    print(f"[Chat] Character: {character.get('data', {}).get('name') if character else 'None'}")
    print(f"[Chat] Worldbook IDs: {session.worldbook_ids}")
    
    pre_history_prompt, post_history_prompt, depth_entries = build_system_prompt(character, worldbook, preset, messages_for_scan)
    
    # DEBUG: Log system prompt content
    print(f"[Chat] pre_history_prompt length: {len(pre_history_prompt) if pre_history_prompt else 0}")
    print(f"[Chat] post_history_prompt length: {len(post_history_prompt) if post_history_prompt else 0}")
    if pre_history_prompt:
        print(f"[Chat] pre_history_prompt first 500 chars: {pre_history_prompt[:500]}")
    
    # Build messages for LLM: pre-history prompt → chat history → post-history prompt
    messages = []
    if pre_history_prompt:
        messages.append({"role": "system", "content": pre_history_prompt})
    
    # Add chat history with depth-based entry injection
    chat_history = [{"role": m.role, "content": m.content} for m in session.messages]
    
    # Inject depth entries into chat history (SillyTavern @ D feature)
    for depth_entry in depth_entries:
        depth = depth_entry["depth"]
        # Insert at position (len - depth) from start, which is depth from end
        insert_pos = max(0, len(chat_history) - depth)
        chat_history.insert(insert_pos, {
            "role": depth_entry["role"],
            "content": depth_entry["content"]
        })
    
    messages.extend(chat_history)
    
    # Add post-history prompt (if any)
    if post_history_prompt:
        messages.append({"role": "system", "content": post_history_prompt})
    
    # DEBUG: Show final message structure
    print(f"[Chat] Final messages count: {len(messages)}")
    for i, m in enumerate(messages):
        role = m.get("role", "unknown")
        content = m.get("content", "")
        has_macros = "{{" in content
        print(f"[Chat] Message {i}: role={role}, len={len(content)}, has_unexpanded_macros={has_macros}")
    
    async def generate():
        """Generate streaming response."""
        full_response = ""
        assistant_msg_id = generate_id()
        
        # Extract generation params from preset
        gen_params = {}
        if preset:
            if preset.get("max_tokens"):
                gen_params["max_tokens"] = preset["max_tokens"]
            if preset.get("temperature") is not None:
                gen_params["temperature"] = preset["temperature"]
            if preset.get("top_p") is not None:
                gen_params["top_p"] = preset["top_p"]
            if preset.get("frequency_penalty"):
                gen_params["frequency_penalty"] = preset["frequency_penalty"]
            if preset.get("presence_penalty"):
                gen_params["presence_penalty"] = preset["presence_penalty"]
            # CoT/Thinking support for Claude and DeepSeek
            if preset.get("enable_cot"):
                # For Claude: use extended thinking (will be added to request if model supports)
                gen_params["enable_thinking"] = True
        
        try:
            async for chunk in stream_completion(messages, llm_config, gen_params):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk, 'message_id': assistant_msg_id})}\n\n"
            
            # Apply regex processing for display
            processed_response = await process_for_display(full_response, message_depth=0)
            
            # Save assistant message (with processed content for display)
            assistant_msg = Message(
                id=assistant_msg_id,
                role="assistant",
                content=processed_response,  # Save processed version
                timestamp=datetime.utcnow().isoformat(),
            )
            session.messages.append(assistant_msg)
            session.updated_at = datetime.utcnow().isoformat()
            await save_json(get_session_path(session_id), session.model_dump())
            
            # Send the processed content in done event for frontend to update
            yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg_id, 'processed_content': processed_response})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
        }
    )


@router.post("/sessions/{session_id}/regenerate/{message_id}")
async def regenerate_message(session_id: str, message_id: str):
    """Regenerate a specific assistant message."""
    session_data = await load_json(get_session_path(session_id))
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = ChatSession(**session_data)
    
    # Find the message index
    msg_index = None
    for i, msg in enumerate(session.messages):
        if msg.id == message_id:
            msg_index = i
            break
    
    if msg_index is None:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if session.messages[msg_index].role != "assistant":
        raise HTTPException(status_code=400, detail="Can only regenerate assistant messages")
    
    # Remove this message and all after it
    session.messages = session.messages[:msg_index]
    
    # Get LLM config
    llm_config = await get_llm_config()
    if not llm_config:
        raise HTTPException(status_code=400, detail="No active LLM configuration")
    
    # Load preset, character, worldbook for context
    preset = await load_preset(session.preset_id)
    character = await load_character(session.character_id)
    worldbook = await load_worldbooks(session.worldbook_ids)
    
    # Build system prompt from character/worldbook/preset
    messages_for_scan = [{"content": m.content} for m in session.messages]
    pre_history_prompt, post_history_prompt, depth_entries = build_system_prompt(character, worldbook, preset, messages_for_scan)
    
    # Build messages for LLM: pre-history prompt → chat history → post-history prompt
    messages = []
    if pre_history_prompt:
        messages.append({"role": "system", "content": pre_history_prompt})
    
    # Add chat history with depth-based entry injection
    chat_history = [{"role": m.role, "content": m.content} for m in session.messages]
    
    # Inject depth entries into chat history (SillyTavern @ D feature)
    for depth_entry in depth_entries:
        depth = depth_entry["depth"]
        insert_pos = max(0, len(chat_history) - depth)
        chat_history.insert(insert_pos, {
            "role": depth_entry["role"],
            "content": depth_entry["content"]
        })
    
    messages.extend(chat_history)
    
    # Add post-history prompt (if any)
    if post_history_prompt:
        messages.append({"role": "system", "content": post_history_prompt})
    
    async def generate():
        """Generate streaming response."""
        full_response = ""
        new_msg_id = generate_id()
        
        # Extract generation params from preset
        gen_params = {}
        if preset:
            if preset.get("max_tokens"):
                gen_params["max_tokens"] = preset["max_tokens"]
            if preset.get("temperature") is not None:
                gen_params["temperature"] = preset["temperature"]
            if preset.get("top_p") is not None:
                gen_params["top_p"] = preset["top_p"]
            if preset.get("frequency_penalty"):
                gen_params["frequency_penalty"] = preset["frequency_penalty"]
            if preset.get("presence_penalty"):
                gen_params["presence_penalty"] = preset["presence_penalty"]
            # CoT/Thinking support
            if preset.get("enable_cot"):
                gen_params["enable_thinking"] = True
        
        try:
            async for chunk in stream_completion(messages, llm_config, gen_params):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk, 'message_id': new_msg_id})}\n\n"
            
            # Apply regex processing for display
            processed_response = await process_for_display(full_response, message_depth=0)
            
            # Save assistant message (with processed content)
            assistant_msg = Message(
                id=new_msg_id,
                role="assistant",
                content=processed_response,
                timestamp=datetime.utcnow().isoformat(),
            )
            session.messages.append(assistant_msg)
            session.updated_at = datetime.utcnow().isoformat()
            await save_json(get_session_path(session_id), session.model_dump())
            
            yield f"data: {json.dumps({'done': True, 'message_id': new_msg_id, 'processed_content': processed_response})}\n\n"
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


@router.get("/sessions/character/{character_id}/latest")
async def get_latest_session_for_character(character_id: str):
    """Get the most recent chat session for a character."""
    sessions = await list_json_files(settings.data_dir / "chats")
    
    character_sessions = [
        s for s in sessions 
        if s.get("character_id") == character_id
    ]
    
    if not character_sessions:
        return None
    
    # Sort by updated_at descending
    character_sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return ChatSession(**character_sessions[0])
