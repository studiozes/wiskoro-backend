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
