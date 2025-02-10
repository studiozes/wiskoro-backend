from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Voor nu toestaan vanaf alle domeinen, kan later strikter
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    input_text: str

@app.get("/")
def read_root():
    return JSONResponse(content={"message": "Wiskoro backend is live!"}, media_type="application/json; charset=utf-8")

@app.post("/chat")
def chat(request: ChatRequest):
    response = f"Je zei: {request.input_text}. Maar bro, laat me ff nadenken... 🤔"
    return JSONResponse(content={"response": response}, media_type="application/json; charset=utf-8")

@app.get("/chat")
def chat_get(input_text: str):
    response = f"Je zei: {input_text}. Maar bro, laat me ff nadenken... 🤔"
    return JSONResponse(content={"response": response}, media_type="application/json; charset=utf-8")

from fastapi import FastAPI
from pydantic import BaseModel
import asyncpg
import os

app = FastAPI()

# Database URL van Railway ophalen
DATABASE_URL = os.getenv("DATABASE_URL")

# Connectie maken met PostgreSQL
async def connect_db():
    return await asyncpg.connect(DATABASE_URL)

# Zorg dat de tabel wordt aangemaakt
async def create_table():
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

# Startup event om de tabel aan te maken bij het starten van de backend
@app.on_event("startup")
async def startup():
    await create_table()
