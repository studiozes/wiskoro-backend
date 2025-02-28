import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten (✅ NOG MEER VARIATIE, LEERZAAM & CHILL!)
WISKUNDE_FEITEN = [
    "📐 **Pythagoras voor dummies** – Stel, je wil een shortcut nemen door een veld in plaats van om te lopen. Met **a² + b² = c²** kun je berekenen hoe kort die route écht is. Bouwvakkers en skaters gebruiken dit non-stop! 🛹🏗️",
    "🔢 **Pi = cheatcode voor cirkels** – Dit getal **3.14159…** stopt NOOIT. Zelfs NASA gebruikt het om planeetbanen te berekenen! Zonder **π** geen wiel, geen voetbal en geen fidget spinner. 🔄⚽",
    "📊 **Exponenten groeien sneller dan TikTok fame** – Als een bacterie zich elke minuut **verdubbelt**, heb je in no-time een wereldprobleem. TikTok-algoritmes? Zelfde principe, maar dan met views. 📈",
    "🌀 **Waarom een cirkel chill is?** – Draai ‘m hoe je wil, hij blijft hetzelfde. Daarom hebben raceauto’s ronde wielen en geen vierkante. **Oneindig veel symmetrieassen** = perfect design. 🏎️",
    "🎵 **Muziek = wiskunde in disguise** – Je favoriete beats volgen de **Fibonacci-reeks**. Zelfs Mozart gebruikte ‘m, en die had geen Spotify Premium. 🎼🔥",
    "🧮 **De magische 9-truc** – Check dit: neem een getal, tel de cijfers op. Als dat nieuwe getal door **9 deelbaar is**, was het originele getal dat ook! Wiskunde cheatcode 🔥",
    "⚡ **Waarom 0× iets altijd 0 is?** – Stel, je hebt **nul** pizza’s en je deelt die met vrienden. Hoeveel krijgt iedereen? **Precies, niks.** Daarom is elk getal keer nul gewoon nul. 🍕😂",
    "🔗 **Fractals = wiskunde kunst** – Heb je ooit een sneeuwvlok goed bekeken? Overal zie je kleine herhalende patronen. Dit noemen we **fractals** en ze worden gebruikt in animatiefilms. ❄️🎨",
    "📏 **Waarom een rechthoek makkelijker is dan een driehoek?** – Driehoeken zijn WILD. Je kunt er ALTIJD een breken in twee rechthoeken. Daarom werken wiskunde GOAT’s liever met rechthoeken! 🏗️",
    "🎯 **De kans op een perfecte worp** – Wist je dat je met wiskunde kunt berekenen hoe je een bal perfect gooit? **Parabolische banen** helpen basketbalspelers de GOAT te worden. 🏀",
    "📊 **Normaalverdeling is overal** – IQ’s, schoenmaten en hoe lang mensen gemiddeld scrollen op Insta. Alles volgt een **klokvormige verdeling**. De meeste mensen zitten in het midden, met een paar uitschieters. 🔥",
    "💰 **Waarom compound interest OP is** – Stel je spaart **€100** en krijgt **5% rente per jaar**. Dat lijkt weinig, maar door **samengestelde rente** groeit het EXPONENTIEEL. Pensioenfondsen leven hiervan. 📈💵",
    "🃏 **Waarom gokken altijd in het voordeel van het casino is?** – Kansberekening zegt dat bij elke draai het **huis wint**. Hoe langer je speelt, hoe meer je verliest. Zelfs met ‘bijna winnen’ manipuleren ze je brein. 🎰💸",
    "🌍 **Waarom GPS zonder wiskunde niet zou werken** – Je telefoon gebruikt **triangulatie** om je locatie te bepalen. Dat is gewoon **Pythagoras, maar dan in 3D**. Zonder wiskunde? Verdwaald. 📍",
    "📐 **Waarom 180° in een driehoek een wet is** – Teken een driehoek, knip ‘m in drie stukken en leg ze naast elkaar. BAM! Altijd een rechte lijn, oftewel **180°**. #mindblown 🤯",
    "🧠 **Hoeveel is 1000 + 40 + 1000 + 30?** – Je dacht **3000** hè? Nope, het is **2070**. Je brein wordt keihard **getrickt** door patroonherkenning. Wiskunde = een illusie soms. 😵‍💫",
    "🚀 **Waarom parabolen de GOAT zijn in de ruimte** – Ruimteraketten en satellieten gebruiken **parabolische banen**. Zonder die kennis? Geen Starlink, geen NASA, geen SpaceX. 📡🚀",
    "📎 **De golden ratio is letterlijk overal** – Van je gezicht, tot kunst, tot schelpen in de zee. Wiskunde GOAT’s gebruiken de **gulden snede** om dingen visueel perfect te maken. 🎨",
    "🎭 **De kans op een dobbelsteenworp** – De kans dat je een **6** gooit met een eerlijke dobbelsteen is **1 op 6**. Maar als je **twee dobbelstenen** gooit? Dan is **7** het meest voorkomende getal. #probability 🔢",
    "🔥 **Waarom een driehoek het sterkste figuur is** – Driehoeken kunnen niet instorten zoals vierkanten dat doen. Daarom bouwen ingenieurs bruggen en torens met driehoeken. 💪🏗️",
    "🔄 **Waarom de tafel van 9 mind-blowing is** – Check dit: 9×1=9, 9×2=18 (1+8=9), 9×3=27 (2+7=9). Zie je het patroon? **Altijd 9!** 🔥",
    "🛸 **Waarom aliens wiskunde snappen** – De SETI gebruikt **priemgetallen** in radiosignalen om aliens te vinden. Want priemgetallen zijn universeel. 👽📡",
    "🏆 **Waarom records steeds verbroken worden** – Wiskunde laat zien dat atleten door **techniek, training en aerodynamica** steeds sneller, sterker en beter worden. 📊🏃‍♂️",
    "📱 **Waarom je telefoon sneller lijkt dan je denkt** – De **snelheid van licht** is de limiet. Je wifi, 5G en zelfs je camera’s werken door wiskundige algoritmes. 🚀",
]

# 🔹 FastAPI Setup
app = FastAPI(title="Wiskoro API", version="1.0.0")

# 🔹 CORS-instellingen (verbindt met frontend)
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
    """ Geeft een willekeurig wiskunde-feitje terug met veel variatie en uitleg """
    fact = random.choice(WISKUNDE_FEITEN)
    return {"response": fact}

@app.get("/health")
async def health_check():
    """ Controleert of de API werkt """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
