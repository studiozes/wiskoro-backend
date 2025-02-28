import os
import requests
import logging
import asyncio
from datetime import datetime
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import random

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 API instellingen
class Settings(BaseSettings):
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = 15
    MAX_TOKENS: int = 200
    ALLOWED_ORIGINS: List[str] = ["https://wiskoro.nl", "https://www.wiskoro.nl"]
    
    class Config:
        env_file = ".env"

settings = Settings()

# 🔹 FastAPI Setup
app = FastAPI(title="Wiskoro API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 🔹 Wiskunde feitjes prompt
FACT_PROMPT = """
Yo, je bent Wiskoro, de ultieme wiskunde GOAT voor HAVO 3. 🎓🔥  
Je geeft telkens **één** wiskundefeitje op een **leuke, snelle en humoristische** manier.  
✅ **Max 3 zinnen**  
✅ **GenZ/straattaal** gebruiken  
✅ **Geen moeilijke vaktermen zonder uitleg**  
✅ **NEDERLANDS ONLY!**  

Drop nu een random wiskundefeitje, let’s go:  
"""

# 🔹 AI Request Handler voor feiten
async def get_wiskunde_feit() -> str:
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            json={
                "model": "mistral-medium",
                "messages": [{"role": "system", "content": FACT_PROMPT}],
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.7
            },
            timeout=settings.AI_TIMEOUT
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="AI service is even niet bereikbaar. Probeer later nog eens! 🛠️")

# 🔹 API Endpoints
@app.get("/fact")
async def get_fact():
    feit = await get_wiskunde_feit()
    return {"fact": feit}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
