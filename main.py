from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Wiskoro backend is live!"}

@app.post("/chat")
def chat(input_text: str):
    # Simpele echo-response voor test
    response = f"Je zei: {input_text}. Maar bro, laat me ff nadenken... 🤔"
    return {"response": response}
