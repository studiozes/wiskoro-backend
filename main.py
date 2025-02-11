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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Constants
SYSTEM_PROMPT = """Je bent Wiskoro, de Nederlandse wiskunde G! 🧮

REGELS:
- SUPER KORT antwoorden (max 3 zinnen)
- ALLEEN wiskunde/reken vragen beantwoorden
- Voor niet-wiskunde: "Yo sorry fam! Ik ga alleen over wiskunde/rekenen. Daar ben ik echt een G in! 🧮"
- ALTIJD Nederlands met straattaal mix
- ALTIJD eindig met emoji

TAALGEBRUIK:
- "Yo" als start
- "Sws" voor "sowieso"
- "Fr fr" voor emphasis
- "Geen cap" voor "echt waar"
- Mix normale uitleg met straattaal

FORMAAT:
Antwoord → Korte uitleg → Emoji

Voorbeeld:
"Yo! Antwoord = 25m² sws.
Check: 5 x 5 = 25, geen cap! 📐"
"""

ERROR_MESSAGES = {
    "timeout": "Yo deze som duurt te lang fam! Probeer nog een keer ⏳",
    "service": "Ff chillen, ben zo back! 🔧",
    "non_math": "Yo sorry, alleen wiskunde/rekenen hier! Daar ben ik een G in! 🧮",
    "invalid": "Die vraag snap ik niet fam, retry? 🤔"
}

# 🔹 Configuratie instellingen
class Settings(BaseSettings):
    """Applicatie instellingen."""
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = Field(10, description="Timeout voor AI requests in seconden")
    CACHE_EXPIRATION: int = Field(3600, description="Cache vervaltijd in seconden")
    MAX_RESPONSE_LENGTH: int = Field(200, description="Maximum lengte van antwoorden")
    MAX_TOKENS: int = Field(100, description="Maximum tokens voor AI response")
    ALLOWED_ORIGINS: list[str] = Field(
        ["https://wiskoro.nl", "https://www.wiskoro.nl"],
        description="Toegestane CORS origins"
    )

    class Config:
        env_file = ".env"

settings = Settings()

# 🔹 Versimpelde cache implementatie
class LocalCache:
    """Cache voor snelle antwoorden."""
    def __init__(self):
        self._items: Dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        """Haalt cache op als deze nog geldig is."""
        if key in self._items:
            value, timestamp = self._items[key]
            if time.time() - timestamp < settings.CACHE_EXPIRATION:
                return value
            del self._items[key]
        return None

    def set(self, key: str, value: str) -> None:
        """Slaat waarde op in cache."""
        self._items[key] = (value, time.time())

    def clear_expired(self) -> None:
        """Verwijdert verlopen cache items."""
        current_time = time.time()
        self._items = {
            k: v for k, v in self._items.items()
            if current_time - v[1] < settings.CACHE_EXPIRATION
        }

    @property
    def size(self) -> int:
        """Aantal items in cache."""
        return len(self._items)

cache = LocalCache()

# 🔹 Response validatie
def validate_response(response: str) -> str:
    """Valideer en kort indien nodig het antwoord in."""
    if len(response) > settings.MAX_RESPONSE_LENGTH:
        shortened = response[:settings.MAX_RESPONSE_LENGTH].rsplit('.', 1)[0] + '.'
        return shortened + ' 💯'
    return response

# 🔹 AI chatbot logica
async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """Haalt AI-respons op via Mistral API."""
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    prompt = f"{SYSTEM_PROMPT}\n\n❓ Vraag: {user_question}\n\n✅ Antwoord:"

    payload = {
        "model": "mistral-medium",
        "messages": [{"role": "system", "content": prompt}],
        "max_tokens": settings.MAX_TOKENS,
        "temperature": 0.7
    }

    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                json=payload
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()
            
            validated_response = validate_response(result)
            cache.set(user_question, validated_response)
            return validated_response, False

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=ERROR_MESSAGES["timeout"])
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES["service"])
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

# 🔹 Request model
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=500)

# 🔹 FastAPI app
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    description="Nederlandse wiskunde chatbot met straattaal"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 Endpoints
@app.get("/")
async def root():
    """Status check."""
    return {
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
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simplified health check."""
    return {"status": "healthy"}

# 🔹 Startup event
@app.on_event("startup")
async def startup_event():
    """Start cache cleanup taak."""
    async def cleanup_cache():
        while True:
            try:
                cache.clear_expired()
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Cache cleanup error: {str(e)}")

    asyncio.create_task(cleanup_cache())
    logger.info("✅ Wiskoro API started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info"
    )
