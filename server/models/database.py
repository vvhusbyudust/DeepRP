"""
Database models and initialization using aiosqlite.
"""
import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from config import settings


DATABASE_PATH = settings.data_dir / "deeprp.db"


async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # LLM Configurations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS llm_configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                default_model TEXT,
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Image API Configurations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS image_configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                model TEXT,
                size TEXT DEFAULT '1024x1024',
                quality TEXT DEFAULT 'standard',
                negative_prompt TEXT DEFAULT '',
                steps INTEGER DEFAULT 28,
                cfg_scale REAL DEFAULT 7.0,
                sampler TEXT DEFAULT '',
                workflow_json TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # TTS Configurations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tts_configs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                default_voice_id TEXT,
                model_id TEXT DEFAULT '',
                stability REAL DEFAULT 0.5,
                similarity_boost REAL DEFAULT 0.75,
                speed REAL DEFAULT 1.0,
                dialogue_wrap_pattern TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Character voice mappings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS character_voices (
                id TEXT PRIMARY KEY,
                tts_config_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                voice_id TEXT NOT NULL,
                FOREIGN KEY (tts_config_id) REFERENCES tts_configs(id)
            )
        """)
        
        # Agent configuration table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_config (
                id TEXT PRIMARY KEY DEFAULT 'default',
                enabled INTEGER DEFAULT 0,
                director_llm_config_id TEXT,
                director_preset_id TEXT,
                writer_llm_config_id TEXT,
                writer_preset_id TEXT,
                painter_llm_config_id TEXT,
                painter_preset_id TEXT,
                image_config_id TEXT,
                tts_config_id TEXT,
                tts_llm_config_id TEXT,
                tts_preset_id TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Regex scripts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS regex_scripts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                find_regex TEXT NOT NULL,
                replace_with TEXT DEFAULT '',
                run_on_user_input INTEGER DEFAULT 0,
                run_on_ai_output INTEGER DEFAULT 1,
                only_format_display INTEGER DEFAULT 1,
                only_format_prompt INTEGER DEFAULT 0,
                min_depth INTEGER DEFAULT 0,
                max_depth INTEGER DEFAULT -1,
                flags TEXT DEFAULT 'g',
                order_index INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Migration helper function
        async def safe_add_column(table: str, column: str, column_def: str):
            """Safely add a column, ignoring if it already exists."""
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
            except aiosqlite.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    # Log unexpected errors but don't crash
                    print(f"[DB Migration] Warning: {e}")
        
        # Migration: Add missing columns to agent_config (safe to run multiple times)
        await safe_add_column("agent_config", "tts_llm_config_id", "TEXT")
        await safe_add_column("agent_config", "tts_preset_id", "TEXT")
        
        # Migration: Add cached_models column to llm_configs for storing fetched model lists
        await safe_add_column("llm_configs", "cached_models", "TEXT DEFAULT '[]'")
        
        # Migration: Add new regex_scripts columns for SillyTavern compatibility
        await safe_add_column("regex_scripts", "run_on_user_input", "INTEGER DEFAULT 0")
        await safe_add_column("regex_scripts", "run_on_ai_output", "INTEGER DEFAULT 1")
        await safe_add_column("regex_scripts", "run_on_edit", "INTEGER DEFAULT 0")
        await safe_add_column("regex_scripts", "only_format_display", "INTEGER DEFAULT 1")
        await safe_add_column("regex_scripts", "only_format_prompt", "INTEGER DEFAULT 0")
        
        # Migration: Add agent stage scope columns for preset binding
        await safe_add_column("regex_scripts", "run_on_director_output", "INTEGER DEFAULT 0")
        await safe_add_column("regex_scripts", "run_on_writer_output", "INTEGER DEFAULT 1")
        await safe_add_column("regex_scripts", "run_on_paint_director_output", "INTEGER DEFAULT 0")
        
        # Migration: Migrate old affect_display/affect_prompt to new columns
        try:
            await db.execute("""
                UPDATE regex_scripts 
                SET only_format_display = affect_display, 
                    only_format_prompt = affect_prompt,
                    run_on_ai_output = 1
                WHERE only_format_display IS NULL OR run_on_ai_output IS NULL
            """)
        except aiosqlite.OperationalError as e:
            # Old columns may not exist, that's fine
            if "no such column" not in str(e).lower():
                print(f"[DB Migration] Warning during data migration: {e}")


        
        # Request logs table for full LLM request/response logging
        await db.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                request_type TEXT NOT NULL,
                model TEXT,
                prompt_preview TEXT,
                full_request TEXT,
                full_response TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                status TEXT DEFAULT 'success',
                error_message TEXT
            )
        """)
        
        # Agent runs table - tracks each complete pipeline execution
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                character_id TEXT,
                timestamp TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                user_message TEXT,
                total_duration_ms INTEGER DEFAULT 0,
                total_tokens_in INTEGER DEFAULT 0,
                total_tokens_out INTEGER DEFAULT 0,
                error_message TEXT,
                director_output TEXT,
                writer_output TEXT,
                image_url TEXT,
                image_prompt TEXT,
                audio_data TEXT
            )
        """)
        
        # Agent stage logs table - tracks each stage within a run
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_stage_logs (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT DEFAULT 'running',
                duration_ms INTEGER DEFAULT 0,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                input_content TEXT,
                output_content TEXT,
                llm_config_id TEXT,
                preset_id TEXT,
                error_message TEXT,
                FOREIGN KEY (run_id) REFERENCES agent_runs(id)
            )
        """)
        
        await db.commit()


