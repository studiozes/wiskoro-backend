import os
import asyncpg
import requests
import smtplib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from email.mime.text import MIMEText
import time
import asyncio

# 🔹 Logging setup with more detailed configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

# 🔹 Settings
class Settings(BaseSettings):
    DATABASE_URL: str
    HUGGINGFACE_API_KEY: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_RECEIVER: str
    RATE_LIMIT_PER_MINUTE: int = 30
    AI_TIMEOUT: int = 10
    CACHE_EXPIRATION: int = 3600  # 1 uur
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "https://wiskoro.com"]  # Add your frontend URLs

    class Config:
        case_sensitive = True

settings = Settings()

# 🔹 In-memory cache
class LocalCache:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            if time.time() - self.timestamps[key] < settings.CACHE_EXPIRATION:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None

    def set(self, key: str, value: str):
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self._cleanup()

    def _cleanup(self):
        current_time = time.time()
        expired_keys = [k for k, t in self.timestamps.items() 
                       if current_time - t > settings.CACHE_EXPIRATION]
        for k in expired_keys:
            del self.cache[k]
            del self.timestamps[k]

cache = LocalCache()

# 🔹 Database connection pooling
class Database:
    pool = None

    @classmethod
    async def create_pool(cls, retries=3):
        for attempt in range(retries):
            try:
                cls.pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=5,
                    max_size=20,
                    command_timeout=10
                )
                logger.info("✅ Database pool succesvol aangemaakt")
                return
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"❌ Database pool creatie gefaald na {retries} pogingen: {e}")
                    raise
                logger.warning(f"⚠️ Database pool creatie poging {attempt + 1} gefaald, nieuwe poging...")
                await asyncio.sleep(2 ** attempt)

    @classmethod
    async def get_connection(cls):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.acquire()

    @classmethod
    async def release_connection(cls, conn):
        await cls.pool.release(conn)

# 🔹 AI chatbot met caching
async def get_ai_response(user_question: str) -> str:
    """Haalt AI-respons op via Hugging Face API."""
    cached_response = cache.get(user_question)
    if cached_response:
        logger.info("Cache hit voor vraag: %s", user_question)
        return cached_response

    AI_MODEL = "facebook/blenderbot-400M-distill"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {"inputs": user_question}

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{AI_MODEL}",
            headers=headers,
            json=payload,
            timeout=settings.AI_TIMEOUT
        )
        response.raise_for_status()
        response_data = response.json()

        if isinstance(response_data, list) and response_data:
            result = response_data[0].get("generated_text", "Yo, geen idee wat je bedoelt... 🤔")
            cache.set(user_question, result)
            return result

        raise ValueError("Onverwacht API response formaat")

    except requests.exceptions.Timeout:
        logger.error("AI timeout voor vraag: %s", user_question)
        raise HTTPException(
            status_code=504,
            detail="Yo fam, deze vraag is te complex voor nu! Probeer het nog een x! ⏳"
        )
    except requests.exceptions.RequestException as e:
        logger.error("AI API error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="De AI is even offline, kom zo terug! 🔧"
        )

# 🔹 FastAPI setup
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    docs_url="/docs",  # Enable Swagger UI
    redoc_url="/redoc"  # Enable ReDoc
)

# Update CORS middleware with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 🔹 API models
class ChatRequest(BaseModel):
    message: str

# 🔹 Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Global error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Er is een onverwachte fout opgetreden."}
    )

# 🔹 API endpoints
@app.get("/")
async def root():
    """Test endpoint om te zien of de API live is."""
    return {"message": "Wiskoro API is live! 🚀"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint voor AI-chatbot"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Yo, drop even een vraag! 📢")

    try:
        bot_response = await get_ai_response(request.message)
        return {"response": bot_response}
    except Exception as e:
        logger.error("Chat endpoint error: %s", str(e), exc_info=True)
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if Database.pool:
            async with Database.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
        return JSONResponse(
            content={
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/routes")
async def list_routes():
    """List all available API routes."""
    try:
        routes_list = {}
        for route in app.routes:
            routes_list[route.path] = {
                "methods": list(route.methods),
                "name": route.name,
                "endpoint": route.path
            }
        logger.info("Routes retrieved successfully")
        return JSONResponse(content=routes_list)
    except Exception as e:
        logger.error("Failed to list routes: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="Kon de routes niet ophalen"
        )

@app.get("/test")
async def test_endpoint():
    """Test endpoint voor basis API functionaliteit."""
    try:
        return {
            "message": "Test endpoint werkt! 🎉",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Test endpoint error: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="Test endpoint fout"
        )

# 🔹 Startup
@app.on_event("startup")
async def startup_event():
    """Initialize services."""
    try:
        await Database.create_pool()
        logger.info("✅ Applicatie succesvol gestart")
    except Exception as e:
        logger.error("❌ Startup error: %s", str(e), exc_info=True)
        raise

# 🔹 Shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup bij afsluiten."""
    try:
        if Database.pool:
            await Database.pool.close()
        logger.info("✅ Applicatie succesvol afgesloten")
    except Exception as e:
        logger.error("❌ Shutdown error: %s", str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info("🔥 FastAPI wordt gestart op poort %d...", port)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
