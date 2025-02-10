import os
import asyncpg
import requests
import smtplib
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic_settings import BaseSettings
from email.mime.text import MIMEText

# 🔹 Logging configureren
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 🔹 Configuratie met Pydantic voor environment variables
class Settings(BaseSettings):
    DATABASE_URL: str
    HUGGINGFACE_API_KEY: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_RECEIVER: str

    class Config:
        case_sensitive = True

settings = Settings()

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

# 🔹 AI integratie met Hugging Face
async def get_ai_response(user_question: str) -> str:
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {"inputs": user_question}

    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1",
            headers=headers,
            json=payload,
            timeout=10  # Kortere timeout voor snellere respons
        )
        response.raise_for_status()
        response_data = response.json()

        if isinstance(response_data, list) and response_data:
            return response_data[0].get("generated_text", "Ik snap je vraag ff niet. 🤔")
        return "AI gaf een rare respons. Probeer opnieuw. 🤖"

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="AI service timeout ⏳")
    except requests.exceptions.RequestException as e:
        logger.error(f"AI API error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fout bij ophalen AI antwoord 🔧")

# 🔹 FastAPI-instantie & middleware
app = FastAPI(title="Wiskoro API", version="1.0.0")

# CORS instellen (nodig voor frontend integratie)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Later beperken tot specifieke domeinen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 API request model
class ChatRequest(BaseModel):
    message: str

@app.post("/chat", tags=["Chatbot"])
async def chat(request: ChatRequest):
    user_question = request.message
    bot_response = await get_ai_response(user_question)

    conn = await Database.get_connection()
    try:
        await conn.execute(
            "INSERT INTO logs (vraag, antwoord, status) VALUES ($1, $2, $3)",
            user_question, bot_response, "succes"
        )
    except Exception as e:
        logger.error(f"Database logging error: {str(e)}", exc_info=True)
    finally:
        await conn.release()

    return {"response": bot_response}

# 🔹 Health Check Endpoint
@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "ok", "message": "Wiskoro API draait soepel 🚀"}

# 🔹 Dagelijkse e-mailfunctie
async def send_daily_email():
    try:
        conn = await Database.get_connection()
        result = await conn.fetch("SELECT COUNT(*), ARRAY_AGG(vraag) FROM logs WHERE timestamp >= CURRENT_DATE;")
        await conn.release()

        total_questions = result[0]["count"]
        questions_list = result[0]["array_agg"]

        email_content = f"""
        <html>
        <body>
        <h2>📊 Dagelijkse Wiskoro Stats</h2>
        <p><b>🔢 Totaal aantal vragen vandaag:</b> {total_questions}</p>
        <p><b>❓ Vragen die gesteld zijn:</b></p>
        <ul>
        {''.join(f'<li>{q}</li>' for q in questions_list) if questions_list else "<li>Geen vragen vandaag.</li>"}
        </ul>
        </body>
        </html>
        """

        msg = MIMEText(email_content, "html")
        msg["Subject"] = "📊 Dagelijkse Wiskoro Stats"
        msg["From"] = settings.SMTP_USERNAME
        msg["To"] = settings.EMAIL_RECEIVER

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USERNAME, settings.EMAIL_RECEIVER, msg.as_string())

        logger.info("✅ Dagelijkse e-mail succesvol verzonden!")

    except Exception as e:
        logger.error(f"⚠️ Fout bij verzenden e-mail: {str(e)}", exc_info=True)

# 🔹 Scheduler voor dagelijks rapport om 21:30
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    await Database.create_pool()
    scheduler.add_job(send_daily_email, "cron", hour=21, minute=30)
    scheduler.start()
