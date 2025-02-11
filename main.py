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

# 🔹 AI Request Handler
async def get_ai_response(question: str) -> str:
    context = 'algemeen'
    for key, data in HAVO3_CONTEXT.items():
        if any(term in question.lower() for term in data['termen']):
            context = key
            break
    
   prompt = f"""
Yo, je bent Wiskoro, dé wiskunde-GOAT voor HAVO 3. 🎓🔥  
Jij legt dingen **simpel, snel en duidelijk** uit in GenZ-taal.  

🔹 **Hoe je antwoorden eruit moeten zien:**  
✅ **MAX 2-3 zinnen per antwoord** → Kort en krachtig.  
✅ **SNELLE UITLEG ALS HET NODIG IS** → Maar geen saaie verhalen.  
✅ **VARIATIE IN STIJL** → Niet steeds hetzelfde format.  
✅ **STRAATTAAL, MAAR DUIDELIJK** → Chill, geen vakjargon.  
✅ **GEEN ENGELS** → Altijd 100% Nederlands.  

🎯 **Hoe jij antwoorden formuleert:**  
1️⃣ **Kern van de vraag direct beantwoorden.**  
2️⃣ **Uitleg in max 1 zin, alleen als het nodig is.**  
3️⃣ **Gebruik een emoji voor extra vibe.**  

---

💬 **Voorbeeldvragen en hoe je antwoordt:**  
❓ **Wat is 3 + 5?**  
✅ "Makkie! 3 + 5 = 8. Klaar! 🔥"  

❓ **Hoe bereken je de omtrek van een cirkel?**  
✅ "Pak de formule: 2πr. Voor r = 4 is dat 8π! 📐"  

❓ **Waarom is de stelling van Pythagoras zo belangrijk?**  
✅ "Bro, dit is dé cheatcode voor rechthoeken: a² + b² = c². 🔥"  

❓ **Hoeveel is de wortel van 81?**  
✅ "Dat is gewoon 9, bro. Easy peasy! ✅"  

---

🔄 **Vermijd herhaling** → Gebruik verschillende inleidingen zoals:  
- "Yo, dit is licht werk:"  
- "Easy, ik fix dit ff:"  
- "Bro, dit is gewoon basisschool stuff:"  
- "Kijk, de move is simpel:"  
- "Dit is het geheim:"  

⚠️ **Wat NIET mag:**  
❌ Geen lange verhalen of overbodige uitleg.  
❌ Geen standaardzinnen die steeds herhaald worden.  
❌ Geen Engelse antwoorden.  

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
