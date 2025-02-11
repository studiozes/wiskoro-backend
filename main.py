import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging
import time
import asyncio
import aiohttp

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Logging configuratie
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Applicatie instellingen met type hints en beschrijvingen."""
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    HUGGINGFACE_API_KEY: str = Field(..., description="Hugging Face API key")
    AI_TIMEOUT: int = Field(15, description="Timeout voor AI requests in seconden")
    CACHE_EXPIRATION: int = Field(3600, description="Cache vervaltijd in seconden")
    ALLOWED_ORIGINS: list[str] = Field(
        ["https://wiskoro.nl", "https://www.wiskoro.nl"],
        description="Toegestane CORS origins"
    )

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

class LocalCache:
    """Verbeterde in-memory cache met type hints en betere error handling."""
    def __init__(self, expiration: int = settings.CACHE_EXPIRATION):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._expiration = expiration

    def get(self, key: str) -> Optional[str]:
        """Haalt waarde op uit cache met expiratie check."""
        try:
            if (
                key in self._cache
                and time.time() - self._timestamps[key] < self._expiration
            ):
                return self._cache[key]
        except Exception as e:
            logger.error(f"Cache ophalen mislukt: {str(e)}")
        return None

    def set(self, key: str, value: str) -> None:
        """Slaat waarde op in cache met timestamp."""
        try:
            self._cache[key] = value
            self._timestamps[key] = time.time()
        except Exception as e:
            logger.error(f"Cache opslaan mislukt: {str(e)}")

    def clear_expired(self) -> None:
        """Verwijdert verlopen cache items."""
        current_time = time.time()
        expired_keys = [
            k for k, t in self._timestamps.items()
            if current_time - t >= self._expiration
        ]
        for k in expired_keys:
            self._cache.pop(k, None)
            self._timestamps.pop(k, None)

cache = LocalCache()

# Globale aiohttp ClientSession
async def get_aiohttp_session():
    """Creëert of hergebruikt een aiohttp ClientSession."""
    if not hasattr(get_aiohttp_session, '_session'):
        get_aiohttp_session._session = aiohttp.ClientSession()
    return get_aiohttp_session._session

async def close_aiohttp_session():
    """Sluit de aiohttp ClientSession."""
    if hasattr(get_aiohttp_session, '_session'):
        await get_aiohttp_session._session.close()
        delattr(get_aiohttp_session, '_session')

async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """
    Haalt AI-respons op met verbeterde error handling en response validatie.
    Returns tuple van (response, is_cached).
    """
    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    AI_MODEL = "google/flan-t5-large"
    
    # Verbeterde prompt template
    math_prompt = (
        "Je bent een ervaren wiskundeleraar die uitlegt in jongerentaal.\n\n"
        "🔢 Beantwoord deze wiskundevraag **stap voor stap** en "
        "geef het eindantwoord met een ✅:\n\n"
        f"**Vraag:** {user_question}\n\n"
        "**Antwoord:**"
    )

    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": math_prompt,
        "parameters": {
            "do_sample": True,
            "temperature": 0.7,
            "max_length": 250,
            "top_p": 0.9,
            "return_full_text": False
        }
    }

    try:
        session = await get_aiohttp_session()
        async with asyncio.timeout(settings.AI_TIMEOUT):
            async with session.post(
                f"https://api-inference.huggingface.co/models/{AI_MODEL}",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=503,
                        detail=f"AI service error: {response.status}"
                    )
                
                response_data = await response.json()

        # Valideer response format
        if not isinstance(response_data, list) or not response_data:
            raise ValueError("Ongeldig API response formaat")
        
        result = response_data[0].get("generated_text", "").strip()
        if not result or result.lower() == user_question.lower():
            raise ValueError("Ongeldig AI antwoord ontvangen")

        # Cache resultaat
        cache.set(user_question, result)
        return result, False

    except asyncio.TimeoutError:
        logger.error("AI request timeout")
        raise HTTPException(
            status_code=504,
            detail="Yo fam, deze wiskundevraag is pittig! Probeer het nog een keer! ⏳"
        )
    except aiohttp.ClientError as e:
        logger.error(f"AI request fout: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="De AI is even off-duty, kom zo terug! 🔧"
        )
    except Exception as e:
        logger.error(f"Onverwachte fout: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Er ging iets mis! 😕"
        )

class ChatRequest(BaseModel):
    """Chat request model met validatie."""
    message: str = Field(..., min_length=1, max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Los op: 3x + 5 = 20"
            }
        }

# FastAPI app setup
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    description="Een API voor wiskundige vraagstukken met AI ondersteuning"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint met basis health check."""
    return {
        "message": "Wiskoro API is live!",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Chat endpoint met verbeterde response handling.
    Geeft ook aan of het antwoord uit cache komt.
    """
    try:
        response, is_cached = await get_ai_response(request.message)
        return {
            "response": response,
            "cached": is_cached,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Onverwachte fout bij verwerken van je vraag 😕"
        )

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Uitgebreide health check met extra metrics."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_size": len(cache._cache)
    }

# Startup en shutdown events
@app.on_event("startup")
async def startup_event():
    """Startup event met cache cleanup scheduler."""
    async def cleanup_cache():
        while True:
            try:
                cache.clear_expired()
                await asyncio.sleep(300)  # Elke 5 minuten
            except Exception as e:
                logger.error(f"Cache cleanup error: {str(e)}")

    try:
        # Start cache cleanup task
        asyncio.create_task(cleanup_cache())
        # Initialiseer aiohttp session
        await get_aiohttp_session()
        logger.info("✅ Application startup complete")
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event voor cleanup."""
    try:
        await close_aiohttp_session()
        logger.info("✅ Application shutdown complete")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True  # Alleen voor development
    )
