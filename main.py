import os
import asyncpg
import requests
import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
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
    DATABASE_URL: str
    HUGGINGFACE_API_KEY: str
    AI_TIMEOUT: int = 15
    CACHE_EXPIRATION: int = 3600  

    class Config:
        case_sensitive = True

settings = Settings()

# 🔹 In-memory cache
class LocalCache:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self.cache and time.time() - self.timestamps[key] < settings.CACHE_EXPIRATION:
            return self.cache[key]
        return None

    def set(self, key: str, value: str):
        self.cache[key] = value
        self.timestamps[key] = time.time()

cache = LocalCache()

# 🔹 AI chatbot logica
async def get_ai_response(user_question: str) -> str:
    """Haalt AI-respons op via Hugging Face API met wiskundefocus."""
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response

    AI_MODEL = "google/flan-t5-large"

    # 🔹 Verbeterde prompt voor beter antwoord
    math_prompt = f"""
    **Jij bent een ervaren wiskundeleraar die uitlegt in jongerentaal.**
    
    🔢 *Beantwoord deze wiskundevraag stap voor stap en geef het eindantwoord met een ✅:*
    
    **Vraag:** {user_question}
    
    **Antwoord:**
    """

    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": math_prompt,
        "parameters": {
            "do_sample": True,  # Zorgt ervoor dat het model creatief een antwoord genereert
            "temperature": 0.7,  # Meer variatie in antwoorden
            "max_length": 300,   # Vermijd te korte antwoorden
            "top_p": 0.9
        }
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{AI_MODEL}",
            headers=headers,
            json=payload,
            timeout=settings.AI_TIMEOUT
        )
        response.raise_for_status()
        response_data = response.json()

        # 🔹 Controleer of de AI een echt antwoord heeft gegenereerd
        if isinstance(response_data, list) and "generated_text" in response_data[0]:
            result = response_data[0]["generated_text"].strip()
            
            # Zorg ervoor dat het antwoord niet gelijk is aan de vraag
            if result.lower().strip() == user_question.lower().strip():
                raise ValueError("De AI heeft de vraag herhaald in plaats van een antwoord te geven.")

            cache.set(user_question, result)
            return result

        raise ValueError("Onverwacht API response formaat")

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Yo fam, deze wiskundevraag is pittig! Probeer het nog een keer! ⏳")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"De AI is even off-duty, kom zo terug! 🔧 Fout: {str(e)}")

# 🔹 FastAPI setup
app = FastAPI(title="Wiskoro API", version="1.0.0")

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
    """Endpoint voor AI-chatbot met wiskundefocus."""
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
