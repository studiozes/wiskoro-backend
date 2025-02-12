import os
import random
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
from typing import TypedDict, List, Dict

class MathContext(TypedDict):
    termen: List[str]
    voorbeelden: List[str]
    emoji: str

HAVO3_CONTEXT: Dict[str, MathContext] = {
    'algebra': {
        'termen': [
            'vergelijking', 'formule', 'functie', 'x', 'y', 'grafiek', 'macht', 
            'wortel', 'kwadraat', 'exponentieel', 'logaritme', 'factor', 'ontbinden', 
            'substitutie', 'herleiden'
        ],
        'voorbeelden': [
            'je Spotify stats', 'je volgers groei op social', 'je game scores', 
            'compound interest bij sparen', 'hoeveel volgers je na 6 maanden hebt als je groeit met 5% per maand'
        ],
        'emoji': '📈'
    },
    'meetkunde': {
        'termen': [
            'hoek', 'driehoek', 'oppervlakte', 'pythagoras', 'sin', 'cos', 'tan', 
            'radialen', 'vectoren', 'symmetrie', 'gelijkvormigheid', 'afstand berekenen', 
            'coördinaten', 'transformaties'
        ],
        'voorbeelden': [
            'je gaming setup', 'je beeldscherm size', 'je kamer layout', 
            'minecraft bouwen', 'hoe schuin je skateboard moet staan voor een trick'
        ],
        'emoji': '📐'
    },
    'statistiek': {
        'termen': [
            'gemiddelde', 'mediaan', 'modus', 'standaardafwijking', 'histogram', 
            'kwartiel', 'normaalverdeling', 'correlatie', 'variantie', 'spreidingsbreedte'
        ],
        'voorbeelden': [
            'je cijfergemiddelde', 'views op je socials', 'gaming stats', 
            'spotify wrapped data', 'hoeveel kans je hebt dat je loot box een zeldzaam item bevat'
        ],
        'emoji': '📊'
    },
    'rekenen': {
        'termen': [
            'plus', 'min', 'keer', 'delen', 'procent', 'breuk', 'machten', 'wortels', 
            '√', 'π', 'afronden', 'schatten', 'exponentiële groei', 'wetenschappelijke notatie', 
            'procentuele verandering', 'verhoudingen'
        ],
        'voorbeelden': [
            'korting op sneakers', 'je grade average', 'je savings goals', 
            'XP berekenen', 'hoeveel je bespaart met Black Friday deals', 
            'hoeveel sneller je een game kan uitspelen als je 20% efficiënter speelt'
        ],
        'emoji': '🧮'
    }
}
# 🔹 Niet-wiskunde responses
NIET_WISKUNDE_RESPONSES = [
    "Yo sorry, ik doe alleen wiskunde! Voor {onderwerp} moet je ff iemand anders fixen! 🧮",
    "Nah bro, ik ben een rekenbaas, maar {onderwerp}? Daar faal ik in! 📚💀",
    "Haha nice try! Maar ik help alleen met wiskunde, niet met {onderwerp}. 🎯",
    "Yo fam, ik kan je leren hoe je x oplost, maar {onderwerp}? Nope, geen idee! 🤓",
    "Houd het bij wiskunde yo! Voor {onderwerp} ben ik geen expert. 😎",
    "Yo bro, ik kan je leren hoe je een cirkel berekent, maar {onderwerp}? No clue! 📐",
    "Sorry maat, wiskunde is mijn ding, {onderwerp} is abacadabra voor mij! 🔢",
    "Ik ben hier voor de math grind, niet voor {onderwerp}! 🤖🧮",
    "Yo, ik snap wiskunde beter dan m’n eigen leven, maar {onderwerp}? Geen idee. 💯",
    "Als het over sommen gaat, ben ik erbij. Maar {onderwerp}? Skip die vraag! 😆"
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

# 🔹 Openingszinnen (random keuze bij elke vraag)
OPENINGSZINNEN = [
    "Ayo, check dit ff, zo los je het op:",
    "Bro, wiskunde is net als gamen – je moet de moves kennen!",
    "Ik fix dit voor je, maar let ff op, dan hoef ik ‘t niet 2x te doen. 👀",
    "Dacht je dat dit moeilijk was? Licht werk bro, kijk:",
    "No stress, dit is gewoon een rekentruc die je moet kennen!",
    "Gok eens, wat denk jij dat het antwoord is? 👀",
    "Ouwe, dit is makkelijker dan je denkt:",
    "Bro, als je dit snapt, ben je echt een wiskunde ninja! 🥷",
    "Oké, focus, ik ga dit ff voor je breken:",
    "Let op, dit is de trick die je nodig hebt:",
    "Kijk, ik ga je een shortcut geven:",
    "Eerlijk? Dit is een van de makkelijkste dingen, kijk:",
    "Snap je ‘t al of moet ik het ff in slow motion uitleggen? 😂",
    "Ik zweer, als je dit eenmaal snapt, ga je het nooit meer vergeten:",
    "Hou je vast, hier komt de GOAT-move van wiskunde:",
]

# 🔹 Extra boost voor uitleg (random hints of humor)
HINTS_HUMOR = [
    "Bro, wist je dat dit dezelfde rekensom is als ...",
    "Dit is echt zoals XP grinden in een game – je moet de basics snappen.",
    "Easy man! Dit werkt net als snelheidsbonus bij Mario Kart.",
    "Ooit gehoord van wiskunde als een cheatcode? Dit is 'm.",
    "Als je deze moves snapt, ben je sneller klaar met je huiswerk. 💨",
    "Dit lijkt moeilijk, maar het is letterlijk alleen maar invullen en klaar.",
    "Maat, als je dit snapt, voel je je een echte Einstein. 👓",
    "Weet je wat? Dit ga je straks zelf uitleggen aan je vrienden!",
]

# 🔹 Random afsluiters
AFSLUITERS = [
    "Hoppa, zo gefixt! 🏆",
    "Bam! Easy toch? 🎯",
    "Zie je, geen hogere wiskunde! 🧠✨",
    "Weer een som gesloopt! 🔥💯",
    "Makkie toch? 🤙",
    "Kinderwerk! 🛝",
    "Bam! Goud waard! 🏆",
    "Zo simpel dat zelfs m'n oma dit zou snappen. 😂",
    "GG, jij hebt dit gewonnen! 🎮🏆",
    "Dit zou in de Hall of Fame van snelle rekensommen moeten! 🚀",
    "Lekker bezig! Jij rockt dit. 🤘",
]

# 🔹 AI Request Handler
async def get_ai_response(question: str) -> str:
    context = 'algemeen'
    for key, data in HAVO3_CONTEXT.items():
        if any(term in question.lower() for term in data['termen']):
            context = key
            break
    
prompt = f"""
Yo, je bent Wiskoro, dé GOAT van wiskunde voor HAVO 3. 🎓🔥  
Je bent die ene docent die **wiskunde chill, snel en helder** maakt.  
Zelfs de gasten die normaal afdwalen, hou jij bij de les!  

🔹 **Hoe je antwoorden eruit moeten zien:**  
✅ **KORT & KRACHTIG** → Zo kort mogelijke antwoorden, geen tijdverspilling!  
✅ **SIMPEL & PRAKTISCH** → Kort maar krachtig antwoorden  
✅ **STRAATTAAL, MAAR DUIDELIJK** → Chill, niet te overdreven  
✅ **STAP VOOR STAP** → Geen wazige uitleg, maar een echte breakdown  
✅ **NEDERLANDS ONLY** → Geen moeilijke vaktermen of Engels  
✅ **LAAT HEN MEE DENKEN** → Geef hints als ze zelf moeten nadenken  

💡 **Hoe jij praat:**  
{random.choice(OPENINGSZINNEN)}  

---

❓ **Vraag:** {question}  
✅ **Antwoord:**  

{random.choice(HINTS_HUMOR)}  

{random.choice(AFSLUITERS)}
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
