import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import logging
import time
import asyncio

import requests
import asyncpg
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
    """Applicatie instellingen."""
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    MISTRAL_API_KEY: str = Field(..., description="Mistral AI API key")
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
    """In-memory cache."""
    def __init__(self, expiration: int = settings.CACHE_EXPIRATION):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._expiration = expiration

    def get(self, key: str) -> Optional[str]:
        if key in self._cache and time.time() - self._timestamps[key] < self._expiration:
            return self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        self._cache[key] = value
        self._timestamps[key] = time.time()

cache = LocalCache()

async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """Haalt AI-respons op met Mistral API."""
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    headers = {"Authorization": f"Bearer {settings.MISTRAL_API_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": f"{user_question}\nAntwoord in GenZ-straatstaal:", "max_tokens": 100}

    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                "https://api.mistral.ai/v1/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            response_data = response.json()

        if "choices" not in response_data or not response_data["choices"]:
            raise ValueError("Ongeldig AI antwoord ontvangen")
        
        result = response_data["choices"][0]["text"].strip()
        cache.set(user_question, result)
        return result, False

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Yo fam, deze wiskundevraag is pittig! Probeer 'm nog een keer! ⏳"
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail="De AI is even off-duty, kom zo terug! 🔧"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Er ging iets mis! 😕"
        )

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=1000)

app = FastAPI(title="Wiskoro API", version="1.0.0", description="Een API voor wiskundige vraagstukken met AI ondersteuning")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Wiskoro API is live!", "status": "healthy"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint met straattaal vibe."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Yo, drop even een vraag! 📢")
    
    if not any(char.isdigit() for char in request.message) and not any(word in request.message.lower() for word in ["plus", "min", "keer", "gedeeld", "wortel", "kwadraat"]):
        return {"response": "Bro, ik ben hier voor wiskunde. Drop ff een som. 📐"}
    
    try:
        bot_response, is_cached = await get_ai_response(request.message)
        return {"response": bot_response, "cached": is_cached, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Onverwachte fout bij verwerken van je vraag 😕")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "cache_size": len(cache._cache)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info", reload=True)
