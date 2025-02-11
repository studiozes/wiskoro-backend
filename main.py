import os
import logging
import asyncio
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# 🔹 Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 🔹 Settings
class Settings(BaseSettings):
    MISTRAL_API_KEY: str
    AI_TIMEOUT: int = 15
    CACHE_EXPIRATION: int = 3600  

    class Config:
        case_sensitive = True

settings = Settings()

# 🔹 AI chatbot logica
async def get_ai_response(user_question: str) -> str:
    """Haalt AI-respons op via Mistral AI API."""
    API_URL = "https://api.mistral.ai/v1/chat/completions"
    MODEL = "mistral-medium"

    headers = {
        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_question}],
        "max_tokens": 200,
        "temperature": 0.7,
        "top_p": 0.9
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=settings.AI_TIMEOUT)
        response.raise_for_status()
        response_data = response.json()

        if "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0]["message"]["content"].strip()

        raise ValueError("Ongeldig AI antwoord")

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="AI request timeout ⏳ Probeer het later nog eens!")
    except requests.exceptions.RequestException as e:
        logger.error(f"AI API fout: {str(e)}")
        raise HTTPException(status_code=503, detail="Mistral AI is tijdelijk niet bereikbaar! 🔧")

# 🔹 FastAPI setup
app = FastAPI(title="Wiskoro AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://wiskoro.nl", "https://www.wiskoro.nl"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 🔹 API models
class ChatRequest(BaseModel):
    message: str

# 🔹 API endpoints
@app.get("/")
async def root():
    return {"message": "Wiskoro API is live!", "status": "healthy"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint voor AI-chatbot met Mistral AI."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Yo, drop even een vraag! 📢")

    try:
        bot_response = await get_ai_response(request.message)
        return {"response": bot_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Er ging iets mis met de AI 😕 Fout: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "healthy"})

# 🔹 Startup event
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("✅ Application startup complete")
    except Exception as e:
        logger.error("❌ Startup error: %s", str(e), exc_info=True)
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
