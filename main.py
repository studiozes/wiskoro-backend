import os
import requests
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 🔹 Logging configuratie
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 🔹 Configuratie instellingen
class Settings(BaseSettings):
    """Applicatie instellingen."""
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = Field(15, description="Timeout voor AI requests")
    CACHE_EXPIRATION: int = Field(3600, description="Cache vervaltijd in seconden")
    ALLOWED_ORIGINS: list[str] = Field(
        ["https://wiskoro.nl", "https://www.wiskoro.nl"],
        description="Toegestane CORS origins"
    )

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# 🔹 Simpele in-memory cache
class LocalCache:
    """Cache om snelle antwoorden te leveren."""
    def __init__(self, expiration: int = settings.CACHE_EXPIRATION):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._expiration = expiration

    def get(self, key: str) -> Optional[str]:
        """Haalt cache op als deze nog geldig is."""
        if key in self._cache and time.time() - self._timestamps[key] < self._expiration:
            return self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        """Slaat waarde op in cache."""
        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear_expired(self) -> None:
        """Verwijdert verlopen cache items."""
        current_time = time.time()
        expired_keys = [k for k, t in self._timestamps.items() if current_time - t >= self._expiration]
        for k in expired_keys:
            self._cache.pop(k, None)
            self._timestamps.pop(k, None)

cache = LocalCache()

# 🔹 AI chatbot logica via Mistral API
async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """Haalt AI-respons op via de **Mistral API**."""
    
    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    # Basis prompt met GenZ-stijl
    prompt = f"""
    Jij bent Wiskoro, een straatwijze wiskundecoach. 
    Geef korte, duidelijke uitleg en gebruik 🧠🔥 als dat past.

    ❓ Vraag: {user_question}

    ✅ Antwoord:
    """

    headers = {"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"}
    payload = {
        "model": "mistral-medium",  # Of een andere variant zoals "mistral-small"
        "messages": [{"role": "system", "content": prompt}]
    }

    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            response_data = response.json()

        # Check of de AI een geldig antwoord gaf
        if "choices" not in response_data or not response_data["choices"]:
            raise ValueError("Ongeldig AI antwoord")

        result = response_data["choices"][0]["message"]["content"].strip()

        # Cache het resultaat voor snellere toekomstige antwoorden
        cache.set(user_question, result)
        return result, False

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Yo, deze vraag is pittig! Probeer het opnieuw. ⏳"
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail="De AI is even off-duty, check later! 🔧"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Er ging iets mis! 😕"
        )

# 🔹 Request model
class ChatRequest(BaseModel):
    """Chat request model met validatie."""
    message: str = Field(..., min_length=1, max_length=500)

    class Config:
        json_schema_extra = {"example": {"message": "Bereken de oppervlakte van een cirkel met straal 4"}}

# 🔹 FastAPI setup
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    description="Een API voor wiskundige vraagstukken met AI",
)

# 🔹 CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 🔹 API Endpoints
@app.get("/")
async def root():
    """API status check."""
    return {
        "message": "Wiskoro API is live!",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """Wiskunde chatbot endpoint."""
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
        raise HTTPException(status_code=500, detail="Er ging iets mis met de AI 😕")

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_size": len(cache._cache)
    }

# 🔹 Periodieke cache cleanup
@app.on_event("startup")
async def startup_event():
    """Startup event voor cache opschoning."""
    async def cleanup_cache():
        while True:
            try:
                cache.clear_expired()
                await asyncio.sleep(300)  # Elke 5 minuten
            except Exception as e:
                logger.error(f"Cache cleanup error: {str(e)}")

    try:
        asyncio.create_task(cleanup_cache())
        logger.info("✅ Application startup complete")
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True  # Voor ontwikkeling
    )
