import os
import re
import random
import requests
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 HAVO 3 onderwerpen en context
HAVO3_TOPICS = {
    'algebra': {
        'onderwerpen': ['vergelijkingen', 'ongelijkheden', 'kwadratische functies'],
        'toetsvragen': [
            "Los op: 2x + 5 = 13",
            "Vereenvoudig: 3(x + 2) - 2(x - 1)",
            "Los op: x² - 4 = 20"
        ],
        'voorbeelden': [
            "Check deze: 3x + 1 = 7",
            "Deze is nice: x² + 2x = 15"
        ]
    },
    'meetkunde': {
        'onderwerpen': ['pythagoras', 'goniometrie', 'oppervlakte', 'inhoud'],
        'toetsvragen': [
            "In een rechthoekige driehoek is sin(30°) = ?",
            "Pythagoras: Als a=3 en b=4, wat is dan c?",
            "Bereken de oppervlakte van een cirkel met r=5"
        ],
        'voorbeelden': [
            "Net als bij een driehoek met zijden 3, 4 en 5",
            "Zoals bij een cirkel met straal 2"
        ]
    },
    'statistiek': {
        'onderwerpen': ['diagrammen', 'gemiddelde', 'mediaan', 'modus'],
        'toetsvragen': [
            "Wat is de mediaan van: 4, 7, 8, 8, 9?",
            "Bereken het gemiddelde van: 12, 15, 18, 21",
            "Wat is de modus van: 1, 2, 2, 3, 2, 4?"
        ],
        'voorbeelden': [
            "Net als bij getallen 2, 4, 4, 6, 8",
            "Zoals bij een reeks: 10, 20, 20, 30"
        ]
    },
    'functies': {
        'onderwerpen': ['lineaire functies', 'parabolen', 'grafieken'],
        'toetsvragen': [
            "Wat is het snijpunt met de y-as bij y = 2x + 3?",
            "Bij y = x² + 1, wat is de laagste waarde van y?",
            "Als y = 3x - 6, wat is x als y = 0?"
        ],
        'voorbeelden': [
            "Zoals bij y = 2x + 1",
            "Net als bij y = x² - 4"
        ]
    }
}

# 🔹 GenZ/Straattaal templates
STRAATTAAL = {
    'intro': [
        "Yo fam!",
        "Sheesh!",
        "Aight!",
        "Let's go!"
    ],
    'correct': [
        "Het antwoord is {antwoord}, sws!",
        "Easy: {antwoord}, no cap!",
        "{antwoord}, fr fr!",
        "Check it: {antwoord}!"
    ],
    'uitleg': [
        "Kijk, {uitleg}",
        "Want {uitleg}",
        "{uitleg}, snap je?",
        "{uitleg}, easy peasy!"
    ],
    'toets_intro': [
        "Maar ff checken:",
        "Quick vraagje tho:",
        "Test je skills:",
        "Prove je worth:"
    ],
    'niet_wiskunde': [
        "Yo! Sorry fam, ik ga alleen over wiskunde en rekenen! 🧮",
        "Nah g, alleen wiskunde hier! Kom met een rekensom! 🔢",
        "Dit ain't it chief, ik doe alleen wiskunde! 📚"
    ],
    'onduidelijk': [
        "Yo fam, snap je vraag niet helemaal. Kun je het anders zeggen? 🤔",
        "Deze is wazig g, probeer het nog een keer! 💭",
        "Not sure wat je bedoelt fam, rephrase? 🤷"
    ]
}

# 🔹 Systeem prompt
SYSTEM_PROMPT = """Je bent Wiskoro, de Nederlandse wiskunde G voor HAVO 3! 🧮

REGELS:
1. ALTIJD Nederlands met GenZ/straattaal
2. MAX 2 zinnen per antwoord
3. Houd het HAVO 3 niveau
4. NOOIT vermelden dat je AI bent
5. ALTIJD emoji's gebruiken

ANTWOORD OPBOUW:
1. Start met "Yo!" of "Sheesh!"
2. Geef antwoord in straattaal
3. Korte uitleg
4. Soms een toetsvraag
5. Emoji's

VOORBEELDEN:
- "Yo! Antwoord = 25 sws. Area = length × width, no cap! 📐"
- "Sheesh, met Pythagoras wordt dat 5! Easy: a² + b² = c² 🔥"

{context_prompt}
"""

# 🔹 Settings en configuratie blijft ongewijzigd
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

# 🔹 Cache implementatie blijft ongewijzigd
class LocalCache:
    """Cache voor snelle antwoorden."""
    def __init__(self):
        self._items: Dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._items:
            value, timestamp = self._items[key]
            if time.time() - timestamp < settings.CACHE_EXPIRATION:
                return value
            del self._items[key]
        return None

    def set(self, key: str, value: str) -> None:
        self._items[key] = (value, time.time())

cache = LocalCache()

# 🔹 Topic detector
def detect_topic(question: str) -> Optional[str]:
    """Detecteer het HAVO 3 onderwerp van de vraag."""
    question_lower = question.lower()
    
    for topic, data in HAVO3_TOPICS.items():
        if any(onderwerp in question_lower for onderwerp in data['onderwerpen']):
            return topic
    
    # Check voor basis rekenen
    if any(word in question_lower for word in ['+', '-', '*', '/', 'keer', 'gedeeld', 'plus', 'min']):
        return 'algebra'
        
    return None

# 🔹 Antwoord generator
def generate_response(topic: str, answer: str) -> str:
    """Genereer een GenZ antwoord met mogelijk een toetsvraag."""
    intro = random.choice(STRAATTAAL['intro'])
    response = random.choice(STRAATTAAL['correct']).format(antwoord=answer)
    
    # 30% kans op toetsvraag
    if topic in HAVO3_TOPICS and random.random() < 0.3:
        toets_intro = random.choice(STRAATTAAL['toets_intro'])
        toets_vraag = random.choice(HAVO3_TOPICS[topic]['toetsvragen'])
        response += f" {toets_intro} {toets_vraag}"
    
    # Voeg emoji's toe
    emojis = "🧮✨💯🔥"
    response += f" {random.choice(emojis)}"
    
    return f"{intro} {response}"

# 🔹 AI Response functie
async def get_ai_response(user_question: str) -> Tuple[str, bool]:
    """Haalt AI-respons op met HAVO 3 context."""
    
    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    # Detecteer onderwerp
    topic = detect_topic(user_question)
    if not topic:
        return random.choice(STRAATTAAL['niet_wiskunde']), False

    # Bouw context
    context_prompt = f"Je helpt een HAVO 3 leerling met {topic}."
    if topic in HAVO3_TOPICS:
        context_prompt += f" Gebruik voorbeelden zoals: {random.choice(HAVO3_TOPICS[topic]['voorbeelden'])}"

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
        
        # Post-process het antwoord
        final_response = generate_response(topic, result)
        cache.set(user_question, final_response)
        return final_response, False

    except requests.exceptions.RequestException as e:
        logger.error(f"API error: {str(e)}")
        raise HTTPException(status_code=503, detail="Ff chillen, ben zo back! 🔧")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return random.choice(STRAATTAAL['onduidelijk']), False

# 🔹 FastAPI app setup blijft ongewijzigd
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

# 🔹 API models blijven ongewijzigd
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=500)

# 🔹 Endpoints blijven ongewijzigd
@app.get("/")
async def root():
    """Status check."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """Wiskunde chatbot endpoint."""
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
        logger.error(f"Chat error: {str(e)}")
        return {
            "response": random.choice(STRAATTAAL['onduidelijk']),
            "cached": False,
            "timestamp": datetime.utcnow().isoformat()
        }

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
