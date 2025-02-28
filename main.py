import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten met extra spice, humor & uitleg
WISKUNDE_FEITEN = [
    "📐 Pythagoras' Cheatcode: Stel je voor, je bent een architect en moet een schuin dak berekenen. Hoe lang moet dat schuine stuk zijn? Easy, bro! Pythagoras’ a² + b² = c² is basically de OG-formule om hoeken te checken. Zelfs in Fortnite als je ramp-building doet, gebruik je 'm zonder dat je het doorhebt. 🔥",
    
    "🤯 Pi is oneindig lang, net als je scroll-sessie op TikTok. Je kunt doorgaan, maar je komt nooit bij het einde. NASA gebruikt Pi om de afstanden van planeten te berekenen. Jij gebruikt het om te zorgen dat je pizza eerlijk verdeeld is. Prioriteiten. 🍕🚀",
    
    "📊 Exponentiële groei is waarom virale trends exploderen. Kijk, 2⁵ = 32, maar 2¹⁰ = 1024. Elke keer dat iets gedeeld wordt, wordt het groter en groter. Dit is waarom een domme meme binnen 24 uur een wereldhit kan worden. 📈🔥",
    
    "🔄 Een cirkel heeft oneindig veel symmetrieassen. Daarom rolt een wiel smooth en een vierkant... nou ja, niet. Zonder cirkels zouden fietsen useless zijn en auto's basically kruiwagens op vierkante wielen. 🚗💨",
    
    "🎵 Muziek is gewoon wiskunde met swag. De Fibonacci-reeks zit in klassieke muziek, hiphop en EDM. Mozart gebruikte wiskunde om zijn composities perfect te maken, maar Lil Nas X en Drake doen het ook – zonder dat ze het doorhebben. 🎼🔥",
    
    "🎮 Gaming zonder wiskunde? No way! Vectoren, algebra en physics zorgen ervoor dat je character niet random zweeft en dat kogels in Call of Duty realistisch vallen. Zonder wiskunde zou GTA 6 gewoon Mario Kart zijn met guns. 🎯",
    
    "🐺 Priemgetallen zijn de lone wolves van de wiskunde. Ze delen alleen door zichzelf en 1. Zonder priemgetallen zouden je wachtwoorden en banktransacties super hackable zijn. Dus als je geld veilig is, bedank wiskunde. 💰🔐",
    
    "⏳ Pythagoras’ stelling wordt al 2500 jaar gebruikt! Dit is ouder dan de meeste talen die we nu spreken. Zelfs de oude Grieken berekenden al hoe groot hun tempels moesten worden met deze formule. 📐🤯",
    
    "💡 Wil je checken of een getal door 9 deelbaar is? Tel de cijfers bij elkaar op. Is dat getal ook deelbaar door 9? Dan is het originele getal dat ook. Check maar: 729 → 7+2+9 = 18 en ja hoor, 18 is deelbaar door 9. Wiskunde hacks! 🔥",
    
    "📱 Je TikTok For You-page werkt met wiskunde. Het algoritme checkt hoe lang je kijkt, hoeveel je liket en hoe vaak je doorscrolt. Dit heet een gewogen gemiddelde. Dus nee, TikTok leest je gedachten niet, het is gewoon pure wiskunde. 🤯📊",
    
    "❄️ Fractals zijn wiskunde-kunst. Sneeuwvlokken, bladeren en zelfs de kustlijn van Nederland... allemaal fractals. Moeder Natuur doet gewoon aan wiskunde, zonder dat ze ooit naar school is geweest. 🍂🔄",
    
    "🎲 Kansberekening is waarom het casino altijd wint. De kans dat je wint is altijd net iets lager dan dat je verliest. Daarom wordt het huis altijd rijker en de spelers meestal armer. 🎰🎲",
    
    "📏 De gulden snede (1.618) is de mooiste verhouding. Het zit in schilderijen, architectuur en zelfs je gezicht. Daarom vinden mensen symmetrische gezichten mooier – het is gewoon wiskunde. 📐✨",
    
    "💰 Exponentiële groei is de reden dat rijke mensen rijker worden. Sparen + rente = gratis geld. Daarom zegt iedereen dat je vroeg moet beginnen met sparen. Hoe langer je wacht, hoe minder geld je opbouwt. 📈🔥",
    
    "🚀 Een blad papier 42 keer vouwen raakt de maan. Ja, echt. Elke vouw verdubbelt de dikte. Na 10 vouwen? 10 cm. Na 20? 100 meter. Na 42? BAM, maan. Too bad dat je max bij 7 keer vouwen zit. 🤷📄",
    
    "📊 Statistiek is basically gokken, maar dan slim. Daarom wint het casino altijd. De kans dat je wint is altijd net iets lager dan dat je verliest. Dus als je denkt dat je geluk hebt, nope – wiskunde heeft al bepaald dat je verliest. 🎲",
    
    "🔀 Waarom kiezen mensen altijd 7 als 'random' getal? Omdat het geen symmetrie of patroon heeft. Je brein denkt dat het random is, maar eigenlijk kies je het onbewust vaker dan andere cijfers. 📊🤯",
    
    "🕹️ Waarom werkt je game zo smooth? Wiskunde. Je karakter rent dankzij vectoren en zwaartekracht-berekeningen. Zonder dit zou Fortnite gewoon een glitch-fest zijn. 🎮",
    
    "🌍 De aarde is niet perfect rond, maar een afgeplatte bol. Dit wisten wiskundigen lang voordat astronauten het konden zien. Wiskunde kan dus feiten bewijzen zonder dat we het hoeven te checken. 🤯🚀",
    
    "💡 Waarom is 2 het enige even priemgetal? Omdat elk ander even getal altijd door 2 deelbaar is. 2 is de enige die geen delers heeft behalve 1 en zichzelf. 🔢💥",
    
    "📈 Als je 5 keer achter elkaar een 6 gooit met een dobbelsteen… is de kans op de volgende 6 dan ook 1 op 6? YES! Elke worp is onafhankelijk. Je brein denkt dat 6 minder waarschijnlijk wordt, maar nope. Kans blijft exact hetzelfde! 🎲🤓"
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
