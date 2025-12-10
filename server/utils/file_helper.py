"""
File helper utilities.
"""
import os
import uuid
import json
import aiofiles
from pathlib import Path
from typing import Any

from config import settings


async def save_json(path: Path, data: Any) -> None:
    """Save data to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))


async def load_json(path: Path) -> Any:
    """Load data from a JSON file."""
    if not path.exists():
        return None
    async with aiofiles.open(path, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)


async def list_json_files(directory: Path) -> list[dict]:
    """List all JSON files in a directory with their contents."""
    if not directory.exists():
        return []
    
    items = []
    for file_path in directory.glob("*.json"):
        data = await load_json(file_path)
        if data:
            items.append(data)
    return items


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


async def save_image(image_data: bytes, chat_session_id: str, filename: str = None) -> str:
    """Save an image to the session's image folder."""
    if filename is None:
        filename = f"{generate_id()}.png"
    
    session_dir = settings.data_dir / "images" / f"chat_session_{chat_session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    image_path = session_dir / filename
    async with aiofiles.open(image_path, 'wb') as f:
        await f.write(image_data)
    
    return f"/static/images/chat_session_{chat_session_id}/{filename}"


async def save_audio(audio_data: bytes, chat_session_id: str, filename: str = None) -> str:
    """Save an audio file to the session's audio folder."""
    if filename is None:
        filename = f"{generate_id()}.mp3"
    
    session_dir = settings.data_dir / "audio" / f"chat_session_{chat_session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    audio_path = session_dir / filename
    async with aiofiles.open(audio_path, 'wb') as f:
        await f.write(audio_data)
    
    return f"/static/audio/chat_session_{chat_session_id}/{filename}"
