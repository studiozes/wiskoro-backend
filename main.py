import os
import logging
import time
import asyncio
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 🔹 Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 🔹 Instellingen
class Settings(BaseSettings):
    """Applicatie instellingen"""
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

# 🔹 Cache systeem
class LocalCache:
    """Eenvoudige in-memory cache voor AI-antwoorden"""
    def __init__(self, expiration: int = settings.CACHE_EXPIRATION):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._expiration = expiration

    def get(self, key: str) -> Optional[str]:
        """Haal antwoord op uit cache"""
        if key in self._cache and time.time() - self._timestamps[key] < self._expiration:
            return self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        """Sla antwoord op in cache"""
        self._cache[key] = value
        self._timestamps[key] = time.time()

cache = LocalCache()

# 🔹 AI-verbinding met Mistral
async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """Haalt AI-antwoord op via Mistral API, met caching en duidelijke opmaak"""
    
    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    headers = {
        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-tiny",
        "messages": [
            {"role": "system", "content": (
                "Je bent een wiskundedocent die uitlegt in jongerentaal. "
                "Gebruik emoji's, straattaal en maak je uitleg super helder. "
                "Laat elke stap zien en geef een duidelijke opmaak met witregels.\n\n"
                "🔢 Als iemand een wiskundevraag stelt, beantwoord die stap voor stap.\n"
                "📖 Gebruik duidelijke tussenkopjes.\n"
                "💡 Formatteer berekeningen zoals **2 × 3 = 6**.\n"
                "🤔 Als de vraag niet wiskundig is, vraag dan: 'Bro, bedoel je iets met wiskunde? 🤔'"
            )},
            {"role": "user", "content": user_question}
        ]
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

        result = response_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        # Check of de AI een geldig antwoord gaf
        if not result or result.lower() == user_question.lower():
            raise ValueError("AI antwoord is ongeldig")

        # Cache het resultaat
        cache.set(user_question, result)
        return result, False

    except asyncio.TimeoutError:
        logger.error("⏳ AI request timeout")
        raise HTTPException(status_code=504, detail="Bro, dit is ff pittig. Probeer opnieuw! ⏳")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ AI request fout: {str(e)}")
        raise HTTPException(status_code=503, detail="De AI is even out of service, check later terug! 🔧")
    except Exception as e:
        logger.error(f"❌ Onverwachte fout: {str(e)}")
        raise HTTPException(status_code=500, detail="Yo, er ging iets mis! 😕")

# 🔹 Request model
class ChatRequest(BaseModel):
    """Validatiemodel voor een chatbericht"""
    message: str = Field(..., min_length=1, max_length=500)

# 🔹 FastAPI setup
app = FastAPI(
    title="Wiskoro API",
    version="1.2.0",
    description="AI chatbot voor wiskundige vraagstukken met Mistral"
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
    """Health check en API status"""
    return {
        "message": "🔥 Wiskoro API draait als een trein!",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Wiskunde chatbot met AI-ondersteuning.  
    - Geeft stap-voor-stap uitleg in **straattaal**  
    - Gebruikt **emoji's**  
    - Formatteert wiskundige formules mooi  
    - Vraagt om verduidelijking als de vraag niet wiskundig lijkt  
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
        raise HTTPException(status_code=500, detail="Yo, er ging iets mis met de AI 😕")

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Controleer of de API en cache werken"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_size": len(cache._cache)
    }

# 🔹 Cache cleanup bij startup
@app.on_event("startup")
async def startup_event():
    """Verwijdert verlopen cache items elke 5 minuten"""
    async def cleanup_cache():
        while True:
            cache._cache = {k: v for k, v in cache._cache.items() if time.time() - cache._timestamps[k] < settings.CACHE_EXPIRATION}
            await asyncio.sleep(300)

    try:
        asyncio.create_task(cleanup_cache())
        logger.info("✅ Startup complete!")
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info",
        reload=True
    )
