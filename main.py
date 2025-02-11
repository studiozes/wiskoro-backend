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
import random

# Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GenZ/straattaal vibes
STRAATTAAL = {
    "intro": [
        "Ey fam!", "Yo bro!", "Wagwan!", "Aight, luister!", "Hoor me ff!",
        "Check dit!", "Brooo, dit is easy!", "Dit fixen we!", "Ik help je wel!"
    ],
    "bevestiging": [
        "Makkie toch?", "Snap je?", "Check je die?", "Gekke wiskunde moves!", "Wiskunde goat!",
        "Fakka met je cijfers!", "No cap, dit klopt!", "Wiskunde baas!", "Eitje toch?"
    ],
}

# Wiskunde context
HAVO3_CONTEXT = {
    'algebra': {
        'termen': ['vergelijking', 'formule', 'functie', 'macht', 'wortel', 'logaritme'],
        'emoji': '📈'
    },
    'meetkunde': {
        'termen': ['hoek', 'driehoek', 'oppervlakte', 'pythagoras', 'sin', 'cos', 'tan'],
        'emoji': '📐'
    },
    'statistiek': {
        'termen': ['gemiddelde', 'mediaan', 'modus', 'histogram', 'boxplot'],
        'emoji': '📊'
    },
    'rekenen': {
        'termen': ['plus', 'min', 'keer', 'delen', 'procent', 'breuk', '+', '-'],
        'emoji': '🧮'
    }
}

# AI instellingen (ongewijzigd, want die werken goed!)
class Settings(BaseSettings):
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = Field(10, description="Timeout voor AI requests")
    MAX_TOKENS: int = Field(100, description="Max tokens voor AI response")
    ALLOWED_ORIGINS: list[str] = Field(
        ["https://wiskoro.nl", "https://www.wiskoro.nl"],
        description="Toegestane CORS origins"
    )
    class Config:
        env_file = ".env"

settings = Settings()

# Functie om wiskundevraag te herkennen
def identify_math_context(question: str) -> Tuple[str, str]:
    """Identificeer de juiste wiskunde context."""
    question_lower = question.lower()
    for context, data in HAVO3_CONTEXT.items():
        if any(term in question_lower for term in data['termen']):
            return context, data['emoji']
    return 'rekenen', '🧮'  # Default naar rekenen

# Functie om straattaal antwoord te genereren
def format_response(answer: str, emoji: str) -> str:
    """Maak het antwoord leuker en korter."""
    sentences = [s.strip() for s in answer.split('.') if s.strip()]
    if len(sentences) > 2:
        sentences = sentences[:2]
    result = f"{random.choice(STRAATTAAL['intro'])} {' '.join(sentences)} {emoji}"
    if random.random() < 0.3:
        result += f" {random.choice(STRAATTAAL['bevestiging'])}!"
    return result

# AI chatbot functie (zelfde API, geen aanpassingen!)
async def get_ai_response(user_question: str, client_ip: str) -> str:
    """Haalt AI-respons op met verbeterde stijl."""
    context, emoji = identify_math_context(user_question)
    full_prompt = f"Vraag: {user_question}\nAntwoord:"  # Simpele prompt
    
    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
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
            return format_response(result, emoji)
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        raise HTTPException(status_code=500, detail="Yo bro, iets ging mis! Probeer ff opnieuw! 🔧")

# FastAPI setup
app = FastAPI(title="Wiskoro API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Chat endpoint
@app.post("/chat")
async def chat(request: BaseModel, client_request: Request):
    """Wiskunde chatbot endpoint."""
    try:
        response = await get_ai_response(request.message, client_request.client.host)
        return {"response": response, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Yo bro, iets ging mis! Probeer ff opnieuw! 🔧")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("✅ Wiskoro API gestart!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
