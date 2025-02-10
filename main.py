import os
import asyncpg
import requests
import smtplib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel, BaseSettings
from email.mime.text import MIMEText
import time
import asyncio

# 🔹 Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    AI_TIMEOUT: int = 10
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
        # Cleanup oude cache entries
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
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

    @classmethod
    async def get_connection(cls):
        if not cls.pool:
            await cls.create_pool()
        return await cls.pool.acquire()

    @classmethod
    async def release_connection(cls, conn):
        await cls.pool.release(conn)

# 🔹 Rate limiting
class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, ip: str) -> bool:
        now = datetime.now()
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Verwijder oude requests
        self.requests[ip] = [ts for ts in self.requests[ip] 
                           if now - ts < timedelta(minutes=1)]
        
        if len(self.requests[ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            return False
        
        self.requests[ip].append(now)
        return True

rate_limiter = RateLimiter()

# 🔹 AI chatbot met caching
async def get_ai_response(user_question: str) -> str:
    # Check local cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response

    # Voeg GenZ context toe aan de prompt
    enhanced_prompt = f"""Je bent een wiskundeleraar die in GenZ/straattaal praat.
    Beantwoord deze wiskundevraag op een begrijpelijke manier in GenZ/straattaal: {user_question}"""

    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {"inputs": enhanced_prompt}

    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1",
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
        raise HTTPException(
            status_code=504,
            detail="Yo fam, deze vraag is te complex voor nu! Probeer het nog een x! ⏳"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"AI API error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="De AI is even offline, kom zo terug! 🔧"
        )

# 🔹 FastAPI setup
app = FastAPI(title="Wiskoro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In productie aanpassen naar specifieke domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 API models
class ChatRequest(BaseModel):
    message: str

    class Config:
        min_length = 2
        max_length = 500

# 🔹 API endpoints
@app.post("/chat")
async def chat(request: ChatRequest, client_request: Request):
    client_ip = client_request.client.host
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rustig aan G! Je gaat te snel! 🚦"
        )

    start_time = time.time()
    try:
        bot_response = await get_ai_response(request.message)
        processing_time = time.time() - start_time

        # Log naar database
        conn = await Database.get_connection()
        try:
            await conn.execute("""
                INSERT INTO logs (vraag, antwoord, status, processing_time) 
                VALUES ($1, $2, $3, $4)
            """, request.message, bot_response, "success", processing_time)
        except Exception as e:
            logger.error(f"Database logging error: {str(e)}", exc_info=True)
        finally:
            await Database.release_connection(conn)

        return {"response": bot_response}

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status = {
        "api": "healthy",
        "database": "unknown",
        "timestamp": datetime.now().isoformat()
    }

    try:
        conn = await Database.get_connection()
        await conn.execute("SELECT 1")
        await Database.release_connection(conn)
        status["database"] = "healthy"
    except Exception as e:
        status["database"] = f"unhealthy: {str(e)}"

    return JSONResponse(content=status)

# 🔹 Email functionaliteit
async def send_daily_email():
    """Verstuurt dagelijkse statistieken."""
    try:
        conn = await Database.get_connection()
        try:
            result = await conn.fetch("""
                SELECT 
                    COUNT(*) as total,
                    ARRAY_AGG(vraag) as vragen,
                    AVG(COALESCE(processing_time, 0)) as avg_time
                FROM logs 
                WHERE timestamp >= CURRENT_DATE;
            """)
        finally:
            await Database.release_connection(conn)

        total_questions = result[0]['total']
        questions_list = result[0]['vragen'] or []
        avg_time = round(result[0]['avg_time'] or 0, 2)

        email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>📊 Wiskoro Dagelijkse Stats</h2>
            <p><b>🔢 Totaal aantal vragen vandaag:</b> {total_questions}</p>
            <p><b>⚡ Gemiddelde antwoordtijd:</b> {avg_time} seconden</p>
            <p><b>❓ Vragen die gesteld zijn:</b></p>
            <ul>
            {''.join(f'<li>{q}</li>' for q in questions_list) if questions_list else '<li>Geen vragen vandaag.</li>'}
            </ul>
            <p>Keep grinding! 💪</p>
        </body>
        </html>
        """

        msg = MIMEText(email_content, "html")
        msg["Subject"] = "📊 Dagelijkse Wiskoro Stats"
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = settings.EMAIL_RECEIVER

        # Email versturen met retry mechanisme
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                logger.info("✅ Dagelijkse e-mail succesvol verzonden!")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"⚠️ Email verzenden gefaald na {max_retries} pogingen: {e}")
                    raise
                await asyncio.sleep(2 ** attempt)

    except Exception as e:
        logger.error(f"⚠️ Fout bij e-mail verwerking: {e}", exc_info=True)

# 🔹 Startup
@app.on_event("startup")
async def startup_event():
    """Initialize services."""
    try:
        await Database.create_pool()
        
        # Email scheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            send_daily_email,
            "cron",
            hour=21,
            minute=30,
            misfire_grace_time=300
        )
        scheduler.start()
        
        logger.info("✅ Applicatie succesvol gestart")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}", exc_info=True)
        raise

# 🔹 Shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup bij afsluiten."""
    if Database.pool:
        await Database.pool.close()
    logger.info("✅ Applicatie succesvol afgesloten")
