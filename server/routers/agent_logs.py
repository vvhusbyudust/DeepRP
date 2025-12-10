"""
Agent Logs Router - API endpoints for agent run logs
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models import AgentRun, AgentStageLog
from services.agent.logging import (
    get_agent_runs,
    get_agent_run_details,
    get_agent_runs_count,
    delete_agent_run,
    clear_agent_logs
)

router = APIRouter()


@router.get("", response_model=list[AgentRun])
async def list_agent_runs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session_id: Optional[str] = None
):
    """List agent runs with pagination and optional session filter."""
    runs = await get_agent_runs(limit=limit, offset=offset, session_id=session_id)
    return [AgentRun(**run) for run in runs]


@router.get("/count")
async def get_runs_count(session_id: Optional[str] = None):
    """Get total count of agent runs."""
    count = await get_agent_runs_count(session_id)
    return {"count": count}


@router.get("/{run_id}")
async def get_run_details(run_id: str):
    """Get a specific agent run with full stage details."""
    run = await get_agent_run_details(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@router.delete("")
async def clear_all_logs():
    """Clear all agent logs."""
    await clear_agent_logs()
    return {"status": "cleared"}


@router.delete("/{run_id}")
async def delete_run(run_id: str):
    """Delete a specific agent run."""
    deleted = await delete_agent_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return {"status": "deleted"}
