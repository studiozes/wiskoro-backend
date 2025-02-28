import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten met extra stijl, humor & uitleg
WISKUNDE_FEITEN = [
    "📐 **Pythagoras’ Cheatcode:** Stel je voor: je bouwt een schuin dak op je Minecraft-huis. Hoe lang moet dat schuine stuk zijn? Easy! Pythagoras regelt het met a² + b² = c². Dit is basically de **OG-formule** om rechte hoeken te checken. Zelfs bouwvakkers gebruiken dit IRL! 🔥",
    
    "🤯 **Pi is een eindeloze vibe:** Pi (3,14159265...) is net als TikTok-scrollen: je kunt **oneindig doorgaan**, maar je komt nooit bij het einde. NASA gebruikt Pi om de afstanden van planeten te berekenen. Jij gebruikt het om pizza’s eerlijk te verdelen. Prioriteiten. 🍕🚀",
    
    "📊 **Exponentiële groei = je volgers skyrocketen**: 2⁵ = 32, maar 2¹⁰ = 1024! **Dit is waarom virale trends exploderen**. Elke keer dat iemand jouw video deelt, verdubbelt het bereik. Wiskunde = de kracht achter influencer-success! 📈🔥",
    
    "🔄 **Cirkel = de koning van symmetrie:** Een cirkel heeft **oneindig veel symmetrieassen**. Daarom rolt een wiel soepel en een vierkant… nou ja, niet. Zonder cirkels zouden fietsen useless zijn en auto’s basically karretjes op vierkante blokken. 🚗💨",
    
    "🎵 **Muziek = pure wiskunde:** Wist je dat **je favoriete beats wiskundig perfect zijn?** De **Fibonacci-reeks** komt voor in klassieke muziek, hiphop en zelfs EDM. Mozart was basically een wiskunde-nerd zonder dat ‘ie het wist. 🎼🔢",
    
    "🎮 **Gaming zonder wiskunde? No way.** Vectoren, algebra & physics zorgen ervoor dat Mario niet random zweeft en dat Fortnite-schoten realistisch vallen. Hoe verder de kogel, hoe meer zwaartekracht ‘m naar beneden trekt. **Zonder wiskunde zou Call of Duty voelen als een glitch-fest.** 🎯",
    
    "🐺 **Priemgetallen = de lone wolves van de wiskunde:** Ze delen alleen door zichzelf en 1. Ze zijn **onvoorspelbaar en ongekend nuttig**. Zonder priemgetallen zouden wachtwoorden en banktransacties **super hackable** zijn. Dus als je geld veilig is, bedank wiskunde. 💰🔐",
    
    "⏳ **Pythagoras’ stelling wordt al 2500 jaar gebruikt!** Dat is **ouder dan de meeste talen** die we nu spreken. Terwijl Griekse filosofen nog discussies voerden over of de zon wel echt bestond, **rekenden ze al met Pythagoras**. 📐🤯",
    
    "💡 **Wil je checken of een getal door 9 deelbaar is?** Tel de cijfers bij elkaar op. Is dat getal ook deelbaar door 9? Dan is het originele getal dat ook. Check maar: 729 → 7+2+9 = 18 en ja hoor, 18 is deelbaar door 9. **Math hacks! 🔥**",
    
    "📱 **Je TikTok For You-page werkt met wiskunde:** Het algoritme checkt **hoe lang je kijkt, hoeveel je liket en hoe vaak je doorscrolt**. Dit heet een ‘gewogen gemiddelde’. **Dus als je denkt dat TikTok je gedachten leest… nee bro, het is gewoon pure wiskunde.** 🤯📊",
    
    "❄️ **Fractals = wiskunde-kunst:** Sneeuwvlokken, bladeren, de kustlijn van Nederland… allemaal fractals. **Natuur doet gewoon aan advanced math zonder dat we het doorhebben.** 🍂🔄",
    
    "🎲 **Kansberekening = waarom je nooit de loterij wint:** De kans om zes keer achter elkaar kop te gooien? 1 op 64. Maar de kans dat je de loterij wint? **1 op 14 miljoen.** Dus als je wint: direct naar Vegas. 😂",
    
    "📏 **De gulden snede (1.618) = de mooiste verhouding:** Het komt voor in schilderijen, architectuur en zelfs je gezicht. Wiskunde bepaalt dus **wat we aantrekkelijk vinden**. Thanks, getallen. 📐✨",
    
    "💰 **Exponentiële groei = de reden dat rijke mensen rijker worden:** Sparen + rente = **gratis geld**. Daarom zegt iedereen dat je vroeg moet beginnen met sparen. De bank is basically slow mode, maar het werkt. 📈🔥",
    
    "🚀 **Een blad papier 42 keer vouwen raakt de maan.** Ja, echt. Elke vouw verdubbelt de dikte. **Na 10 vouwen? 10 cm. Na 20? 100 meter. Na 42? BAM, maan.** Too bad dat je max bij 7 keer vouwen zit. 🤷📄",
    
    "📊 **Statistiek is basically gokken, maar dan slim.** Daarom wint het casino **altijd**. De kans dat je wint is altijd net iets **lager** dan dat je verliest. 🎰🎲",
    
    "🔀 **Waarom is 7 het meest gekozen ‘random’ getal?** Omdat het **geen symmetrie of patroon** heeft. Je brein denkt dat het random is, maar eigenlijk kies je het **onbewust vaker dan andere cijfers**. 📊🤯",
    
    "🕹️ **Waarom werkt je game zo smooth? Wiskunde.** Je karakter rent dankzij vectoren en zwaartekracht-berekeningen. Wiskunde checkt **elke seconde** hoe je beweegt. Zonder dit zou je Call of Duty of FIFA **pure chaos zijn.** 🎮",
    
    "🌍 **De aarde is niet perfect rond, maar een afgeplatte bol.** Dit wisten wiskundigen **lang voordat astronauten het konden zien**. Wiskunde kan dus feiten bewijzen zonder dat we het hoeven te checken. 🤯🚀",
    
    "💡 **Waarom is 2 het enige even priemgetal?** Omdat elk ander even getal **altijd door 2 deelbaar is**. 2 is de enige die **geen delers** heeft behalve 1 en zichzelf. 🔢💥",
    
    "📈 **Als je 5 keer achter elkaar een 6 gooit met een dobbelsteen… is de kans op de volgende 6 dan ook 1 op 6?** YES! Elke worp is onafhankelijk. Je brein **denkt** dat 6 minder waarschijnlijk wordt, maar nope. Kans blijft exact hetzelfde! 🎲🤓"
]

# 🔹 FastAPI Setup
app = FastAPI()

# 🔹 CORS-instellingen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wiskoro.nl", "https://www.wiskoro.nl"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 API Endpoints
@app.get("/fact")
async def get_fact():
    """ Geeft een willekeurig wiskunde-feitje terug """
    return {"type": "text", "response": random.choice(WISKUNDE_FEITEN)}

@app.get("/health")
async def health_check():
    """ Controleert of de API werkt """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
