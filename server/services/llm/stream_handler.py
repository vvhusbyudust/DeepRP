"""
LLM Stream Handler - Handles streaming responses from OpenAI-compatible APIs
"""
import httpx
import json
import time
import aiosqlite
from collections import OrderedDict
from typing import AsyncIterator, Optional

from models import DATABASE_PATH
from utils import decrypt_api_key, get_logger

# Set up module logger
logger = get_logger("llm.stream")

# Global abort controller for stopping requests with memory limit
_abort_flags: OrderedDict[str, bool] = OrderedDict()
MAX_ABORT_FLAGS = 500  # Prevent memory growth


def set_abort(session_id: str):
    """Set abort flag for a session."""
    _abort_flags[session_id] = True
    # Cleanup old entries to prevent memory leak
    while len(_abort_flags) > MAX_ABORT_FLAGS:
        _abort_flags.popitem(last=False)
    logger.debug("Abort flag set for session %s", session_id)


def clear_abort(session_id: str):
    """Clear abort flag for a session."""
    _abort_flags.pop(session_id, None)


def should_abort(session_id: str) -> bool:
    """Check if session should abort."""
    return _abort_flags.get(session_id, False)


async def get_llm_config(config_id: Optional[str] = None) -> Optional[dict]:
    """Get LLM configuration by ID or get active config."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if config_id:
            query = "SELECT * FROM llm_configs WHERE id = ?"
            params = (config_id,)
        else:
            query = "SELECT * FROM llm_configs WHERE is_active = 1"
            params = ()
        
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            return {
                "id": row["id"],
                "name": row["name"],
                "base_url": row["base_url"],
                "api_key": decrypt_api_key(row["api_key_encrypted"]),
                "model": row["default_model"],
            }


async def stream_completion(
    messages: list[dict],
    config: dict,
    params: Optional[dict] = None,
    session_id: Optional[str] = None
) -> AsyncIterator[str]:
    """
    Stream LLM responses as text chunks.
    
    Args:
        messages: List of message dicts with role and content
        config: LLM configuration with base_url, api_key, model
        params: Optional generation parameters (temperature, max_tokens, etc.)
        session_id: Optional session ID for abort support
    
    Yields:
        Text chunks from the LLM response
    """
    from routers.logs import log_request
    
    if params is None:
        params = {}
    
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]
    model = config.get("model", "gpt-3.5-turbo")
    
    request_body = {
        "model": model,
        "messages": messages,
        "stream": True,
        **params
    }
    
    start_time = time.time()
    full_response = ""
    status = "success"
    error_message = None
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)  # Reasonable limits
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    status = "error"
                    error_message = f"LLM API error {response.status_code}: {error_text.decode()}"
                    raise Exception(error_message)
                
                async for line in response.aiter_lines():
                    # Check abort flag
                    if session_id and should_abort(session_id):
                        clear_abort(session_id)
                        break
                    
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        data = line[6:]
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if choices := chunk.get("choices"):
                                choice = choices[0]
                                if delta := choice.get("delta"):
                                    # Handle thinking/reasoning content (Claude, DeepSeek)
                                    thinking = delta.get("thinking") or delta.get("reasoning_content")
                                    if thinking:
                                        # Wrap thinking in <think> tags for frontend
                                        full_response += f"<think>{thinking}</think>"
                                        yield f"<think>{thinking}</think>"
                                    
                                    if content := delta.get("content"):
                                        full_response += content
                                        yield content
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPError as e:
            status = "error"
            error_message = f"HTTP error: {str(e)}"
            raise Exception(error_message)
        finally:
            # Log the request
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                await log_request(
                    request_type="chat",
                    model=model,
                    full_request=request_body,
                    full_response={"content": full_response} if full_response else None,
                    tokens_in=0,  # Would need to count from messages
                    tokens_out=0,  # Would need to count response
                    duration_ms=duration_ms,
                    status=status,
                    error_message=error_message
                )
            except Exception as log_err:
                # Don't fail on logging errors, but make them visible
                logger.warning("Failed to log request: %s", log_err)


async def get_completion(
    messages: list[dict],
    config: dict,
    params: Optional[dict] = None
) -> str:
    """
    Get a non-streaming completion from the LLM.
    
    Args:
        messages: List of message dicts with role and content
        config: LLM configuration
        params: Optional generation parameters
    
    Returns:
        Complete response text
    """
    from routers.logs import log_request
    
    if params is None:
        params = {}
    
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]
    model = config.get("model", "gpt-3.5-turbo")
    
    request_body = {
        "model": model,
        "messages": messages,
        "stream": False,
        **params
    }
    
    start_time = time.time()
    status = "success"
    error_message = None
    response_content = None
    response_data = None
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=120.0
            )
            
            if response.status_code != 200:
                status = "error"
                error_message = f"LLM API error {response.status_code}: {response.text}"
                raise Exception(error_message)
            
            response_data = response.json()
            response_content = response_data["choices"][0]["message"]["content"]
            return response_content
            
        except httpx.HTTPError as e:
            status = "error"
            error_message = f"HTTP error: {str(e)}"
            raise Exception(error_message)
            
        finally:
            # Log the request
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                await log_request(
                    request_type="chat",
                    model=model,
                    full_request=request_body,
                    full_response=response_data,
                    tokens_in=response_data.get("usage", {}).get("prompt_tokens", 0) if response_data else 0,
                    tokens_out=response_data.get("usage", {}).get("completion_tokens", 0) if response_data else 0,
                    duration_ms=duration_ms,
                    status=status,
                    error_message=error_message
                )
            except Exception as log_err:
                # Don't fail on logging errors, but make them visible
                logger.warning("Failed to log request: %s", log_err)

