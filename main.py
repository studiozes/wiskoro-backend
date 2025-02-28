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
import random

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Wiskunde Feiten
WISKUNDE_FEITEN = [
    "Pi is oneindig lang en niemand kent het exacte einde. 🤯",
    "Wiskunde is overal, zelfs in je TikTok-algoritme! 🧠📱",
    "Een vierkant getal is een getal dat ontstaat door een getal met zichzelf te vermenigvuldigen. 4 = 2×2! 🔢",
    "De kans dat je exact dezelfde 52-kaarten deck schudt als iemand anders is praktisch 0. ♠️♥️",
    "De stelling van Pythagoras wordt al 2500 jaar gebruikt! 📐",
    "Exponenten groeien sneller dan je TikTok views. 🚀",
    "Een cirkel heeft oneindig veel symmetrieassen. 🔄",
    "Wist je dat de som van alle getallen van 1 tot 100 gelijk is aan 5050? 🔢",
    "De Fibonacci-reeks komt voor in bloemen, kunst en zelfs muziek! 🎵",
    "Als je een getal door 9 deelt en de som van de cijfers is deelbaar door 9, dan is het originele getal ook deelbaar door 9. 🤯"
]

# 🔹 API-instellingen
class Settings(BaseSettings):
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = 15
    CACHE_EXPIRATION: int = 3600
    MAX_RESPONSE_LENGTH: int = 500
    MAX_TOKENS: int = 200
    ALLOWED_ORIGINS: List[str] = ["https://wiskoro.nl", "https://www.wiskoro.nl"]
    class Config:
        env_file = ".env"

settings = Settings()

# 🔹 AI Request Handler
async def get_ai_response(question: str) -> str:
    prompt = f"""
Yo, jij bent Wiskoro, de ultieme wiskunde GOAT voor HAVO 3. 🎓🔥  
Jouw taak? Wiskunde simpel, snel en begrijpelijk maken.  

🔹 **Hoe je antwoorden eruit moeten zien:**  
✅ **Kort & krachtig** → Recht op het doel af.  
✅ **Straattaal, maar duidelijk** → Chill, niet te overdreven.  
✅ **Stap voor stap uitleg** → Maar niet te langdradig.  
✅ **Nederlands ONLY** → Geen Engels of moeilijke vaktermen.  

---

❓ **Vraag:** {question}  
✅ **Antwoord:**
"""
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            json={
                "model": "mistral-medium",
                "messages": [{"role": "system", "content": prompt}],
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.3
            },
            timeout=settings.AI_TIMEOUT
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="AI service is even niet bereikbaar. Probeer later nog eens! 🛠️")

# 🔹 FastAPI Setup
app = FastAPI(title="Wiskoro API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 API Models
class ChatRequest(BaseModel):
    message: str

# 🔹 API Endpoints
@app.post("/chat")
async def chat(request: ChatRequest):
    response = await get_ai_response(request.message)
    return {"response": response}

@app.get("/fact")
async def get_fact():
    fact = random.choice(WISKUNDE_FEITEN)
    return {"response": fact}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
