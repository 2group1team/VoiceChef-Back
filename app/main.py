from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.routers import router
from app.config.config import settings
from app.utils.generate_docs import generate_markdown_from_app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    for dir_name in ["uploads/photos", "cache/tts"]:
        Path(dir_name).mkdir(parents=True, exist_ok=True)

    logger.info("Voice Chef API started")
    yield
    logger.info("Voice Chef API stopped")
app = FastAPI(
    title="Voice Chef API",
    description="API для мобильного приложения Voice Chef",
    version=API_VERSION,
    lifespan=lifespan
)

app.include_router(router)

# CORS middleware с настройками из конфига
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URLS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=["Content-Disposition"],
    max_age=3600
)

# Настройка статических файлов
MEDIA_DIR = Path("media")
RECIPES_DIR = MEDIA_DIR / "recipes"
RECIPES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", tags=["Health Check"])
async def root():
    return {
        "status": "ok",
        "message": "Voice Chef API is running",
        "version": API_VERSION
    }

@app.get("/admin")
async def admin_panel():
    return FileResponse("app/static/admin.html")