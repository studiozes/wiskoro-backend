from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse

app = FastAPI()

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
