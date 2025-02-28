import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten (nu met MEMES en meer humor)
WISKUNDE_FEITEN = [
    "📐 **Pythagoras is basically de OG van wiskunde** – a² + b² = c² klinkt saai, maar zonder hem geen bouwkunst, geen GPS en geen skateboard-tricks! 🏗️🛹",
    "🔢 **Pi is een oneindig lang getal en niemand weet het einde.** NASA gebruikt het om planetenbanen te berekenen, jij gebruikt het voor je wiskundetoets. 🤓🌍",
    "📊 **Exponenten groeien sneller dan je TikTok-volgers!** 2⁵ = 32, 2¹⁰ = 1024. Exponentiële groei is de reden waarom virale trends ontploffen! 🚀🔥",
    "🌀 **Waarom een cirkel zo chill is?** Je kunt ‘m draaien hoe je wil, hij blijft altijd hetzelfde. Daarom zijn wielen rond en niet vierkant. 🚗💨",
    "🎵 **Muziek is stiekem wiskunde** – De **Fibonacci-reeks** wordt gebruikt in muziekcomposities. Zelfs Mozart had wiskunde in z’n beats! 🎼🔥",
    "🎭 **Als je een priemgetal deelt door een ander priemgetal krijg je ALTIJD een breuk.** Probeer maar: 5 ÷ 3 = 1.666… Priemgetallen zijn gewoon rebels. 💥",
    "🔥 **Wiskunde in gaming:** Videogames gebruiken **vectoren en algebra** om beweging en physics realistisch te maken. Zonder wiskunde? Mario zou letterlijk zweven! 🎮",
    "📎 **Waarom aliens wiskunde snappen** – Priemgetallen zijn universeel. Wetenschappers sturen radiosignalen met priemgetallen om met aliens te praten. 👽📡",
    
    # 🔹 Memes en GIFs
    {"type": "gif", "url": "https://media.giphy.com/media/l0HlRfddw2mErmhPW/giphy.gif"},
    {"type": "gif", "url": "https://media.giphy.com/media/3ohs7YsK8g5scIe2Pm/giphy.gif"},
    {"type": "gif", "url": "https://media.giphy.com/media/1wrIQdj4M3K2k/giphy.gif"},
    {"type": "gif", "url": "https://media.giphy.com/media/26vIfACq1lvA8c6QU/giphy.gif"},
]

# 🔹 FastAPI Setup
app = FastAPI(title="Wiskoro API", version="1.0.0")

# 🔹 CORS-instellingen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wiskoro.nl", "https://www.wiskoro.nl"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 API Endpoints
@app.get("/fact")
async def get_fact():
    """ Geeft een willekeurig wiskunde-feitje of een GIF terug """
    fact = random.choice(WISKUNDE_FEITEN)
    
    if isinstance(fact, dict) and fact.get("type") == "gif":
        return {"type": "gif", "url": fact["url"]}
    
    return {"type": "text", "response": fact}

@app.get("/health")
async def health_check():
    """ Controleert of de API werkt """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
