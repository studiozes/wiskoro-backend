import os
import asyncpg
import requests
import logging
import time
import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# 🔹 Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 🔹 Settings
class Settings(BaseSettings):
    DATABASE_URL: str
    HUGGINGFACE_API_KEY: str
    RATE_LIMIT_PER_MINUTE: int = 30
    AI_TIMEOUT: int = 15  # AI timeout verhogen
    CACHE_EXPIRATION: int = 3600  # 1 uur cache voor AI-antwoorden

    class Config:
        case_sensitive = True

settings = Settings()

# 🔹 In-memory cache
class LocalCache:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self.cache and time.time() - self.timestamps[key] < settings.CACHE_EXPIRATION:
            return self.cache[key]
        return None

    def set(self, key: str, value: str):
        self.cache[key] = value
        self.timestamps[key] = time.time()

cache = LocalCache()

# 🔹 Database connection pooling
class Database:
    pool = None

    @classmethod
    async def create_pool(cls):
        cls.pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=5, max_size=20)

    @classmethod
    async def get_connection(cls):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.acquire()

    @classmethod
    async def release_connection(cls, conn):
        await cls.pool.release(conn)

# 🔹 Wiskunde-validatie
def validate_math_question(question: str) -> Tuple[bool, str]:
    """Valideert of de vraag wiskundegerelateerd is."""
    math_keywords = ['bereken', 'kwadraat', 'vergelijking', 'functie', 'formule', 'uitkomst', 
                     '+', '-', '*', '/', '=', '%', 'π', 'sin', 'cos', 'tan', 'log']
    
    has_numbers = any(char.isdigit() for char in question)
    has_math_terms = any(keyword in question.lower() for keyword in math_keywords)

    if not (has_numbers or has_math_terms):
        return False, "Yo! Stel een wiskundevraag, bijv. 'Los 3x + 5 = 11 op' of 'Bereken de omtrek van een cirkel met straal 4' 🔢"
    
    return True, ""

# 🔹 AI chatbot logica
async def get_ai_response(user_question: str) -> str:
    """Haalt AI-respons op via Hugging Face API met wiskundefocus."""
    cached_response = cache.get(user_question)
    if cached_response:
        logger.info("Cache hit voor vraag: %s", user_question)
        return cached_response

    AI_MODEL = "google/flan-t5-large"

    math_prompt = f"""Je bent een wiskundedocent die uitlegt in jongerentaal.
    Los deze wiskundevraag stap voor stap op:

    {user_question}

    Gebruik deze regels:
    1. Leg elke stap duidelijk uit.
    2. Gebruik emoji's om uitleg leuker te maken.
    3. Schrijf in begrijpelijke taal met GenZ-invloeden.
    4. Geef het eindantwoord met een ✅.
    """

    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {"inputs": math_prompt, "parameters": {"max_length": 500, "temperature": 0.7}}

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{AI_MODEL}",
            headers=headers,
            json=payload,
            timeout=settings.AI_TIMEOUT
        )
        response.raise_for_status()
        response_data = response.json()

        if isinstance(response_data, list) and response_data:
            result = response_data[0].get("generated_text", "")
            cache.set(user_question, result)
            return result

        raise ValueError("Onverwacht API response formaat")

    except requests.exceptions.Timeout:
        logger.error("AI timeout voor vraag: %s", user_question)
        raise HTTPException(status_code=504, detail="Yo fam, deze vraag is pittig! Probeer het nog een keer of splits 'm op! ⏳")
    except requests.exceptions.RequestException as e:
        logger.error("AI API error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="De AI is even off-duty, kom zo terug! 🔧")

# 🔹 FastAPI setup
app = FastAPI(title="Wiskoro API", version="1.0.0")

# 🔹 CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wiskoro.nl", "https://www.wiskoro.nl", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 🔹 API models
class ChatRequest(BaseModel):
    message: str

# 🔹 API endpoints
@app.get("/")
async def root():
    """Root endpoint met status en route-informatie."""
    return {"message": "Wiskoro API is live!", "status": "healthy"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint voor AI-chatbot met wiskundefocus."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Yo, drop even een vraag! 📢")

    is_valid, error_message = validate_math_question(request.message)
    if not is_valid:
        return {"response": error_message}

    try:
        bot_response = await get_ai_response(request.message)
        return {"response": bot_response}
    except Exception as e:
        logger.error("Chat endpoint error: %s", str(e), exc_info=True)
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if Database.pool:
            async with Database.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
        return JSONResponse(content={"status": "healthy", "database": "connected"})
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})

# 🔹 Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services en log environment info."""
    try:
        await Database.create_pool()
        logger.info("✅ Application startup complete")
    except Exception as e:
        logger.error("❌ Startup error: %s", str(e), exc_info=True)
        raise

# 🔹 Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup bij afsluiten."""
    try:
        if Database.pool:
            await Database.pool.close()
        logger.info("✅ Application shutdown complete")
    except Exception as e:
        logger.error("❌ Shutdown error: %s", str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
