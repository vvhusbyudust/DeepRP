"""
Regex Router - Handles regex script management for display/prompt processing
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import aiosqlite
import re

from models import DATABASE_PATH, RegexScript, RegexScriptCreate
from utils import generate_id

router = APIRouter()


@router.get("/", response_model=list[RegexScript])
async def list_regex_scripts():
    """List all regex scripts."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM regex_scripts ORDER BY order_index") as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                row_dict = dict(row)
                result.append(RegexScript(
                    id=row_dict["id"],
                    name=row_dict["name"],
                    enabled=bool(row_dict["enabled"]),
                    find_regex=row_dict["find_regex"],
                    replace_with=row_dict["replace_with"] or "",
                    run_on_user_input=bool(row_dict.get("run_on_user_input", 0)),
                    run_on_ai_output=bool(row_dict.get("run_on_ai_output", 1)),
                    run_on_edit=bool(row_dict.get("run_on_edit", 0)),
                    only_format_display=bool(row_dict.get("only_format_display", row_dict.get("affect_display", 1))),
                    only_format_prompt=bool(row_dict.get("only_format_prompt", row_dict.get("affect_prompt", 0))),
                    min_depth=row_dict.get("min_depth", 0),
                    max_depth=row_dict.get("max_depth", -1),
                    flags=row_dict.get("flags", "g"),
                    order_index=row_dict.get("order_index", 0),
                    run_on_director_output=bool(row_dict.get("run_on_director_output", 0)),
                    run_on_writer_output=bool(row_dict.get("run_on_writer_output", 1)),
                    run_on_paint_director_output=bool(row_dict.get("run_on_paint_director_output", 0)),
                ))
            return result



