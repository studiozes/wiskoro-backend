import os
import re
import requests
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, TypedDict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 HAVO 3 Wiskunde Context
class MathContext(TypedDict):
    termen: List[str]
    voorbeelden: List[str]
    emoji: str

HAVO3_CONTEXT: Dict[str, MathContext] = {
    'algebra': {
        'termen': ['vergelijking', 'formule', 'functie', 'x', 'y', 'grafiek', 'macht', 'wortel', 'kwadraat', 'exponentieel', 'logaritme', 'factor', 'ontbinden'],
        'voorbeelden': ['je Spotify stats', 'je volgers groei op social', 'je game scores', 'compound interest bij sparen'],
        'emoji': '📈'
    },
    'meetkunde': {
        'termen': ['hoek', 'driehoek', 'oppervlakte', 'pythagoras', 'sin', 'cos', 'tan', 'radialen', 'vectoren', 'symmetrie', 'gelijkvormigheid'],
        'voorbeelden': ['je gaming setup', 'je beeldscherm size', 'je kamer layout', 'minecraft bouwen'],
        'emoji': '📐'
    },
    'statistiek': {
        'termen': ['gemiddelde', 'mediaan', 'modus', 'standaardafwijking', 'histogram', 'kwartiel', 'normaalverdeling'],
        'voorbeelden': ['je cijfergemiddelde', 'views op je socials', 'gaming stats', 'spotify wrapped data'],
        'emoji': '📊'
    },
    'rekenen': {
        'termen': ['plus', 'min', 'keer', 'delen', 'procent', 'breuk', 'machten', 'wortels', '√', 'π', 'afronden'],
        'voorbeelden': ['korting op sneakers', 'je grade average', 'je savings goals', 'XP berekenen'],
        'emoji': '🧮'
    }
}

# 🔹 Niet-wiskunde responses
NIET_WISKUNDE_RESPONSES = [
    "Yo sorry! Wiskunde is mijn ding, voor {onderwerp} moet je bij iemand anders zijn! 🧮",
    "Brooo, ik ben een wiskundenerd! Voor {onderwerp} kan ik je niet helpen! 📚",
    "Nah fam, alleen wiskunde hier! {onderwerp} is niet mijn expertise! 🤓",
    "Wiskunde? Bet! Maar {onderwerp}? Daar snap ik niks van! 🎯"
]

# 🔹 API instellingen
class Settings(BaseSettings):
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = 10
    CACHE_EXPIRATION: int = 3600
    MAX_RESPONSE_LENGTH: int = 200
    MAX_TOKENS: int = 100
    ALLOWED_ORIGINS: List[str] = ["https://wiskoro.nl", "https://www.wiskoro.nl"]
    class Config:
        env_file = ".env"

settings = Settings()

# 🔹 AI Request Handler
async def get_ai_response(question: str) -> str:
    context = 'algemeen'
    for key, data in HAVO3_CONTEXT.items():
        if any(term in question.lower() for term in data['termen']):
            context = key
            break
    
    prompt = f"Je bent een wiskundeleraar en legt dingen uit in jongerentaal. {question}\nAntwoord:" 
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            json={
                "model": "mistral-medium",
                "messages": [{"role": "system", "content": prompt}],
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.1
            },
            timeout=settings.AI_TIMEOUT
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="AI service is even niet bereikbaar. Probeer later nog eens! 🛠️")

# 🔹 FastAPI Setup
app = FastAPI(title="Wiskoro API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])

# 🔹 API Models
class ChatRequest(BaseModel):
    message: str

# 🔹 API Endpoints
@app.post("/chat")
async def chat(request: ChatRequest):
    response = await get_ai_response(request.message)
    return {"response": response}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
