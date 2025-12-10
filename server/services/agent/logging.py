"""
Agent Logging Service - Tracks agent pipeline runs and stages
"""
import aiosqlite
from datetime import datetime
from typing import Optional
import json

from models import DATABASE_PATH
from utils import generate_id


async def create_agent_run(
    session_id: str,
    user_message: str,
    character_id: Optional[str] = None
) -> str:
    """Create a new agent run record. Returns the run ID."""
    run_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO agent_runs 
            (id, session_id, character_id, timestamp, status, user_message)
            VALUES (?, ?, ?, ?, 'running', ?)
            """,
            (run_id, session_id, character_id, now, user_message)
        )
        await db.commit()
    
    return run_id


async def start_stage_log(
    run_id: str,
    stage: str,
    input_content: str = "",
    llm_config_id: Optional[str] = None,
    preset_id: Optional[str] = None
) -> str:
    """Start logging a stage. Returns the stage log ID."""
    stage_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO agent_stage_logs 
            (id, run_id, stage, timestamp, status, input_content, llm_config_id, preset_id)
            VALUES (?, ?, ?, ?, 'running', ?, ?, ?)
            """,
            (stage_id, run_id, stage, now, input_content, llm_config_id, preset_id)
        )
        await db.commit()
    
    return stage_id


async def complete_stage_log(
    stage_id: str,
    output_content: str = "",
    duration_ms: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    status: str = "success",
    error_message: Optional[str] = None
):
    """Complete a stage log with results."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE agent_stage_logs SET
                status = ?, duration_ms = ?, tokens_in = ?, tokens_out = ?,
                output_content = ?, error_message = ?
            WHERE id = ?
            """,
            (status, duration_ms, tokens_in, tokens_out, output_content, error_message, stage_id)
        )
        await db.commit()


async def skip_stage_log(run_id: str, stage: str, reason: str = "disabled"):
    """Log a skipped stage."""
    stage_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO agent_stage_logs 
            (id, run_id, stage, timestamp, status, error_message)
            VALUES (?, ?, ?, ?, 'skipped', ?)
            """,
            (stage_id, run_id, stage, now, reason)
        )
        await db.commit()


async def complete_agent_run(
    run_id: str,
    status: str = "success",
    total_duration_ms: int = 0,
    director_output: Optional[str] = None,
    writer_output: Optional[str] = None,
    image_url: Optional[str] = None,
    image_prompt: Optional[str] = None,
    audio_data: Optional[list] = None,
    error_message: Optional[str] = None
):
    """Complete an agent run with final results."""
    # Calculate total tokens from stages
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT SUM(tokens_in), SUM(tokens_out) FROM agent_stage_logs WHERE run_id = ?",
            (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            total_tokens_in = row[0] or 0
            total_tokens_out = row[1] or 0
        
        await db.execute(
            """
            UPDATE agent_runs SET
                status = ?, total_duration_ms = ?,
                total_tokens_in = ?, total_tokens_out = ?,
                director_output = ?, writer_output = ?,
                image_url = ?, image_prompt = ?,
                audio_data = ?, error_message = ?
            WHERE id = ?
            """,
            (status, total_duration_ms, total_tokens_in, total_tokens_out,
             director_output, writer_output, image_url, image_prompt,
             json.dumps(audio_data) if audio_data else None, error_message, run_id)
        )
        await db.commit()


async def get_agent_runs(
    limit: int = 50,
    offset: int = 0,
    session_id: Optional[str] = None
) -> list[dict]:
    """Get agent runs with stage summaries."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = "SELECT * FROM agent_runs"
        params = []
        
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            runs = []
            
            for row in rows:
                run = dict(row)
                
                # Get stage summaries
                async with db.execute(
                    """
                    SELECT stage, status, duration_ms 
                    FROM agent_stage_logs 
                    WHERE run_id = ? 
                    ORDER BY timestamp
                    """,
                    (row["id"],)
                ) as stage_cursor:
                    stages = await stage_cursor.fetchall()
                    run["stages"] = [dict(s) for s in stages]
                
                runs.append(run)
            
            return runs


async def get_agent_run_details(run_id: str) -> Optional[dict]:
    """Get a single agent run with full stage details."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute(
            "SELECT * FROM agent_runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            run = dict(row)
            
            # Get full stage logs
            async with db.execute(
                """
                SELECT * FROM agent_stage_logs 
                WHERE run_id = ? 
                ORDER BY timestamp
                """,
                (run_id,)
            ) as stage_cursor:
                stages = await stage_cursor.fetchall()
                run["stages"] = [dict(s) for s in stages]
            
            return run


async def delete_agent_run(run_id: str) -> bool:
    """Delete an agent run and its stage logs."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM agent_stage_logs WHERE run_id = ?", (run_id,))
        result = await db.execute("DELETE FROM agent_runs WHERE id = ?", (run_id,))
        await db.commit()
        return result.rowcount > 0


async def clear_agent_logs():
    """Clear all agent logs."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM agent_stage_logs")
        await db.execute("DELETE FROM agent_runs")
        await db.commit()


async def get_agent_runs_count(session_id: Optional[str] = None) -> int:
    """Get total count of agent runs."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        query = "SELECT COUNT(*) FROM agent_runs"
        params = []
        
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return row[0]