@router.post("/", response_model=RegexScript)
async def create_regex_script(script: RegexScriptCreate):
    """Create a new regex script."""
    script_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    # Validate regex
    try:
        re.compile(script.find_regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {str(e)}")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get next order index
        async with db.execute("SELECT MAX(order_index) FROM regex_scripts") as cursor:
            row = await cursor.fetchone()
            order_index = (row[0] or 0) + 1
        
        await db.execute(
            """
            INSERT INTO regex_scripts 
            (id, name, enabled, find_regex, replace_with, 
             run_on_user_input, run_on_ai_output, run_on_edit, only_format_display, only_format_prompt,
             min_depth, max_depth, flags, order_index,
             run_on_director_output, run_on_writer_output, run_on_paint_director_output,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (script_id, script.name, 1, script.find_regex, script.replace_with,
             1 if script.run_on_user_input else 0, 1 if script.run_on_ai_output else 0,
             1 if script.run_on_edit else 0,
             1 if script.only_format_display else 0, 1 if script.only_format_prompt else 0,
             script.min_depth, script.max_depth, script.flags, order_index,
             1 if script.run_on_director_output else 0, 1 if script.run_on_writer_output else 0,
             1 if script.run_on_paint_director_output else 0, now, now)
        )
        await db.commit()
    
    return RegexScript(
        id=script_id,
        name=script.name,
        enabled=True,
        find_regex=script.find_regex,
        replace_with=script.replace_with,
        run_on_user_input=script.run_on_user_input,
        run_on_ai_output=script.run_on_ai_output,
        run_on_edit=script.run_on_edit,
        only_format_display=script.only_format_display,
        only_format_prompt=script.only_format_prompt,
        min_depth=script.min_depth,
        max_depth=script.max_depth,
        flags=script.flags,
        order_index=order_index,
        run_on_director_output=script.run_on_director_output,
        run_on_writer_output=script.run_on_writer_output,
        run_on_paint_director_output=script.run_on_paint_director_output,
    )


@router.put("/{script_id}", response_model=RegexScript)
async def update_regex_script(script_id: str, update: RegexScriptCreate):
    """Update a regex script."""
    # Validate regex
    try:
        re.compile(update.find_regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {str(e)}")
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        now = datetime.utcnow().isoformat()
        result = await db.execute(
            """
            UPDATE regex_scripts SET
                name = ?, find_regex = ?, replace_with = ?,
                run_on_user_input = ?, run_on_ai_output = ?, run_on_edit = ?,
                only_format_display = ?, only_format_prompt = ?,
                min_depth = ?, max_depth = ?, flags = ?,
                run_on_director_output = ?, run_on_writer_output = ?, run_on_paint_director_output = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (update.name, update.find_regex, update.replace_with,
             1 if update.run_on_user_input else 0, 1 if update.run_on_ai_output else 0,
             1 if update.run_on_edit else 0,
             1 if update.only_format_display else 0, 1 if update.only_format_prompt else 0,
             update.min_depth, update.max_depth, update.flags,
             1 if update.run_on_director_output else 0, 1 if update.run_on_writer_output else 0,
             1 if update.run_on_paint_director_output else 0, now, script_id)
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Script not found")
        
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM regex_scripts WHERE id = ?", (script_id,)) as cursor:
            row = await cursor.fetchone()
            row_dict = dict(row)
            return RegexScript(
                id=row_dict["id"],
                name=row_dict["name"],
                enabled=bool(row_dict["enabled"]),
                find_regex=row_dict["find_regex"],
                replace_with=row_dict["replace_with"] or "",
                run_on_user_input=bool(row_dict.get("run_on_user_input", 0)),
                run_on_ai_output=bool(row_dict.get("run_on_ai_output", 1)),
                run_on_edit=bool(row_dict.get("run_on_edit", 0)),
                only_format_display=bool(row_dict.get("only_format_display", 1)),
                only_format_prompt=bool(row_dict.get("only_format_prompt", 0)),
                min_depth=row_dict.get("min_depth", 0),
                max_depth=row_dict.get("max_depth", -1),
                flags=row_dict.get("flags", "g"),
                order_index=row_dict.get("order_index", 0),
                run_on_director_output=bool(row_dict.get("run_on_director_output", 0)),
                run_on_writer_output=bool(row_dict.get("run_on_writer_output", 1)),
                run_on_paint_director_output=bool(row_dict.get("run_on_paint_director_output", 0)),
            )


@router.delete("/{script_id}")
async def delete_regex_script(script_id: str):
    """Delete a regex script."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        result = await db.execute("DELETE FROM regex_scripts WHERE id = ?", (script_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Script not found")
    return {"status": "deleted"}


@router.put("/{script_id}/toggle")
async def toggle_regex_script(script_id: str):
    """Toggle a regex script's enabled state."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE regex_scripts SET enabled = NOT enabled, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), script_id)
        )
        await db.commit()
    return {"status": "toggled"}


class TestRegexRequest(BaseModel):
    find_regex: str
    replace_with: str
    flags: str
    test_text: str


@router.post("/test")
async def test_regex(request: TestRegexRequest):
    """Test a regex pattern against sample text."""
    try:
        # Build regex flags
        flags = 0
        if 'i' in request.flags:
            flags |= re.IGNORECASE
        if 's' in request.flags:
            flags |= re.DOTALL
        if 'm' in request.flags:
            flags |= re.MULTILINE
        
        pattern = re.compile(request.find_regex, flags)
        
        # Find all matches
        matches = [m.group() for m in pattern.finditer(request.test_text)]
        
        # Apply replacement
        if 'g' in request.flags:
            result = pattern.sub(request.replace_with, request.test_text)
        else:
            result = pattern.sub(request.replace_with, request.test_text, count=1)
        
        return {
            "matches": matches,
            "result": result,
            "valid": True,
        }
    except re.error as e:
        return {
            "matches": [],
            "result": request.test_text,
            "valid": False,
            "error": str(e),
        }


@router.put("/reorder")
async def reorder_scripts(order: list[str]):
    """Reorder regex scripts by providing list of IDs in desired order."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for index, script_id in enumerate(order):
            await db.execute(
                "UPDATE regex_scripts SET order_index = ? WHERE id = ?",
                (index, script_id)
            )
        await db.commit()
    return {"status": "reordered"}


@router.get("/export")
async def export_all_regex():
    """Export all regex scripts in SillyTavern-compatible format."""
    scripts = await list_regex_scripts()
    
    # Convert to SillyTavern format
    st_scripts = []
    for script in scripts:
        # Map placement: 1=AI Output, 2=User Input
        placement = []
        if script.run_on_ai_output:
            placement.append(1)  # AI Output
        if script.run_on_user_input:
            placement.append(2)  # User Input
        
        st_scripts.append({
            "scriptName": script.name,
            "findRegex": script.find_regex,
            "replaceString": script.replace_with,
            "trimStrings": [],
            "placement": placement,
            "disabled": not script.enabled,
            "markdownOnly": script.only_format_display and not script.only_format_prompt,
            "promptOnly": script.only_format_prompt and not script.only_format_display,
            "runOnEdit": True,
            "substituteRegex": False,
            "minDepth": script.min_depth,
            "maxDepth": script.max_depth if script.max_depth >= 0 else None,
        })
    
    return {"regex_scripts": st_scripts}


@router.post("/import")
async def import_regex_scripts(data: dict):
    """Import regex scripts from SillyTavern format."""
    scripts = data.get("regex_scripts", [])
    if not scripts and isinstance(data, list):
        scripts = data  # Handle direct list format
    
    imported = []
    async with aiosqlite.connect(DATABASE_PATH) as db:
        now = datetime.utcnow().isoformat()
        
        for st_script in scripts:
            script_id = generate_id()
            
            # Map placement to run_on options
            placement = st_script.get("placement", [1])
            run_on_ai_output = 1 in placement
            run_on_user_input = 2 in placement
            
            # Map display/prompt options
            prompt_only = st_script.get("promptOnly", False)
            markdown_only = st_script.get("markdownOnly", False)
            only_format_display = not prompt_only
            only_format_prompt = prompt_only or not markdown_only
            
            await db.execute(
                """
                INSERT INTO regex_scripts 
                (id, name, enabled, find_regex, replace_with, 
                 run_on_user_input, run_on_ai_output, only_format_display, only_format_prompt,
                 min_depth, max_depth, flags, order_index, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (script_id, st_script.get("scriptName", "Imported Script"),
                 0 if st_script.get("disabled", False) else 1,
                 st_script.get("findRegex", ""),
                 st_script.get("replaceString", ""),
                 1 if run_on_user_input else 0,
                 1 if run_on_ai_output else 0,
                 1 if only_format_display else 0,
                 1 if only_format_prompt else 0,
                 st_script.get("minDepth", 0),
                 st_script.get("maxDepth") if st_script.get("maxDepth") is not None else -1,
                 "g",
                 len(imported),
                 now, now)
            )
            
            imported.append({
                "id": script_id,
                "name": st_script.get("scriptName", "Imported Script"),
            })
        
        await db.commit()
    
    return {"imported": imported, "count": len(imported)}
