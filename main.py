import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten (met Markdown-styling)
WISKUNDE_FEITEN = [
    "**Pythagoras is de OG van wiskunde** – a² + b² = c² is basically de cheatcode voor alle schuine lijnen! 📐🔥",
    "**Pi is oneindig lang** en niemand kent het exacte einde. NASA gebruikt het om planetenbanen te berekenen, jij gebruikt het om cirkels te tekenen. 🤯",
    "**Exponenten groeien sneller dan je TikTok-volgers**! 🚀 2⁵ = 32, maar 2¹⁰ = 1024! Dat is waarom virale trends exploderen! 🔥",
    "**Een cirkel heeft oneindig veel symmetrieassen**. 🔄 Daarom rolt een wiel soepel en een vierkant... nou ja, niet. 🚗💨",
    "**Muziek is stiekem wiskunde** – De Fibonacci-reeks wordt gebruikt in beats en harmonieën. Zelfs Mozart deed aan wiskunde zonder het door te hebben! 🎼🔥",
    "**Wiskunde in gaming:** Games gebruiken vectoren en algebra om beweging en physics realistisch te maken. Zonder wiskunde? Mario zou letterlijk zweven! 🎮",
    "**Priemgetallen zijn de lone wolves** van de getallenwereld. Ze zijn alleen deelbaar door zichzelf en 1. 2, 3, 5, 7, 11... en geen enkele andere! 🐺💯",
    "**De stelling van Pythagoras wordt al 2500 jaar gebruikt!** Dat is ouder dan de meeste talen die we nu spreken. 📐⏳",
    "**Als je een getal door 9 deelt** en de som van de cijfers is deelbaar door 9, dan is het originele getal ook deelbaar door 9. Try it! 🤯",
    "**Waarom is 0! = 1?** Omdat het het enige logische antwoord is. Factorial betekent ‘hoeveel manieren kun je dingen ordenen’. Als je niks hebt, is er maar één manier: niks doen. 💡",
    "**Wiskunde is letterlijk overal**: je geld, je games, je Insta-algoritme. Zonder wiskunde zou je TikTok For You-page een complete puinhoop zijn. 💰📊",
    "**Fractals zijn wiskunde-kunst**. Sneeuwvlokken, bladeren, zelfs de kustlijn van Nederland is een fractal. Moeder Natuur doet aan wiskunde! 🍂❄️",
    "**De kans om zes keer achter elkaar kop te gooien met een munt is 1 op 64**. Dus als dat lukt, ren meteen naar het casino! 🎲😂",
    "**De gulden snede (1.618) is de mooiste verhouding**. Het komt voor in kunst, architectuur en zelfs in je gezicht. 📏✨",
    "**Wiskunde is als een cheatcode voor het leven**. Snap je exponentiële groei? Dan snap je waarom sparen op lange termijn koning is. 💰📈",
    "**Waarom vermenigvuldigen met 0 altijd 0 is?** Simpel: als je 0 keer iets hebt, heb je niks. Ook al was het een miljoen. 🤷‍♂️",
    "**Hoeveel keer moet je een blad papier dubbelvouwen om de maan te raken?** Slechts 42 keer! 🚀📄 Mind blown! 🤯",
    "**Vierkantsgetallen hebben altijd een oneven aantal delers**. Waarom? Omdat één van die delers dubbel voorkomt. Denk aan 16: 1, 2, 4, **4**, 8, 16. 🔢",
    "**De Fibonacci-reeks komt zelfs voor in de spiralen van een ananas**. 🍍 Wiskunde is letterlijk overal!",
    "**Er zijn oneindig veel priemgetallen**. Dus zelfs als je er 1 miljard vindt, zijn er nog steeds oneindig meer te ontdekken! 🤯🔢",
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
    """ Geeft een willekeurig wiskunde-feitje terug met Markdown-opmaak """
    fact = random.choice(WISKUNDE_FEITEN)
    return {"type": "text", "response": fact}

@app.get("/health")
async def health_check():
    """ Controleert of de API werkt """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
