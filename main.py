import os
import re
import requests
import logging
import asyncio
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Wiskunde context voor HAVO 3
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

# Straattaal responses
STRAATTAAL = {
    'intro': ["Yo!", "Ey mattie!", "Yo bro!", "Check dit!", "Luister ff!"],
    'bevestiging': ["Easy toch?", "Makkie!", "Snap je?", "Simpel bro!", "Nu snap je het wel!"],
}

# Niet-wiskundevraag responses
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

def format_response(answer: str, emoji: str) -> str:
    answer = re.sub(r'(als AI|als model|als taalmodel|This response).*', '', answer, flags=re.IGNORECASE)
    sentences = [s.strip() for s in answer.split('.') if s.strip()]
    sentences = sentences[:2]  # Max 2 zinnen
    result = f"{random.choice(STRAATTAAL['intro'])} {'. '.join(sentences)}"
    if random.random() < 0.3:
        result += f" {random.choice(STRAATTAAL['bevestiging'])}!"
    if not any(char in result for char in ['🧮', '📐', '📈', '📊']):
        result += f" {emoji}"
    return result

# FastAPI setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wiskoro.nl", "https://www.wiskoro.nl"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    vraag = request.message.lower()
    for context, data in HAVO3_CONTEXT.items():
        if any(term in vraag for term in data['termen']):
            antwoord = f"{random.choice(STRAATTAAL['intro'])} Dat heeft te maken met {context}. {random.choice(data['termen'])}."
            return {"response": format_response(antwoord, data['emoji'])}
    return {"response": get_niet_wiskunde_response(vraag)}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
