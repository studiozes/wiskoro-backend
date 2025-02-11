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

# 🔹 Random toetsvragen
TOETS_VRAGEN = [
    "Wat is 7 × 8?",
    "Los op: 5x - 3 = 12",
    "Wat is de omtrek van een cirkel met straal 6?",
    "Hoeveel graden is een rechte hoek?",
    "Wat is het decimale getal van 1/4?",
    "Bereken de oppervlakte van een vierkant met zijde 5 cm."
]

# 🔹 Systeem prompt template
SYSTEM_PROMPT = """Je bent Wiskoro, een Nederlandse wiskunde chatbot die in straattaal praat! 🧮

ANTWOORD REGELS:
1. ALTIJD in het Nederlands
2. ALTIJD kort en bondig (max 2 zinnen)
3. ALTIJD straattaal gebruiken
4. NOOIT vermelden dat je een AI of taalmodel bent
5. ALTIJD afsluiten met emoji

Bij niet-wiskunde vragen:
"Yo! Sorry fam, ik help alleen met wiskunde en rekenen! 🧮"

Bij onduidelijke vragen:
"Yo fam, snap je vraag niet helemaal. Kun je het anders zeggen? 🤔"

{context_prompt}
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
    """Applicatie instellingen."""
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = Field(10, description="Timeout voor AI requests")
    CACHE_EXPIRATION: int = Field(3600, description="Cache vervaltijd in seconden")
    MAX_TOKENS: int = Field(100, description="Maximum tokens voor AI response")
    ALLOWED_ORIGINS: list[str] = Field(
        ["https://wiskoro.nl", "https://www.wiskoro.nl"],
        description="Toegestane CORS origins"
    )

    class Config:
        env_file = ".env"

settings = Settings()

# 🔹 AI Response functie
async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """Haalt AI-respons op met validatie en toetsvragen."""
    
    # Check of het een wiskundevraag is
    if not any(word in user_question.lower() for word in sum(MATH_CONTEXTS.values(), [])):
        return ERROR_MESSAGES["non_math"], False

    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    # Identificeer context en bouw prompt
    context = next((ctx for ctx, words in MATH_CONTEXTS.items() if any(word in user_question.lower() for word in words)), "algemeen")
    context_prompt = f"Je helpt een leerling uit HAVO 3 met {context} wiskunde."

    # Bouw volledige prompt
    full_prompt = f"{SYSTEM_PROMPT.format(context_prompt=context_prompt)}\n\n❓ Vraag: {user_question}\n\n✅ Antwoord:"

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            json={
                "model": "mistral-medium",
                "messages": [{"role": "system", "content": full_prompt}],
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.1
            }
        )
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"].strip()

        # Toetsvraag toevoegen met 30% kans
        if random.random() < 0.3:
            result += f" Maar ff checken, weet jij: {random.choice(TOETS_VRAGEN)} 🤔"

        cache.set(user_question, result)
        return result, False

    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES["service"])
    except Exception:
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

# 🔹 FastAPI app setup
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

# 🔹 API modellen
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=500)

# 🔹 API endpoints
@app.get("/")
async def root():
    """Status check."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
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

# 🔹 Startup event
@app.on_event("startup")
async def startup_event():
    """Start log bericht."""
    logger.info("✅ Wiskoro API gestart!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
