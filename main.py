import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 🔹 Wiskunde Feiten
WISKUNDE_FEITEN = [
    "Pi is oneindig lang en niemand kent het exacte einde. 🤯",
    "Een vierkant getal is een getal dat ontstaat door een getal met zichzelf te vermenigvuldigen. 4 = 2×2! 🔢",
    "De stelling van Pythagoras wordt al 2500 jaar gebruikt! 📐",
    "Exponenten groeien sneller dan je TikTok views. 🚀",
    "Een cirkel heeft oneindig veel symmetrieassen. 🔄",
    "De Fibonacci-reeks komt voor in bloemen, kunst en zelfs muziek! 🎵",
    "Als je een getal door 9 deelt en de som van de cijfers is deelbaar door 9, dan is het originele getal ook deelbaar door 9. 🤯"
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
    """ Geeft een willekeurig wiskunde-feitje terug """
    fact = random.choice(WISKUNDE_FEITEN)
    return {"response": fact}

@app.get("/health")
async def health_check():
    """ Controleert of de API werkt """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
