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

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Wiskundige context helpers
HAVO3_CONTEXT = {
    'algebra': {
        'termen': ['vergelijking', 'formule', 'functie', 'x', 'y', 'grafiek',
                   'macht', 'wortel', 'kwadraat', 'exponentieel', 'logaritme',
                   'log', 'ln', 'factor', 'ontbinden'],
        'emoji': '📈'
    },
    'meetkunde': {
        'termen': ['hoek', 'driehoek', 'oppervlakte', 'pythagoras', 'sin', 'cos',
                   'tan', 'radialen', 'goniometrie', 'vectoren', 'symmetrie',
                   'congruentie', 'gelijkvormigheid'],
        'emoji': '📐'
    },
    'statistiek': {
        'termen': ['gemiddelde', 'mediaan', 'modus', 'standaardafwijking',
                   'histogram', 'boxplot', 'spreidingsbreedte', 'kwartiel',
                   'normaalverdeling', 'steekproef'],
        'emoji': '📊'
    },
    'rekenen': {
        'termen': ['plus', 'min', 'keer', 'delen', 'procent', 'breuk', '+', '-', '*', '/',
                   'machten', 'wortels', '√', 'π', 'afronden', 'schatten',
                   'wetenschappelijke notatie'],
        'emoji': '🧮'
    }
}

NIET_WISKUNDE_RESPONSES = [
    "Yo sorry! Wiskunde is mijn ding, voor {onderwerp} moet je bij iemand anders zijn! 🧮",
    "Brooo, ik ben een wiskundenerd! Voor {onderwerp} kan ik je niet helpen! 📚",
    "Nah fam, alleen wiskunde hier! {onderwerp} is niet mijn expertise! 🤓",
    "Wiskunde? Bet! Maar {onderwerp}? Daar snap ik niks van! 🎯"
]

def get_niet_wiskunde_response(vraag: str) -> str:
    onderwerpen = {
        'muziek': ['muziek', 'lied', 'artiest', 'spotify', 'nummer'],
        'sport': ['voetbal', 'sport', 'training', 'wedstrijd'],
        'gaming': ['game', 'fortnite', 'minecraft', 'console'],
        'social': ['insta', 'snap', 'tiktok', 'social'],
        'liefde': ['liefde', 'relatie', 'verkering', 'dating']
    }
    
    vraag_lower = vraag.lower()
    for onderwerp, keywords in onderwerpen.items():
        if any(keyword in vraag_lower for keyword in keywords):
            return random.choice(NIET_WISKUNDE_RESPONSES).format(onderwerp=onderwerp)
    
    return "Yo sorry! Ik help alleen met wiskunde en rekenen! 🧮"

def identify_math_context(question: str) -> Tuple[str, str]:
    question_lower = question.lower()
    for context, data in HAVO3_CONTEXT.items():
        if any(term in question_lower for term in data['termen']):
            return context, data['emoji']
    return 'algemeen', '💡'

def validate_math_question(question: str) -> bool:
    return any(term in question.lower() for term in sum([c['termen'] for c in HAVO3_CONTEXT.values()], []))

def format_response(answer: str, emoji: str) -> str:
    answer = re.sub(r'(als AI|als model|als taalmodel|This response).*', '', answer, flags=re.IGNORECASE)
    sentences = [s.strip() for s in answer.split('.') if s.strip()]
    
    if len(sentences) > 2:
        sentences = sentences[:2]
    
    response = f"{random.choice(['Yo!', 'Bro!', 'Ey fam!'])} {'. '.join(sentences)}"
    
    if random.random() < 0.3:
        response += f" {random.choice(['Snappie?', 'Volg je me?', 'Easy toch?'])}!"
    
    if not any(char in response for char in ['🧮', '📐', '📈', '📊', '💯']):
        response += f" {emoji}"
    
    return response

# 🔹 API-instellingen (GEEN WIJZIGINGEN HIER)
class Settings(BaseSettings):
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = 10
    MAX_TOKENS: int = 100
    ALLOWED_ORIGINS: list[str] = Field(["https://wiskoro.nl", "https://www.wiskoro.nl"])

settings = Settings()

app = FastAPI(title="Wiskoro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)

@app.get("/")
async def root():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest, client_request: Request) -> Dict[str, Any]:
    vraag = request.message.strip()
    
    if not validate_math_question(vraag):
        return {"response": get_niet_wiskunde_response(vraag)}

    context, emoji = identify_math_context(vraag)

    full_prompt = f"Yo, check dit: {vraag}\n\n✅ Antwoord:"

    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                json={"model": "mistral-medium", "messages": [{"role": "system", "content": full_prompt}], "max_tokens": settings.MAX_TOKENS}
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()

            return {"response": format_response(result, emoji)}

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Yo deze som duurt te lang fam! Probeer het nog een keer ⏳")
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Ff chillen, ben zo back! 🔧")
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        raise HTTPException(status_code=500, detail="Er ging iets mis fam! 🤔")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
