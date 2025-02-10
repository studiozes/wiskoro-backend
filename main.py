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
import asyncpg
import os

app = FastAPI()

# PostgreSQL connectiegegevens ophalen
DATABASE_URL = os.getenv("DATABASE_URL")

@app.get("/db-test")
async def db_test():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        return {"status": "✅ Databaseverbinding succesvol!"}
    except Exception as e:
        return {"status": f"❌ Database connectie fout: {e}"}
