import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten (opnieuw uitgebreid en verbeterd)
WISKUNDE_FEITEN = [
    "<b>Pythagoras is de OG van wiskunde</b> – a² + b² = c² is basically de cheatcode voor alle schuine lijnen! 📐🔥",
    "<b>Pi is oneindig lang</b> en niemand kent het exacte einde. NASA gebruikt het om planetenbanen te berekenen, jij gebruikt het om cirkels te tekenen. 🤯",
    "<b>Exponenten groeien sneller dan je TikTok-volgers</b>! 🚀 2⁵ = 32, maar 2¹⁰ = 1024! Dat is waarom virale trends exploderen! 🔥",
    "<b>Een cirkel heeft oneindig veel symmetrieassen</b>. 🔄 Daarom rolt een wiel soepel en een vierkant... nou ja, niet. 🚗💨",
    "<b>Muziek is stiekem wiskunde</b> – De Fibonacci-reeks wordt gebruikt in beats en harmonieën. Zelfs Mozart deed aan wiskunde zonder het door te hebben! 🎼🔥",
    "<b>Wiskunde in gaming:</b> Games gebruiken vectoren en algebra om beweging en physics realistisch te maken. Zonder wiskunde? Mario zou letterlijk zweven! 🎮",
    "<b>Priemgetallen zijn de lone wolves</b> van de getallenwereld. Ze zijn alleen deelbaar door zichzelf en 1. 2, 3, 5, 7, 11... en geen enkele andere! 🐺💯",
    "<b>De stelling van Pythagoras wordt al 2500 jaar gebruikt!</b> Dat is ouder dan de meeste talen die we nu spreken. 📐⏳",
    "<b>Als je een getal door 9 deelt</b> en de som van de cijfers is deelbaar door 9, dan is het originele getal ook deelbaar door 9. Try it! 🤯",
    "<b>Waarom is 0! = 1?</b> Omdat het het enige logische antwoord is. Factorial betekent ‘hoeveel manieren kun je dingen ordenen’. Als je niks hebt, is er maar één manier: niks doen. 💡",
    "<b>Wiskunde is letterlijk overal</b>: je geld, je games, je Insta-algoritme. Zonder wiskunde zou je TikTok For You-page een complete puinhoop zijn. 💰📊",
    "<b>Fractals zijn wiskunde-kunst</b>. Sneeuwvlokken, bladeren, zelfs de kustlijn van Nederland is een fractal. Moeder Natuur doet aan wiskunde! 🍂❄️",
    "<b>De kans om zes keer achter elkaar kop te gooien met een munt is 1 op 64</b>. Dus als dat lukt, ren meteen naar het casino! 🎲😂",
    "<b>De gulden snede (1.618) is de mooiste verhouding</b>. Het komt voor in kunst, architectuur en zelfs in je gezicht. 📏✨",
    "<b>Wiskunde is als een cheatcode voor het leven</b>. Snap je exponentiële groei? Dan snap je waarom sparen op lange termijn koning is. 💰📈",
    "<b>Waarom vermenigvuldigen met 0 altijd 0 is?</b> Simpel: als je 0 keer iets hebt, heb je niks. Ook al was het een miljoen. 🤷‍♂️",
    "<b>Hoeveel keer moet je een blad papier dubbelvouwen om de maan te raken?</b> Slechts 42 keer! 🚀📄 Mind blown! 🤯",
    "<b>Vierkantsgetallen hebben altijd een oneven aantal delers</b>. Waarom? Omdat één van die delers dubbel voorkomt. Denk aan 16: 1, 2, 4, **4**, 8, 16. 🔢",
    "<b>De Fibonacci-reeks komt zelfs voor in de spiralen van een ananas</b>. 🍍 Wiskunde is letterlijk overal!",
    "<b>Er zijn oneindig veel priemgetallen</b>. Dus zelfs als je er 1 miljard vindt, zijn er nog steeds oneindig meer te ontdekken! 🤯🔢",
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
    """ Geeft een willekeurig wiskunde-feitje terug met correcte HTML-opmaak """
    fact = random.choice(WISKUNDE_FEITEN)
    return {"type": "text", "response": fact}

@app.get("/health")
async def health_check():
    """ Controleert of de API werkt """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
