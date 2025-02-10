from fastapi import FastAPI
from pydantic import BaseModel
import asyncpg
import os

app = FastAPI()

# PostgreSQL connectiegegevens ophalen
DATABASE_URL = os.getenv("DATABASE_URL")

async def connect_db():
    """Maakt verbinding met de database."""
    return await asyncpg.connect(DATABASE_URL)

async def create_table():
    """Maakt de logs-tabel aan als deze nog niet bestaat."""
    conn = await connect_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vraag TEXT NOT NULL,
            antwoord TEXT NOT NULL,
            status TEXT NOT NULL
        );
    """)
    await conn.close()
    print("✅ Logs-tabel aangemaakt of bestaat al.")

# Startup event om de tabel aan te maken bij het opstarten van de backend
@app.on_event("startup")
async def startup():
    await create_table()

# API request model
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    user_question = request.message

    # Placeholder antwoord (later kan AI worden toegevoegd)
    bot_response = f"Je zei: {user_question}. Hier is je antwoord! 📚"

    # Log de interactie in de database
    conn = await connect_db()
    try:
        await conn.execute("""
            INSERT INTO logs (vraag, antwoord, status) 
            VALUES ($1, $2, $3)
        """, user_question, bot_response, "succes")
        await conn.close()
    except Exception as e:
        print(f"⚠️ Database fout bij logging: {e}")

    return {"response": bot_response}

@app.get("/")
async def root():
    return {"message": "Wiskoro API is live!"}

import smtplib
from email.mime.text import MIMEText
import asyncio
from datetime import datetime, timedelta

# E-mail configuratie
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "wiskoro.app@gmail.com"
SMTP_PASSWORD = "nieh bkjf aqdg mzuv"
EMAIL_RECEIVER = "wiskoro.app@gmail.com"

async def send_daily_email():
    try:
        conn = await connect_db()
        result = await conn.fetch("SELECT COUNT(*), ARRAY_AGG(vraag) FROM logs WHERE timestamp >= CURRENT_DATE;")
        await conn.close()

        total_questions = result[0]["count"]
        questions_list = result[0]["array_agg"]

        email_content = f"""\
        Hey Wiskoro-baas! 🚀

        Hier is je dagelijkse log:
        🔢 Totaal aantal vragen vandaag: {total_questions}
        ❓ Vragen die gesteld zijn:
        {chr(10).join(questions_list) if questions_list else "Geen vragen vandaag."}

        Keep grinding! 💪
        """

        msg = MIMEText(email_content)
        msg["Subject"] = "📊 Dagelijkse Wiskoro Stats"
        msg["From"] = SMTP_USERNAME
        msg["To"] = EMAIL_RECEIVER

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, EMAIL_RECEIVER, msg.as_string())

        print("✅ Dagelijkse e-mail succesvol verzonden!")

    except Exception as e:
        print(f"⚠️ Fout bij verzenden e-mail: {e}")

# Plan e-mail om elke dag om 21:30 te versturen
@app.on_event("startup")
async def schedule_daily_email():
    while True:
        now = datetime.now()
        target_time = now.replace(hour=21, minute=30, second=0)
        sleep_seconds = (target_time - now).total_seconds()
        if sleep_seconds < 0:
            sleep_seconds += 86400  # Voeg 1 dag toe

        await asyncio.sleep(sleep_seconds)
        await send_daily_email()