# Pydantic models for API responses

class LLMConfig(BaseModel):
    id: str
    name: str
    base_url: str
    api_key_masked: str  # Only show last 4 chars
    default_model: Optional[str] = None
    is_active: bool = False
    created_at: str
    updated_at: str
    cached_models: list[str] = []  # Cached model list from API


class LLMConfigCreate(BaseModel):
    name: str
    base_url: str
    api_key: str
    default_model: Optional[str] = None


class LLMConfigUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    is_active: Optional[bool] = None


class ImageConfig(BaseModel):
    id: str
    name: str
    type: str  # openai, stable_diffusion, comfyui, novelai
    base_url: str
    api_key_masked: str
    model: Optional[str] = None
    size: str = "1024x1024"
    quality: str = "standard"
    # Extended generation parameters
    negative_prompt: str = ""
    steps: int = 28
    cfg_scale: float = 7.0
    sampler: str = ""  # Empty = auto/default
    workflow_json: str = ""  # Custom ComfyUI workflow JSON
    prompt_node_id: Optional[str] = None  # ComfyUI node ID to inject prompt into
    is_active: bool = False
    created_at: str
    updated_at: str


class ImageConfigCreate(BaseModel):
    name: str
    type: str  # openai, stable_diffusion, comfyui, novelai
    base_url: str
    api_key: str
    model: Optional[str] = None
    size: str = "1024x1024"
    quality: str = "standard"
    # Extended generation parameters
    negative_prompt: str = ""
    steps: int = 28
    cfg_scale: float = 7.0
    sampler: str = ""
    workflow_json: str = ""
    prompt_node_id: Optional[str] = None


class TTSConfig(BaseModel):
    id: str
    name: str
    type: str  # elevenlabs, openai
    api_key_masked: str
    default_voice_id: Optional[str] = None
    # Extended parameters
    model_id: str = ""  # ElevenLabs model: eleven_multilingual_v2, eleven_turbo_v2_5, etc.
    stability: float = 0.5  # ElevenLabs: 0.0-1.0
    similarity_boost: float = 0.75  # ElevenLabs: 0.0-1.0
    speed: float = 1.0  # OpenAI: 0.25-4.0
    dialogue_wrap_pattern: str = ""  # Pattern to wrap dialogue text before synthesis, e.g. "<speak>{text}</speak>"
    is_active: bool = False
    created_at: str
    updated_at: str


