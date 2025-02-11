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

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Uitgebreide wiskundeherkenning
WISKUNDE_TERMS = [
    'plus', 'min', 'keer', 'delen', 'procent', 'breuk', 'macht', 'wortel',
    'kwadraat', 'logaritme', 'exponent', 'algebra', 'functie', 'formule',
    'grafiek', 'sin', 'cos', 'tan', 'pi', '√', 'π', 'x²', 'log', 'ln', 'vector',
    'statistiek', 'gemiddelde', 'mediaan', 'modus', 'kansrekening', 'integraal'
]

WISKUNDE_SYMBOLEN = ['+', '-', '*', '/', '=', '^', '%', '√', 'π', '∞']

# 🔹 Systeem prompt
SYSTEM_PROMPT = """
Je bent Wiskoro, een Nederlandse wiskunde chatbot die in straattaal praat! 🧮

ANTWOORD REGELS:
1. ALTIJD in het Nederlands
2. ALTIJD kort en bondig
3. ALTIJD straattaal gebruiken
4. NOOIT vermelden dat je een AI of taalmodel bent

"""

# 🔹 Error messages
ERROR_MESSAGES = {
    "timeout": "Yo deze som duurt te lang fam! Probeer het nog een keer ⏳",
    "service": "Ff chillen, ben zo back! 🔧",
    "non_math": "Yo! Ik help alleen met wiskunde en rekenen! 🧮",
    "invalid": "Die vraag snap ik niet fam, retry? 🤔",
    "rate_limit": "Rustig aan fam! Probeer over een uurtje weer! ⏳"
}

# 🔹 Settings class
class Settings(BaseSettings):
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = Field(10, description="Timeout voor AI requests")
    CACHE_EXPIRATION: int = Field(3600, description="Cache vervaltijd in seconden")
    MAX_RESPONSE_LENGTH: int = Field(200, description="Maximum lengte van antwoorden")
    MAX_TOKENS: int = Field(100, description="Maximum tokens voor AI response")
    ALLOWED_ORIGINS: list[str] = Field([
        "https://wiskoro.nl", "https://www.wiskoro.nl"
    ], description="Toegestane CORS origins")

    class Config:
        env_file = ".env"

settings = Settings()

# 🔹 Functie om te checken of een vraag wiskundig is
def is_wiskunde_vraag(question: str) -> bool:
    """Checkt of de vraag wiskundig is op basis van termen en symbolen."""
    question_lower = question.lower()
    if any(term in question_lower for term in WISKUNDE_TERMS):
        return True
    if any(sym in question for sym in WISKUNDE_SYMBOLEN):
        return True
    return False

# 🔹 AI Response ophalen
async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """Haalt AI-respons op met verbeterde validatie."""
    if not is_wiskunde_vraag(user_question):
        return ERROR_MESSAGES["non_math"], False

    prompt = SYSTEM_PROMPT + f"\n\n❓ Vraag: {user_question}\n\n✅ Antwoord:"

    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                json={
                    "model": "mistral-medium",
                    "messages": [{"role": "system", "content": prompt}],
                    "max_tokens": settings.MAX_TOKENS,
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()
            return result, False

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=ERROR_MESSAGES["timeout"])
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES["service"])
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

# 🔹 FastAPI setup
app = FastAPI(title="Wiskoro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 API models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)

# 🔹 API endpoints
@app.get("/")
async def root():
    """Status check."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest, client_request: Request) -> Dict[str, Any]:
    """Wiskunde chatbot endpoint."""
    try:
        response, is_cached = await get_ai_response(request.message)
        return {"response": response, "cached": is_cached, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info"
    )
