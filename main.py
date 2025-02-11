import os
import asyncpg
import requests
import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# 🔹 Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 🔹 Settings with validation
class Settings(BaseSettings):
    DATABASE_URL: str
    HUGGINGFACE_API_KEY: str
    AI_TIMEOUT: int = 15
    CACHE_EXPIRATION: int = 3600
    MIN_QUESTION_LENGTH: int = 3
    MAX_QUESTION_LENGTH: int = 500

    class Config:
        case_sensitive = True

    def validate_api_key(self) -> bool:
        return bool(self.HUGGINGFACE_API_KEY and len(self.HUGGINGFACE_API_KEY) > 10)

settings = Settings()

# 🔹 Enhanced in-memory cache with cleanup
class LocalCache:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self._last_cleanup: float = time.time()
        self._cleanup_interval: int = 300  # 5 minutes

    def _should_cleanup(self) -> bool:
        return time.time() - self._last_cleanup > self._cleanup_interval

    def _cleanup_expired(self):
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp >= settings.CACHE_EXPIRATION
        ]
        for key in expired_keys:
            del self.cache[key]
            del self.timestamps[key]
        self._last_cleanup = current_time

    def get(self, key: str) -> Optional[str]:
        if self._should_cleanup():
            self._cleanup_expired()
        
        if key in self.cache and time.time() - self.timestamps[key] < settings.CACHE_EXPIRATION:
            logger.debug(f"Cache hit for key: {key}")
            return self.cache[key]
        return None

    def set(self, key: str, value: str):
        if self._should_cleanup():
            self._cleanup_expired()
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
        logger.debug(f"Cached value for key: {key}")

cache = LocalCache()

# 🔹 Database connection pool
class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=5,
                    max_size=20
                )
                logger.info("Database connection pool created successfully")
            except Exception as e:
                logger.error(f"Failed to create database pool: {str(e)}")
                raise

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

db = Database()

# 🔹 AI chatbot logic with improved error handling
async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """
    Fetches AI response via Hugging Face API with math focus.
    Returns tuple of (response, is_cached)
    """
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    AI_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"

    math_prompt = (
        f"Jij bent een ervaren wiskundeleraar die uitlegt in jongerentaal.\n\n"
        f"🔢 Beantwoord deze wiskundevraag **stap voor stap** en geef het eindantwoord met een ✅:\n\n"
        f"**Vraag:** {user_question}\n\n"
        f"**Antwoord:**"
    )

    try:
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
        payload = {
            "inputs": math_prompt,
            "parameters": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_length": 500
            }
        }

        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{AI_MODEL}",
                headers=headers,
                json=payload,
                timeout=settings.AI_TIMEOUT
            )
            
            response.raise_for_status()
            response_data = response.json()

            if not isinstance(response_data, list) or not response_data:
                raise ValueError("Unexpected API response format")

            result = response_data[0].get("generated_text", "").strip()
            
            if not result or result.lower().strip() == user_question.lower().strip():
                raise ValueError("AI returned empty or repeated question")

            cache.set(user_question, result)
            return result, False

    except asyncio.TimeoutError:
        logger.error("AI request timed out")
        raise HTTPException(
            status_code=504,
            detail="Yo fam, deze wiskundevraag is pittig! Probeer het nog een keer! ⏳"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"AI request failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"De AI is even off-duty, kom zo terug! 🔧"
        )
    except ValueError as e:
        logger.error(f"AI response validation failed: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Kon geen goed antwoord genereren. Probeer je vraag anders te formuleren! 🤔"
        )

# 🔹 API models with validation
class ChatRequest(BaseModel):
    message: str

    def validate_message(self) -> str:
        """Validates and sanitizes the message."""
        message = self.message.strip()
        if len(message) < settings.MIN_QUESTION_LENGTH:
            raise ValueError("Bericht is te kort!")
        if len(message) > settings.MAX_QUESTION_LENGTH:
            raise ValueError("Bericht is te lang!")
        return message

# 🔹 FastAPI setup with enhanced middleware
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    description="Een API voor wiskundehulp in jongerentaal"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wiskoro.nl", "https://www.wiskoro.nl"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log request durations."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"Request to {request.url.path} took {duration:.2f} seconds")
    return response

# 🔹 Enhanced API endpoints
@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Wiskoro API is live!",
        "status": "healthy",
        "version": app.version
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Enhanced chat endpoint with better error handling and response metadata."""
    try:
        message = request.validate_message()
        response, is_cached = await get_ai_response(message)
        
        return {
            "response": response,
            "metadata": {
                "cached": is_cached,
                "timestamp": datetime.utcnow().isoformat(),
                "question_length": len(message)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Er ging iets mis met de AI 😕 Probeer het later nog eens!"
        )

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with system status."""
    return JSONResponse(content={
        "status": "healthy",
        "cache_size": len(cache.cache),
        "timestamp": datetime.utcnow().isoformat()
    })

# 🔹 Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup with enhanced error handling and validation."""
    try:
        if not settings.validate_api_key():
            raise ValueError("Invalid Hugging Face API key configuration")
        
        await db.connect()
        logger.info("✅ Application startup complete")
    except Exception as e:
        logger.error("❌ Startup error: %s", str(e), exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of application resources."""
    try:
        await db.disconnect()
        logger.info("✅ Application shutdown complete")
    except Exception as e:
        logger.error("❌ Shutdown error: %s", str(e), exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info"
    )