class TTSConfigCreate(BaseModel):
    name: str
    type: str  # elevenlabs, openai
    api_key: str
    default_voice_id: Optional[str] = None
    # Extended parameters
    model_id: str = ""  # ElevenLabs model ID
    stability: float = 0.5
    similarity_boost: float = 0.75
    speed: float = 1.0
    dialogue_wrap_pattern: str = ""


class RegexScript(BaseModel):
    id: str
    name: str
    enabled: bool = True
    find_regex: str
    replace_with: str = ""
    # SillyTavern-compatible placement options
    run_on_user_input: bool = False  # Apply to user messages
    run_on_ai_output: bool = True    # Apply to AI/assistant messages
    run_on_edit: bool = False        # Apply when editing messages
    # Output formatting options
    only_format_display: bool = True   # Affects what user sees (display)
    only_format_prompt: bool = False   # Affects what goes to LLM (prompt)
    # Depth constraints (0 = most recent message)
    min_depth: int = 0
    max_depth: int = -1  # -1 = no limit
    # Regex flags: g=global, i=ignorecase, m=multiline, s=dotall, u=unicode
    flags: str = "g"
    order_index: int = 0
    # Agent stage scope flags
    run_on_director_output: bool = False
    run_on_writer_output: bool = True
    run_on_paint_director_output: bool = False


class RegexScriptCreate(BaseModel):
    name: str
    find_regex: str
    replace_with: str = ""
    run_on_user_input: bool = False
    run_on_ai_output: bool = True
    run_on_edit: bool = False
    only_format_display: bool = True
    only_format_prompt: bool = False
    min_depth: int = 0
    max_depth: int = -1
    flags: str = "g"
    # Agent stage scope flags
    run_on_director_output: bool = False
    run_on_writer_output: bool = True
    run_on_paint_director_output: bool = False


class AgentConfig(BaseModel):
    enabled: bool = False
    director_llm_config_id: Optional[str] = None
    director_preset_id: Optional[str] = None
    writer_llm_config_id: Optional[str] = None
    writer_preset_id: Optional[str] = None
    # Paint Director + Painter toggle
    enable_paint: bool = True
    painter_llm_config_id: Optional[str] = None
    painter_preset_id: Optional[str] = None
    image_config_id: Optional[str] = None
    # TTS Actor toggle
    enable_tts: bool = True
    tts_config_id: Optional[str] = None
    tts_llm_config_id: Optional[str] = None
    tts_preset_id: Optional[str] = None


class RequestLog(BaseModel):
    id: str
    timestamp: str
    request_type: str
    model: Optional[str] = None
    prompt_preview: Optional[str] = None
    full_request: Optional[str] = None
    full_response: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    status: str = "success"
    error_message: Optional[str] = None


class AgentRun(BaseModel):
    """Tracks a complete agent pipeline execution."""
    id: str
    session_id: str
    character_id: Optional[str] = None
    timestamp: str
    status: str = "running"  # running, success, partial, error
    user_message: Optional[str] = None
    total_duration_ms: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    error_message: Optional[str] = None
    director_output: Optional[str] = None
    writer_output: Optional[str] = None
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    audio_data: Optional[str] = None  # JSON string
    stages: list = []  # Populated when fetching with details


class AgentStageLog(BaseModel):
    """Tracks a single stage within an agent run."""
    id: str
    run_id: str
    stage: str  # director, writer, paint_director, painter, tts
    timestamp: str
    status: str = "running"  # running, success, skipped, error
    duration_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    input_content: Optional[str] = None
    output_content: Optional[str] = None
    llm_config_id: Optional[str] = None
    preset_id: Optional[str] = None
    error_message: Optional[str] = None


def mask_api_key(key: str) -> str:
    """Mask API key, showing only last 4 characters."""
    if len(key) <= 4:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]
