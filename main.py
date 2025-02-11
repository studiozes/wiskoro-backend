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
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 🔹 Instellingen
class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    HUGGINGFACE_API_KEY: str = Field(..., description="Hugging Face API key")
    AI_TIMEOUT: int = Field(15, description="Timeout voor AI requests")
    CACHE_EXPIRATION: int = Field(3600, description="Cache-vervaltijd")
    ALLOWED_ORIGINS: list[str] = Field(["https://wiskoro.nl", "https://www.wiskoro.nl"], description="Toegestane CORS-origins")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# 🔹 Cache voor AI-antwoorden
class LocalCache:
    def __init__(self, expiration: int = settings.CACHE_EXPIRATION):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._expiration = expiration

    def get(self, key: str) -> Optional[str]:
        """Checkt cache en haalt waarde op als deze nog geldig is."""
        if key in self._cache and time.time() - self._timestamps[key] < self._expiration:
            return self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        """Slaat waarde op in cache."""
        self._cache[key] = value
        self._timestamps[key] = time.time()

cache = LocalCache()

# 🔹 AI-logica voor wiskunde-antwoorden
async def get_ai_response(user_question: str) -> str:
    """Haalt AI-respons op met duidelijke uitleg en GenZ/straattaal."""
    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response

    AI_MODEL = "google/flan-t5-large"

    # 🔢 Wiskundige prompt
    math_prompt = f"""Je bent een ervaren wiskundeleraar die uitlegt in jongerentaal.

🔢 **Vraag:** {user_question}

📖 **Antwoord (kort & duidelijk):**"""

    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": math_prompt,
        "parameters": {
            "max_length": 150,
            "temperature": 0.6,
            "top_p": 0.9,
            "return_full_text": False
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

        # Check en format antwoord
        if isinstance(response_data, list) and response_data:
            result = response_data[0].get("generated_text", "").strip()
            if not result or result.lower() == user_question.lower():
                raise ValueError("AI antwoord is onbruikbaar.")
            
            # ✅ Kort en bondig
            final_response = result.replace("**Antwoord:**", "").strip()
            cache.set(user_question, final_response)
            return final_response

        raise ValueError("Onverwacht API response formaat.")

    except requests.exceptions.RequestException as e:
        logger.error(f"AI request fout: {str(e)}")
        raise HTTPException(status_code=503, detail="AI is even off-duty, bro! 🔧")

# 🔹 Model voor chatberichten
class ChatRequest(BaseModel):
    """Model voor chatverzoeken."""
    message: str = Field(..., min_length=1, max_length=200)

# 🔹 FastAPI setup
app = FastAPI(title="Wiskoro API", version="1.0.0", description="AI-gebaseerde wiskundebot met GenZ vibes.")

# 🔹 CORS-instellingen
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint met status en welkomsbericht."""
    return {
        "message": "Wiskoro is online! Drop je wiskundevraag, bro! 🔢",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/chat")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """Verwerkt een wiskundevraag en geeft een AI-antwoord."""
    user_input = request.message.strip().lower()

    # Checkt of de vraag over wiskunde gaat
    math_keywords = ["plus", "min", "keer", "gedeeld", "wortel", "kwadraat", "oppervlakte", "omtrek", "volume", "sin", "cos", "tan", "log", "pi", "+", "-", "*", "/", "="]
    if not any(word in user_input for word in math_keywords) and not any(char.isdigit() for char in user_input):
        return {"response": "Yo bro, ik doe alleen wiskunde. Gooi een som en ik help je! 🔢"}

    try:
        response = await get_ai_response(request.message)
        return {"response": response}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Er ging iets mis! 😕")

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "cache_size": len(cache._cache)
    }

# 🔹 Startup event
@app.on_event("startup")
async def startup_event():
    """Startup event voor initialisatie."""
    logger.info("✅ Wiskoro API succesvol gestart!")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
