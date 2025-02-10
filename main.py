import os
import asyncpg
import requests
import smtplib
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from email.mime.text import MIMEText
import time
import asyncio
import re

# 🔹 Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)

# 🔹 Settings
class Settings(BaseSettings):
    DATABASE_URL: str
    HUGGINGFACE_API_KEY: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_RECEIVER: str
    RATE_LIMIT_PER_MINUTE: int = 30
    AI_TIMEOUT: int = 20  # Verhoogd voor complexere wiskundevragen
    CACHE_EXPIRATION: int = 3600  # 1 uur

    class Config:
        case_sensitive = True

settings = Settings()

# 🔹 In-memory cache
class LocalCache:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            if time.time() - self.timestamps[key] < settings.CACHE_EXPIRATION:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None

    def set(self, key: str, value: str):
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self._cleanup()

    def _cleanup(self):
        current_time = time.time()
        expired_keys = [k for k, t in self.timestamps.items() 
                       if current_time - t > settings.CACHE_EXPIRATION]
        for k in expired_keys:
            del self.cache[k]
            del self.timestamps[k]

cache = LocalCache()

# 🔹 Database connection pooling
class Database:
    pool = None

    @classmethod
    async def create_pool(cls, retries=3):
        for attempt in range(retries):
            try:
                cls.pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=5,
                    max_size=20,
                    command_timeout=10
                )
                logger.info("✅ Database pool succesvol aangemaakt")
                return
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"❌ Database pool creatie gefaald na {retries} pogingen: {e}")
                    raise
                logger.warning(f"⚠️ Database pool creatie poging {attempt + 1} gefaald, nieuwe poging...")
                await asyncio.sleep(2 ** attempt)

    @classmethod
    async def get_connection(cls):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.acquire()

    @classmethod
    async def release_connection(cls, conn):
        await cls.pool.release(conn)

def format_math_response(text: str) -> str:
    """Format wiskundige notaties voor betere leesbaarheid."""
    replacements = {
        '*': '×',
        '/': '÷',
        'sqrt': '√',
        '^2': '²',
        '^3': '³',
        'pi': 'π',
        'theta': 'θ',
        'alpha': 'α',
        'beta': 'β',
        'delta': 'Δ',
        'sum': '∑',
        'infinity': '∞'
    }
    
    formatted_text = text
    for old, new in replacements.items():
        formatted_text = formatted_text.replace(old, new)
    
    # Format vergelijkingen met spaties
    formatted_text = re.sub(r'(\d+)([\+\-\×\÷])', r'\1 \2 ', formatted_text)
    formatted_text = re.sub(r'([\+\-\×\÷])(\d+)', r' \1 \2', formatted_text)
    
    return formatted_text

def validate_math_question(question: str) -> Tuple[bool, str]:
    """Valideer of de vraag wiskunde-gerelateerd is."""
    math_keywords = [
        'plus', 'min', 'keer', 'gedeeld', 'deel', 'wortel', 'kwadraat', 'vergelijking',
        'functie', 'grafiek', 'formule', 'bereken', 'oplos', 'reken', 'uitkomst',
        '+', '-', '*', '/', '=', '%', '²', '³', 'π', 'pi', 'hoek', 'driehoek',
        'vierkant', 'rechthoek', 'cirkel', 'oppervlakte', 'omtrek', 'volume',
        'algebra', 'meetkunde', 'goniometrie', 'sin', 'cos', 'tan', 'logaritme',
        'macht', 'factor', 'breuk', 'percentage', 'gemiddelde', 'mediaan', 'modus'
    ]
    
    # Check voor getallen
    has_numbers = any(char.isdigit() for char in question)
    
    # Check voor wiskundige termen
    has_math_terms = any(keyword in question.lower() for keyword in math_keywords)
    
    if not (has_numbers or has_math_terms):
        return False, "Yo! Drop een wiskundevraag en ik help je ermee! 🔢 Bijvoorbeeld: 'Los 3x + 5 = 11 op' of 'Bereken de oppervlakte van een cirkel met straal 4'"
    
    return True, ""

