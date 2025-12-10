"""
Regex Processing Service - SillyTavern Compatible with Agent Stage Scope
"""
import re
import json
import aiosqlite
from typing import Optional

from models import DATABASE_PATH


async def get_regex_scripts() -> list[dict]:
    """Get all enabled regex scripts ordered by order_index."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM regex_scripts WHERE enabled = 1 ORDER BY order_index"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_regex_scripts_by_ids(script_ids: list[str]) -> list[dict]:
    """Get regex scripts by specific IDs, preserving order."""
    if not script_ids:
        return []
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        placeholders = ",".join(["?" for _ in script_ids])
        async with db.execute(
            f"SELECT * FROM regex_scripts WHERE enabled = 1 AND id IN ({placeholders})",
            script_ids
        ) as cursor:
            rows = await cursor.fetchall()
            scripts = {row["id"]: dict(row) for row in rows}
            # Return in requested order
            return [scripts[sid] for sid in script_ids if sid in scripts]


def expand_regex_macros(pattern: str, ctx: dict) -> str:
    """
    Expand macros in regex patterns (SillyTavern compatibility).
    
    Supported macros:
    - {{user}} - User's display name (regex escaped)
    - {{char}} - Character's name (regex escaped)
    - {{persona}} - User's persona name (regex escaped)
    - {{input}} - Raw user input (if provided)
    
    Note: Values are regex-escaped to prevent injection issues.
    """
    if not ctx:
        return pattern
    
    result = pattern
    
    # User name
    user_name = ctx.get('user', 'User')
    result = re.sub(r'\{\{user\}\}', re.escape(user_name), result, flags=re.IGNORECASE)
    
    # Character name
    char_name = ctx.get('char', ctx.get('character', ''))
    if char_name:
        result = re.sub(r'\{\{char\}\}', re.escape(char_name), result, flags=re.IGNORECASE)
    
    # Persona
    persona = ctx.get('persona', '')
    if persona:
        result = re.sub(r'\{\{persona\}\}', re.escape(persona), result, flags=re.IGNORECASE)
    
    # User input (not escaped, for advanced users who want to match against it)
    user_input = ctx.get('input', '')
    if user_input:
        result = re.sub(r'\{\{input\}\}', re.escape(user_input), result, flags=re.IGNORECASE)
    
    return result


def apply_regex_scripts(
    text: str,
    scripts: list[dict],
    message_role: str = "assistant",  # "user" or "assistant"
    target: str = "display",  # "display" or "prompt"
    message_depth: int = 0,  # 0 = most recent message
    agent_stage: Optional[str] = None,  # "director", "writer", "paint_director", or None for normal chat
    macro_context: Optional[dict] = None  # Optional context for macro expansion in find_regex
) -> str:
    """
    Apply regex scripts to text with SillyTavern-compatible filtering.
    
    Args:
        text: The text to process
        scripts: List of regex script dicts
        message_role: The role of the message ("user" or "assistant")
        target: Processing target ("display" or "prompt")
        message_depth: The message's position from the end (0 = most recent)
        agent_stage: Optional agent pipeline stage for filtering
        macro_context: Optional dict with 'user', 'char', 'persona' for macro expansion
    
    Returns:
        Processed text
    """
    result = text
    
    for script in scripts:
        # Check if script applies to this agent stage
        if agent_stage:
            if agent_stage == "director":
                if not script.get("run_on_director_output", 0):
                    continue
            elif agent_stage == "writer":
                if not script.get("run_on_writer_output", 1):
                    continue
            elif agent_stage == "paint_director":
                if not script.get("run_on_paint_director_output", 0):
                    continue
        else:
            # Normal chat mode - check run_on_ai_output/run_on_user_input
            if message_role == "user" and not script.get("run_on_user_input", 0):
                continue
            if message_role == "assistant" and not script.get("run_on_ai_output", 1):
                continue
        
        # Check if script applies to this target (display vs prompt)
        # Handle both old and new column names for backwards compatibility
        if target == "display":
            applies = script.get("only_format_display", script.get("affect_display", 1))
            if not applies:
                continue
        elif target == "prompt":
            applies = script.get("only_format_prompt", script.get("affect_prompt", 0))
            if not applies:
                continue
        
        # Check depth constraints (only for non-agent-stage processing)
        if not agent_stage:
            min_depth = script.get("min_depth", 0) or 0
            max_depth = script.get("max_depth", -1)
            if max_depth is None:
                max_depth = -1
            
            if message_depth < min_depth:
                continue
            if max_depth >= 0 and message_depth > max_depth:
                continue
        
        # Build regex flags
        flags_str = script.get("flags", "g") or "g"
        regex_flags = 0
        if 'i' in flags_str:
            regex_flags |= re.IGNORECASE
        if 's' in flags_str:
            regex_flags |= re.DOTALL
        if 'm' in flags_str:
            regex_flags |= re.MULTILINE
        if 'u' in flags_str:
            regex_flags |= re.UNICODE
        
        try:
            # Expand macros in find_regex pattern (SillyTavern compatibility)
            find_pattern = script["find_regex"]
            if macro_context:
                find_pattern = expand_regex_macros(find_pattern, macro_context)
            
            pattern = re.compile(find_pattern, regex_flags)
            replace_with = script.get("replace_with", "") or ""
            
            # SillyTavern {{match}} macro support - replaced during substitution
            # Also support standard regex group references: $1, $2, etc.
            def make_replacement(match_obj):
                replaced = replace_with
                # Replace {{match}} with the full matched text
                replaced = replaced.replace("{{match}}", match_obj.group(0))
                replaced = replaced.replace("{{MATCH}}", match_obj.group(0))
                # Replace $0 with full match
                replaced = replaced.replace("$0", match_obj.group(0))
                # Replace $1, $2, etc. with capture groups
                for i in range(1, min(10, len(match_obj.groups()) + 1)):
                    try:
                        group_value = match_obj.group(i) or ""
                        replaced = replaced.replace(f"${i}", group_value)
                    except IndexError:
                        break
                return replaced
            
            if 'g' in flags_str:
                result = pattern.sub(make_replacement, result)
            else:
                result = pattern.sub(make_replacement, result, count=1)
        except re.error as e:
            # Log and skip invalid regex
            print(f"[Regex] Invalid regex '{script.get('name', 'Unknown')}': {e}")
            continue
    
    return result


async def process_for_display(
    text: str, 
    message_role: str = "assistant",
    message_depth: int = 0,
    macro_context: Optional[dict] = None
) -> str:
    """Process text for display to user."""
    scripts = await get_regex_scripts()
    return apply_regex_scripts(
        text, scripts, 
        message_role=message_role,
        target="display", 
        message_depth=message_depth,
        macro_context=macro_context
    )


async def process_for_prompt(
    text: str,
    message_role: str = "assistant", 
    message_depth: int = 0,
    macro_context: Optional[dict] = None
) -> str:
    """Process text for sending to LLM."""
    scripts = await get_regex_scripts()
    return apply_regex_scripts(
        text, scripts,
        message_role=message_role,
        target="prompt", 
        message_depth=message_depth,
        macro_context=macro_context
    )


async def process_for_agent_stage(
    text: str,
    agent_stage: str,
    script_ids: Optional[list[str]] = None,
    target: str = "prompt",
    macro_context: Optional[dict] = None
) -> str:
    """
    Process text for a specific agent pipeline stage.
    
    Args:
        text: The text to process
        agent_stage: "director", "writer", or "paint_director"
        script_ids: Optional list of specific regex script IDs to use (from preset)
        target: "display" or "prompt"
        macro_context: Optional dict with 'user', 'char', 'persona' for macro expansion
    
    Returns:
        Processed text
    """
    if script_ids:
        scripts = await get_regex_scripts_by_ids(script_ids)
    else:
        scripts = await get_regex_scripts()
    
    return apply_regex_scripts(
        text, scripts,
        target=target,
        agent_stage=agent_stage,
        macro_context=macro_context
    )

