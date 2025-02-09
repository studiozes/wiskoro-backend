from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    input_text: str

@app.get("/")
def read_root():
    return {"message": "Wiskoro backend is live!"}

@app.post("/chat")
def chat(request: ChatRequest):
    response = f"Je zei: {request.input_text}. Maar bro, laat me ff nadenken... 🤔"
    return {"response": response}

@app.get("/chat")
def chat_get(input_text: str):
    response = f"Je zei: {input_text}. Maar bro, laat me ff nadenken... 🤔"
    return {"response": response}