# 🔹 AI chatbot met wiskunde focus
async def get_ai_response(user_question: str) -> str:
    """Haalt AI-respons op via Hugging Face API met wiskunde focus."""
    cached_response = cache.get(user_question)
    if cached_response:
        logger.info("Cache hit voor vraag: %s", user_question)
        return cached_response

    AI_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"

    math_prompt = f"""<s>[INST] Je bent een wiskundedocent die uitlegt in jongerentaal.
    Beantwoord deze vraag:
    {user_question}

    Volg deze regels:
    1. Leg elke stap duidelijk uit
    2. Gebruik emoji's waar passend
    3. Geef het eindantwoord met een ✅
    4. Gebruik straattaal op een natuurlijke manier
    5. Houd het kort maar duidelijk [/INST]"""

    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": math_prompt,
        "parameters": {
            "max_new_tokens": 500,
            "temperature": 0.7,
            "top_p": 0.95,
            "return_full_text": False,
            "stream": False
        }
    }

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
            # Format wiskundige notaties
            result = format_math_response(result)
            cache.set(user_question, result)
            return result

        raise ValueError("Onverwacht API response formaat")

    except requests.exceptions.Timeout:
        logger.error("AI timeout voor vraag: %s", user_question)
        raise HTTPException(
            status_code=504,
            detail="Yo fam, deze wiskundevraag is complex! Probeer het nog een x of splits je vraag op! ⏳"
        )
    except requests.exceptions.RequestException as e:
        logger.error("AI API error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="De wiskunde-AI is even offline, kom zo terug! 🔧"
        )

# 🔹 FastAPI setup
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=True,
    root_path=""
)

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://wiskoro.nl",
        "https://www.wiskoro.nl",
        "https://api.wiskoro.nl",
        "http://localhost:3000"  # Voor lokale ontwikkeling
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)

# 🔹 API models
class ChatRequest(BaseModel):
    message: str

# 🔹 Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Global error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Er is een onverwachte fout opgetreden."}
    )

# 🔹 API endpoints
@app.get("/")
async def root():
    """Root endpoint met status en route informatie."""
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "methods": list(route.methods) if route.methods else []
        })
    return {
        "message": "Wiskoro API is live!",
        "status": "healthy",
        "routes": routes,
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "unknown")
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint voor AI-chatbot met wiskunde focus"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Yo, drop even een vraag! 📢")

    # Valideer of het een wiskundevraag is
    is_valid, error_message = validate_math_question(request.message)
    if not is_valid:
        return {"response": error_message}

    try:
        bot_response = await get_ai_response(request.message)
        return {"response": bot_response}
    except Exception as e:
        logger.error("Chat endpoint error: %s", str(e), exc_info=True)
        raise

@app.get("/test")
async def test_endpoint():
    """Test endpoint voor basis API functionaliteit."""
    logger.info("Test endpoint aangeroepen")
    try:
        response = {
            "message": "Test endpoint werkt!",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        logger.info(f"Test endpoint response: {response}")
        return response
    except Exception as e:
        error_msg = f"Test endpoint error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if Database.pool:
            async with Database.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
        return JSONResponse(
            content={
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# 🔹 Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services en log environment info."""
    try:
        logger.info("🔄 Starting application with environment:")
        logger.info(f"PORT: {os.environ.get('PORT', 'not set')}")
        logger.info(f"HOST: {os.environ.get('HOST', 'not set')}")
        logger.info(f"RAILWAY_STATIC_URL: {os.environ.get('RAILWAY_STATIC_URL', 'not set')}")
        logger.info(f"RAILWAY_PUBLIC_DOMAIN: {os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'not set')}")
        
        await Database.create_pool()
        
        routes = []
        for route in app.routes:
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": route.name if route.name else "unnamed"
            })
        logger.info(f"📝 Registered routes: {routes}")
        
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
    port = int(os.getenv("PORT", 8080))
    logger.info("🔥 FastAPI wordt gestart op poort %d...", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
