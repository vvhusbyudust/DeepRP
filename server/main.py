"""
DeepRP - AI Role Play Agent
FastAPI Backend Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from config import settings
from models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    print(f"DeepRP started on http://localhost:{settings.port}")
    yield
    # Shutdown
    print("DeepRP shutting down...")


# Create FastAPI app
app = FastAPI(
    title="DeepRP",
    description="AI Role Play Agent with Director/Writer/Painter Architecture",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from routers import chat, config, characters, worldbooks, presets, images, tts, regex, agent, agent_logs, logs

app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(characters.router, prefix="/api/characters", tags=["Characters"])
app.include_router(worldbooks.router, prefix="/api/worldbooks", tags=["World Books"])
app.include_router(presets.router, prefix="/api/presets", tags=["Presets"])
app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(tts.router, prefix="/api/tts", tags=["TTS"])
app.include_router(regex.router, prefix="/api/regex", tags=["Regex"])
app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
app.include_router(agent_logs.router, prefix="/api/agent/logs", tags=["Agent Logs"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])

# Ensure static directories exist
(settings.data_dir / "images").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "audio").mkdir(parents=True, exist_ok=True)

# Serve static files (images, audio)
app.mount("/static/images", StaticFiles(directory=str(settings.data_dir / "images")), name="images")
app.mount("/static/audio", StaticFiles(directory=str(settings.data_dir / "audio")), name="audio")

# Serve frontend (if built)
public_dir = Path("public")
if public_dir.exists():
    app.mount("/", StaticFiles(directory="public", html=True), name="frontend")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
