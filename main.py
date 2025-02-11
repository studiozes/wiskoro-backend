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
HAVO3_CONTEXT = {
    'algebra': {
        'termen': ['vergelijking', 'formule', 'functie', 'x', 'y', 'grafiek', 'macht', 'wortel', 'kwadraat'],
        'emoji': '📈'
    },
    'meetkunde': {
        'termen': ['hoek', 'driehoek', 'oppervlakte', 'pythagoras', 'sin', 'cos', 'tan', 'vectoren'],
        'emoji': '📐'
    },
    'statistiek': {
        'termen': ['gemiddelde', 'mediaan', 'modus', 'standaardafwijking', 'histogram', 'boxplot'],
        'emoji': '📊'
    },
    'rekenen': {
        'termen': ['plus', 'min', 'keer', 'delen', 'procent', 'breuk', '+', '-', '*', '/', 'machten', '√', 'π'],
        'emoji': '🧮'
    }
}

# 🔹 Error messages
ERROR_MESSAGES = {
    "timeout": "Yo, deze som duurt te lang! Probeer ff opnieuw. ⏳",
    "service": "Ik ben ff afgeleid, probeer later nog eens. 🔧",
    "non_math": "Yo! Ik help alleen met wiskunde en rekenen! 🧮",
    "invalid": "Die vraag snap ik niet, bro. Kan je het anders zeggen? 🤔",
    "rate_limit": "Rustig aan fam! Probeer later nog een keer. ⏳"
}

# 🔹 Settings class
class Settings(BaseSettings):
    """Applicatie instellingen."""
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = Field(10, description="Timeout voor AI requests")
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

# 🔹 Wiskunde herkenning
def is_math_question(question: str) -> bool:
    """Checkt of een vraag over wiskunde gaat."""
    return any(term in question.lower() for ctx in HAVO3_CONTEXT.values() for term in ctx['termen'])

# 🔹 AI response ophalen
async def get_ai_response(user_question: str, client_ip: str) -> Tuple[str, bool]:
    """Haalt AI-respons op en verwerkt deze naar correct formaat."""
    if not is_math_question(user_question):
        return ERROR_MESSAGES["non_math"], False

    prompt = f"Je bent een wiskundeleraar die kort en bondig uitlegt in GenZ-taal. " \
             f"Beantwoord deze wiskundevraag in max 2 zinnen:\n\nVraag: {user_question}\n\nAntwoord:"

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

            # Zorg dat het antwoord geen Engelse vertalingen bevat
            result = re.sub(r"\(Translation:.*?\)", "", result)

            # Kort en bondig houden
            sentences = [s.strip() for s in result.split('.') if s.strip()]
            result = '. '.join(sentences[:2])

            # Emoji toevoegen
            for context, data in HAVO3_CONTEXT.items():
                if any(term in user_question.lower() for term in data["termen"]):
                    result += f" {data['emoji']}"
                    break

            return result.strip(), False

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=ERROR_MESSAGES["timeout"])
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES["service"])
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

# 🔹 API models
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=500)

# 🔹 FastAPI app
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    description="Nederlandse wiskunde chatbot met GenZ-taal"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 API endpoints
@app.get("/")
async def root():
    """Status check."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest, client_request: Request) -> Dict[str, Any]:
    """Wiskunde chatbot endpoint."""
    try:
        response, is_cached = await get_ai_response(request.message, client_request.client.host)
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
    """Start logging."""
    logger.info("✅ Wiskoro API gestart")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info"
    )
