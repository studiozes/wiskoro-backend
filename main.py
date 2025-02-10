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

# 🔹 Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
        current_time = time.time()
        expired_keys = [k for k, t in self.timestamps.items() if current_time - t > settings.CACHE_EXPIRATION]
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
    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response

    # AI-model wisselen naar BlenderBot omdat Mistral niet werkt
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
        raise HTTPException(
            status_code=504,
            detail="Yo fam, deze vraag is te complex voor nu! Probeer het nog een x! ⏳"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"AI API error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="De AI is even offline, kom zo terug! 🔧"
        )

# 🔹 FastAPI setup
app = FastAPI(title="Wiskoro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In productie aanpassen naar specifieke domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 API models
class ChatRequest(BaseModel):
    message: str

# 🔹 API endpoints
@app.get("/")
async def root():
    """Test endpoint om te zien of de API live is."""
    return {"message": "Wiskoro API is live!"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint voor AI-chatbot"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Yo, drop even een vraag! 📢")

    try:
        bot_response = await get_ai_response(request.message)
        return {"response": bot_response}
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise

@app.get("/test")
async def test_endpoint():
    return {"message": "Test werkt!"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})

# 🔹 Startup
@app.on_event("startup")
async def startup_event():
    """Initialize services."""
    try:
        await Database.create_pool()
        logger.info("✅ Applicatie succesvol gestart")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise

# 🔹 Shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup bij afsluiten."""
    if Database.pool:
        await Database.pool.close()
    logger.info("✅ Applicatie succesvol afgesloten")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

@app.get("/routes")
async def list_routes():
    return {route.path: route.methods for route in app.routes}

if __name__ == "__main__":
    import uvicorn
    print("🔥 FastAPI wordt gestart op poort 8080...")  # Debugging log
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
