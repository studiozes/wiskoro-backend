import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten - **Nu nog begrijpelijker & grappiger!**
WISKUNDE_FEITEN = [
    "📐 **Pythagoras was basically de eerste lifehacker.** a² + b² = c² betekent dat je nooit meer hoeft te gokken hoe schuin een ladder moet staan. 🚀",
    "🤯 **Pi is oneindig!** NASA gebruikt ‘t om ruimteschepen te berekenen, jij gebruikt het om cirkels te tekenen. Prioriteiten. 🎯",
    "📊 **Exponentiële groei is gek!** 2⁵ = 32, maar 2¹⁰ = 1024. Stel je voor dat je volgers zo snel groeien. 🔥",
    "🔄 **Een cirkel heeft oneindig veel symmetrieassen.** Daarom rollen wielen smooth en vierkante banden... nou ja, niet. 🚗💨",
    "🎵 **Wiskunde = muziek.** Fibonacci-reeksen en ratio’s bepalen beats. Zelfs Mozart deed aan wiskunde zonder het te weten! 🎼",
    "🎮 **Zonder wiskunde geen gaming.** Vectoren, algebra en physics zorgen ervoor dat Mario niet zweeft. 🍄",
    "🐺 **Priemgetallen zijn de lone wolves.** Ze delen alleen met zichzelf en 1. 2, 3, 5, 7, 11… exclusieve club. 🔢",
    "⏳ **Pythagoras' stelling wordt al 2500 jaar gebruikt!** Ouder dan de meeste talen die we nu spreken. 🤯",
    "💡 **Getallen deelbaar door 9?** Tel de cijfers op. Is dat ook deelbaar door 9? Dan was het originele getal dat ook! 🎲",
    "❓ **Waarom is 0! = 1?** Omdat als je niks hebt, er maar één manier is om dat niks te ordenen: niks doen. Mind blown. 🤯",
    "📱 **Wiskunde is overal!** Insta, TikTok, je bankrekening. Zonder wiskunde zou je For You-page één grote chaos zijn. 💰",
    "❄️ **Fractals = wiskundige kunst.** Sneeuwvlokken, bladeren, de kustlijn van Nederland… allemaal fractals! 🍂",
    "🎲 **De kans om 6x kop te gooien is 1 op 64.** Lukt dat? Koop een lot. 😆",
    "📏 **De gulden snede (1.618) is de mooiste verhouding.** Je vindt ‘t in kunst, architectuur en zelfs in je gezicht. 😎",
    "💰 **Exponentiële groei is als een cheatcode.** Sparen + rente = gratis geld. Bank = slow mode. 🔥",
    "🚀 **Een blad papier 42 keer vouwen raakt de maan.** Too bad je max bij 7 keer zit. 🤷",
    "🔢 **Vierkantsgetallen hebben een oneven aantal delers.** Waarom? Omdat er altijd eentje dubbel is! (16: 1, 2, 4, 4, 8, 16).",
    "🍍 **De Fibonacci-reeks zit in ananassen, bloemen, en zelfs slakkenhuizen.** Moeder Natuur = wiskunde baas! 🔄",
    "💡 **Er zijn oneindig veel priemgetallen.** Dus zelfs als je er 1 miljard vindt, ben je nog niet klaar. 🔢",
    "💥 **Waarom 1 + 2 + 3 + 4 ... tot oneindig uitkomt op -1/12?** Snap je niet? Geeft niks. Zelfs wiskundigen snappen het amper. 😵",
    "📊 **Statistiek is gewoon gokken, maar slim.** Daarom wint het casino altijd. 🎰",
    "🏠 **Een piramide is eigenlijk een vierkante kegel.** Mind = blown. 🤯",
    "🔀 **Waarom is 7 de meest gekozen random getal?** Omdat het ‘t enige cijfer is zonder symmetrie of patroon. 📊",
    "🕹️ **Je game character rent dankzij wiskunde.** Vectoren, snelheden en afstanden worden nonstop berekend! 🎮",
    "🔬 **Wiskunde voorspelt het weer beter dan je oma’s reuma.** Weermodellen = pure statistiek. 🌦️",
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
    """ Geeft een willekeurig wiskunde-feitje terug """
    fact = random.choice(WISKUNDE_FEITEN)
    return {"type": "text", "response": fact}

@app.get("/health")
async def health_check():
    """ Controleert of de API werkt """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
