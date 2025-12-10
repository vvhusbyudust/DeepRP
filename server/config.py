"""
DeepRP Server Configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 7412
    debug: bool = False
    
    # Paths
    data_dir: Path = Path("data")
    
    # Database
    database_url: str = "sqlite+aiosqlite:///data/deeprp.db"
    
    # Encryption
    encryption_key: str | None = None
    
    class Config:
        env_prefix = "DEEPRP_"
        env_file = ".env"


settings = Settings()

# Ensure data directories exist
(settings.data_dir / "characters").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "worldbooks").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "presets").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "chats").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "images").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "audio").mkdir(parents=True, exist_ok=True)
