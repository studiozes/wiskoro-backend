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
        'termen': ['vergelijking', 'formule', 'functie', 'x', 'y', 'grafiek', 'macht', 'wortel', 'kwadraat', 'exponentieel'],
        'voorbeelden': ['je Spotify stats', 'je game scores', 'je volgers groei op social'],
        'emoji': '📈'
    },
    'meetkunde': {
        'termen': ['hoek', 'driehoek', 'oppervlakte', 'pythagoras', 'sin', 'cos', 'tan'],
        'voorbeelden': ['je gaming setup', 'je beeldscherm size', 'minecraft bouwen'],
        'emoji': '📐'
    },
    'statistiek': {
        'termen': ['gemiddelde', 'mediaan', 'modus', 'standaardafwijking'],
        'voorbeelden': ['je cijfergemiddelde', 'views op je socials', 'gaming stats'],
        'emoji': '📊'
    },
    'rekenen': {
        'termen': ['plus', 'min', 'keer', 'delen', 'procent', 'breuk', 'machten', 'wortels', 'π'],
        'voorbeelden': ['korting op sneakers', 'je grade average', 'XP berekenen'],
        'emoji': '🧮'
    }
}

# 🔹 Niet-wiskunde responses
NIET_WISKUNDE_RESPONSES = [
    "Yo sorry, hier doen we alleen aan wiskunde! Geen politiek, geen gossip, alleen sommen. 🧮",
    "Haha nice try! Maar als het geen wiskunde is, dan ben ik out. 🎯",
    "Bro, ik ben hier om te rekenen, geen Wikipedia. Gooi een som en ik fix het! 🔢",
    "Wiskunde = mijn ding. Alles daarbuiten? Nope, daar weet ik niks van. 🤓",
    "Maat, ik doe alleen cijfers en formules. De rest laat ik aan Google over! 💡"
]

# 🔹 API instellingen (NIET GEWIJZIGD)
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

# 🔹 AI-taalfilter
def fix_language(answer: str) -> str:
    """Checkt of het antwoord Engelse woorden bevat en corrigeert dit."""
    english_words = ["the", "is", "answer", "math", "problem", "solution", "explanation", "question"]
    if any(word in answer.lower() for word in english_words):
        return "Yo, dit ging ff mis! Ik praat **ALLEEN** Nederlands! 🔥🧮 Stel een wiskundeprobleem en ik fix het voor je!"
    return answer

def remove_prompt_explanation(answer: str) -> str:
    """Verwijdert zinnen die uitleg geven over het prompt of de AI."""
    patterns = [
        r"volgens de prompt.*?",
        r"volgens de instructies.*?",
        r"als AI-model.*?",
        r"ik ben een AI.*?",
        r"ik ben geprogrammeerd om.*?",
        r"ik mag alleen.*?",
        r"ik ben getraind om.*?"
    ]
    for pattern in patterns:
        answer = re.sub(pattern, "", answer, flags=re.IGNORECASE)
    return answer.strip()

# 🔹 AI Request Handler
async def get_ai_response(question: str) -> str:
    context = 'algemeen'
    for key, data in HAVO3_CONTEXT.items():
        if any(term in question.lower() for term in data['termen']):
            context = key
            break

    if context == 'algemeen':
        return NIET_WISKUNDE_RESPONSES[0]

    prompt = f"""
Yo, jij bent Wiskoro, de ultieme wiskunde GOAT voor HAVO 3. 🎓🔥  
Je bent die ene leraar die niet lult, maar **gewoon fixt dat iedereen het snapt**.  

🔹 **Hoe je antwoorden eruit moeten zien:**  
✅ KORT & KRACHTIG → Recht op het doel af.  
✅ SIMPEL & PRAKTISCH → Duidelijk en toepasbaar.  
✅ STRAATTAAL, MAAR DUIDELIJK → Chill, begrijpelijk en met een luchtige vibe.  
✅ STAP VOOR STAP (ALS NODIG) → Breakdown in max 2 stappen.  
✅ **NEDERLANDS ONLY** → Engels is VERBODEN.  
✅ **ALTIJD VARIATIE** → Niet steeds dezelfde openingszin of afsluiter.  

💡 **Hoe jij praat:**  
- "Ayo, check dit ff, zo los je het op:"  
- "Dacht je dat dit moeilijk was? Nah man, check dit:"  
- "Ik drop ff een cheatcode voor je, hou je vast:"  
- "Dit is gewoon straight math logic, kijk mee:"  

🔥 **Extra boost voor je uitleg:**  
📌 Gebruik relatable voorbeelden – korting op sneakers, level-ups in games.  
📌 Zet leerlingen aan het denken – “Wat als dit getal ineens verdubbelt?”  
📌 Waarschuw voor valkuilen – “Deze fout zie ik zó vaak op toetsen!”  

🎭 **Afsluiters die random gebruikt mogen worden:**  
- "Hoppa, zo gefixt! 🏆"  
- "Bam! Easy toch? 🎯"  
- "Zie je, geen hogere wiskunde! 🧠✨"  

---

❓ **Vraag:** {question}  
✅ **Antwoord:**
"""
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            json={"model": "mistral-medium", "messages": [{"role": "system", "content": prompt}], "max_tokens": settings.MAX_TOKENS, "temperature": 0.3},
            timeout=settings.AI_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"].strip()
        result = fix_language(result)
        result = remove_prompt_explanation(result)
        return result
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="AI service is even niet bereikbaar. Probeer later nog eens! 🛠️")

# 🔹 FastAPI Setup
app = FastAPI(title="Wiskoro API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])

@app.post("/chat")
async def chat(request: ChatRequest):
    response = await get_ai_response(request.message)
    return {"response": response}
