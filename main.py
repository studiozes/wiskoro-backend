import os
import re
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

# 🔹 Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Wiskundige context helpers
MATH_CONTEXTS = {
    'basis': ['optellen', 'aftrekken', 'plus', 'min', '+', '-'],
    'vermenigvuldigen': ['keer', 'maal', '*', '×', 'vermenigvuldig'],
    'delen': ['delen', 'gedeeld', '/', '÷'],
    'breuken': ['breuk', 'noemer', 'teller', '/'],
    'procenten': ['procent', '%', 'percentage'],
    'meetkunde': ['oppervlakte', 'omtrek', 'volume', 'hoek', 'driehoek', 'vierkant', 'cirkel'],
    'vergelijkingen': ['vergelijking', '=', 'x', 'y', 'onbekende']
}

CONTEXT_PROMPTS = {
    'basis': "Laat zien hoe je optelt/aftrekt stap voor stap.",
    'vermenigvuldigen': "Splits grote berekeningen op in kleinere stappen.",
    'delen': "Laat zien hoe je deelt, rond af op 2 decimalen als nodig.",
    'breuken': "Vereenvoudig breuken waar mogelijk.",
    'procenten': "Reken eerst om naar decimalen voor berekeningen.",
    'meetkunde': "Noem altijd de gebruikte formule eerst.",
    'vergelijkingen': "Los stap voor stap op, werk netjes naar x toe.",
    'algemeen': "Leg stap voor stap uit."
}

SYSTEM_PROMPT = """Je bent Wiskoro, een Nederlandse wiskunde chatbot die in straattaal praat! 🧮

ANTWOORD REGELS:
1. ALTIJD in het Nederlands
2. ALTIJD kort en bondig (max 2 zinnen)
3. ALTIJD straattaal gebruiken
4. NOOIT vermelden dat je een AI of taalmodel bent
5. ALTIJD afsluiten met emoji

{context_prompt}

Voorbeeld:
❓ Vraag: 5 + 3
✅ Antwoord: "Yo! Dat is 8. 5 plus 3 is gewoon 8 toch! 🧮✨"
"""

ERROR_MESSAGES = {
    "timeout": "Yo deze som duurt te lang fam! Probeer het nog een keer ⏳",
    "service": "Ff chillen, ben zo back! 🔧",
    "non_math": "Yo! Ik help alleen met wiskunde en rekenen! 🧮",
    "invalid": "Die vraag snap ik niet fam, retry? 🤔",
    "rate_limit": "Rustig aan fam! Probeer over een uurtje weer! ⏳"
}

class Settings(BaseSettings):
    """Applicatie instellingen."""
    MISTRAL_API_KEY: str
    AI_TIMEOUT: int = 10
    CACHE_EXPIRATION: int = 3600
    MAX_RESPONSE_LENGTH: int = 200
    MAX_TOKENS: int = 100
    ALLOWED_ORIGINS: list[str] = ["https://wiskoro.nl", "https://www.wiskoro.nl"]

    class Config:
        env_file = ".env"

settings = Settings()

class LocalCache:
    def __init__(self):
        self._items: Dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._items and time.time() - self._items[key][1] < settings.CACHE_EXPIRATION:
            return self._items[key][0]
        return None

    def set(self, key: str, value: str) -> None:
        self._items[key] = (value, time.time())

cache = LocalCache()

async def get_ai_response(user_question: str) -> str:
    if cache.get(user_question):
        return cache.get(user_question)

    context = next((ctx for ctx, keywords in MATH_CONTEXTS.items() if any(k in user_question.lower() for k in keywords)), "algemeen")
    prompt = SYSTEM_PROMPT.format(context_prompt=CONTEXT_PROMPTS[context])

    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                json={
                    "model": "mistral-medium",
                    "messages": [{"role": "system", "content": f"{prompt}\n\n❓ Vraag: {user_question}\n\n✅ Antwoord:"}],
                    "max_tokens": settings.MAX_TOKENS,
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()

            if len(result) > settings.MAX_RESPONSE_LENGTH:
                result = result[:settings.MAX_RESPONSE_LENGTH].rsplit('.', 1)[0] + '! 💯'

            cache.set(user_question, result)
            return result

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=ERROR_MESSAGES["timeout"])
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES["service"])
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)

app = FastAPI(title="Wiskoro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

@app.get("/")
async def root():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    try:
        response = await get_ai_response(request.message)
        return {"response": response, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
