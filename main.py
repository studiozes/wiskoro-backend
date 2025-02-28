import os
import requests
import logging
import random
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseSettings, Field

# 🔹 Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 HAVO-3 Wiskunde Feiten
WISKUNDE_FEITEN = [
    "Pi is irrationeel, dus je kunt 'm nooit helemaal uitschrijven! 3.141592653... en zo door! 🌀",
    "De stelling van Pythagoras zegt: a² + b² = c². Perfect voor driehoeken! 📐",
    "Wist je dat de Fibonacci-reeks overal in de natuur voorkomt? Zonnebloemen, spiralen, je naam maar op! 🌻",
    "Exponenten zijn gewoon snellere vermenigvuldigingen. 2³ = 2 × 2 × 2 = 8. Lekker efficiënt! 🚀",
    "Een cirkel heeft 360 graden, maar radianen zijn nog handiger: 2π rad = 360° 🔄",
    "Procent betekent letterlijk 'per honderd'. Dus 25% = 25/100 = 0.25. Snap je 'm? 🎯",
    "Een wortel is gewoon het omgekeerde van een macht. √16 = 4, want 4² = 16! 🔢",
    "De stelling van Thales zegt dat een driehoek in een halve cirkel altijd een rechte hoek heeft! 🏹",
    "Logaritmes zijn de omgekeerde operaties van exponenten. log₂(8) = 3 betekent gewoon 2³ = 8! 🔥",
    "In een gelijkzijdige driehoek zijn alle hoeken altijd 60 graden. Check die symmetrie! 📏",
    "Een priemgetal is alleen deelbaar door 1 en zichzelf. 7? Priem. 9? Nope! ❌",
    "Een parabool in een grafiek? Check de vergelijking y = ax² + bx + c. Dat is de move! 📊",
    "Een negatieve macht is gewoon een breuk: 2⁻³ = 1/2³ = 1/8. Lekker logisch! 🤯",
    "Sinus, cosinus en tangens zijn de drie big players in goniometrie. Ken je SOH-CAH-TOA? 📐",
    "Een even getal is deelbaar door 2, een oneven getal niet. Easy check: eindigt op 0, 2, 4, 6 of 8? ✅",
    "De gulden snede is een magisch getal in kunst en natuur: 1.618... Het ziet er altijd perfect uit! 🎨",
    "Goniometrische functies zijn gewoon cirkelbewegingen in een rechte lijn. Sinus is hoogte, cosinus is breedte! 🔄",
    "Statistiek draait om gemiddelden en spreiding. Weet jij wat mediaan en modus betekenen? 📊",
    "Verhoudingen zie je overal: als een pizza in 4 stukken is verdeeld, heeft elk stuk 25% van het totaal. 🍕",
    "Een oneindige reeks is zoals 1/3 in decimalen: 0.3333... Het stopt nooit! 🔁"
]

# 🔹 Knopteksten in straattaal voor afwisseling
BUTTON_TEKSTEN = [
    "Drop nog een feitje!", "Hit me up!", "Nog een keertje!", 
    "Wat nog meer?", "Tik me nog een wiskundeding!", 
    "Spit nog een feitje!", "Gooi er nog eentje bij!", "Bro, nog een!"
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

# 🔹 FastAPI Setup
app = FastAPI(title="Wiskoro API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 Endpoint om een willekeurig wiskundefeit te geven
@app.post("/chat")
async def get_fact():
    """Geeft een willekeurig wiskunde feitje terug."""
    feitje = random.choice(WISKUNDE_FEITEN)
    knoptekst = random.choice(BUTTON_TEKSTEN)
    return {"response": feitje, "button": knoptekst}

# 🔹 Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
