"""
Request Logs Router - Handles LLM request logging and retrieval
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional
import aiosqlite
import json

from models import DATABASE_PATH, RequestLog
from utils import generate_id

router = APIRouter()


async def log_request(
    request_type: str,
    model: str,
    full_request: dict,
    full_response: dict = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    duration_ms: int = 0,
    status: str = "success",
    error_message: str = None
) -> str:
    """Log an LLM request to the database."""
    log_id = generate_id()
    now = datetime.utcnow().isoformat()
    
    # Create preview from first message or prompt
    prompt_preview = ""
    if isinstance(full_request, dict):
        messages = full_request.get("messages", [])
        if messages:
            last_msg = messages[-1] if messages else {}
            content = last_msg.get("content", "")
            prompt_preview = content[:200] + "..." if len(content) > 200 else content
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO request_logs 
            (id, timestamp, request_type, model, prompt_preview, full_request, full_response,
             tokens_in, tokens_out, duration_ms, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (log_id, now, request_type, model, prompt_preview,
             json.dumps(full_request, ensure_ascii=False) if full_request else None,
             json.dumps(full_response, ensure_ascii=False) if full_response else None,
             tokens_in, tokens_out, duration_ms, status, error_message)
        )
        await db.commit()
    
    return log_id


@router.get("", response_model=list[RequestLog])
async def list_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    request_type: Optional[str] = None
):
    """List request logs with pagination."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = "SELECT * FROM request_logs"
        params = []
        
        if request_type:
            query += " WHERE request_type = ?"
            params.append(request_type)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [
                RequestLog(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    request_type=row["request_type"],
                    model=row["model"],
                    prompt_preview=row["prompt_preview"],
                    full_request=row["full_request"],
                    full_response=row["full_response"],
                    tokens_in=row["tokens_in"] or 0,
                    tokens_out=row["tokens_out"] or 0,
                    duration_ms=row["duration_ms"] or 0,
                    status=row["status"] or "success",
                    error_message=row["error_message"],
                )
                for row in rows
            ]


@router.get("/count")
async def get_log_count():
    """Get total count of logs."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM request_logs") as cursor:
            row = await cursor.fetchone()
            return {"count": row[0]}


@router.get("/{log_id}", response_model=RequestLog)
async def get_log(log_id: str):
    """Get a specific log entry with full details."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM request_logs WHERE id = ?", (log_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Log not found")
            return RequestLog(
                id=row["id"],
                timestamp=row["timestamp"],
                request_type=row["request_type"],
                model=row["model"],
                prompt_preview=row["prompt_preview"],
                full_request=row["full_request"],
                full_response=row["full_response"],
                tokens_in=row["tokens_in"] or 0,
                tokens_out=row["tokens_out"] or 0,
                duration_ms=row["duration_ms"] or 0,
                status=row["status"] or "success",
                error_message=row["error_message"],
            )


@router.delete("")
async def clear_logs():
    """Clear all request logs."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM request_logs")
        await db.commit()
    return {"status": "cleared"}


@router.delete("/{log_id}")
async def delete_log(log_id: str):
    """Delete a specific log entry."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        result = await db.execute("DELETE FROM request_logs WHERE id = ?", (log_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Log not found")
    return {"status": "deleted"}
