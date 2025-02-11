import os
import re
import requests
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# 🔹 Logging configuratie
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Wiskundige context helpers
MATH_CONTEXTS = {
    'basis': ['optellen', 'aftrekken', 'plus', 'min', '+', '-'],
    'vermenigvuldigen': ['keer', 'maal', '*', '×', 'vermenigvuldig'],
    'delen': ['delen', 'gedeeld', '/', '÷'],
    'breuken': ['breuk', 'noemer', 'teller', '/'],
    'procenten': ['procent', '%', 'percentage'],
    'meetkunde': ['oppervlakte', 'omtrek', 'volume', 'hoek', 'driehoek', 'vierkant', 'cirkel'],
    'vergelijkingen': ['vergelijking', '=', 'x', 'y', 'onbekende']
}

CONTEXT_PROMPTS = {
    'basis': "Laat zien hoe je optelt/aftrekt stap voor stap.",
    'vermenigvuldigen': "Splits grote berekeningen op in kleinere stappen.",
    'delen': "Laat zien hoe je deelt, rond af op 2 decimalen als nodig.",
    'breuken': "Vereenvoudig breuken waar mogelijk.",
    'procenten': "Reken eerst om naar decimalen voor berekeningen.",
    'meetkunde': "Noem altijd de gebruikte formule eerst.",
    'vergelijkingen': "Los stap voor stap op, werk netjes naar x toe.",
    'algemeen': "Leg stap voor stap uit."
}

# 🔹 Systeem prompt template
SYSTEM_PROMPT = """Je bent Wiskoro, een Nederlandse wiskunde chatbot die in straattaal praat! 🧮

ANTWOORD REGELS:
1. ALTIJD in het Nederlands
2. ALTIJD kort en bondig (max 2 zinnen)
3. ALTIJD straattaal gebruiken
4. NOOIT vermelden dat je een AI of taalmodel bent
5. ALTIJD afsluiten met emoji

ANTWOORD FORMAAT:
"Yo! [antwoord]. [korte uitleg] 🧮💯"

Voor niet-wiskunde vragen:
"Yo! Sorry fam, ik help alleen met wiskunde en rekenen! 🧮"

Bij onduidelijke vragen:
"Sorry fam, snap je vraag niet helemaal. Kun je het anders zeggen? 🤔"

{context_prompt}

Voorbeeld voor 5 + 3:
"Yo! Het antwoord is 8.
Check: 5 plus 3 = 8, simpel toch! 🧮✨"

Voorbeeld voor onduidelijke vraag:
"Sorry fam, deze snap ik even niet 100%. Kun je het anders vragen? 🤔"
"""

# 🔹 Error messages
ERROR_MESSAGES = {
    "timeout": "Yo deze som duurt te lang fam! Probeer het nog een keer ⏳",
    "service": "Ff chillen, ben zo back! 🔧",
    "non_math": "Yo! Ik help alleen met wiskunde en rekenen! 🧮",
    "invalid": "Die vraag snap ik niet fam, retry? 🤔",
    "rate_limit": "Rustig aan fam! Probeer over een uurtje weer! ⏳"
}

# 🔹 Settings class (ongewijzigd)
class Settings(BaseSettings):
    """Applicatie instellingen."""
    MISTRAL_API_KEY: str = Field(..., description="Mistral API Key")
    AI_TIMEOUT: int = Field(10, description="Timeout voor AI requests")
    CACHE_EXPIRATION: int = Field(3600, description="Cache vervaltijd in seconden")
    MAX_RESPONSE_LENGTH: int = Field(200, description="Maximum lengte van antwoorden")
    MAX_TOKENS: int = Field(100, description="Maximum tokens voor AI response")
    ALLOWED_ORIGINS: list[str] = Field(
        ["https://wiskoro.nl", "https://www.wiskoro.nl"],
        description="Toegestane CORS origins"
    )

    class Config:
        env_file = ".env"

settings = Settings()

# 🔹 Validation functies
def identify_math_context(question: str) -> str:
    """Identificeer het type wiskundevraag."""
    question_lower = question.lower()
    for context, keywords in MATH_CONTEXTS.items():
        if any(keyword in question_lower for keyword in keywords):
            return context
    return 'algemeen'

def validate_math_question(question: str) -> bool:
    """Check of de vraag over wiskunde gaat."""
    math_indicators = sum(MATH_CONTEXTS.values(), [])  # Flatten alle keywords
    return any(indicator in question.lower() for indicator in math_indicators)

def verify_numerical_answer(question: str, answer: str) -> bool:
    """Controleer of numerieke antwoorden logisch zijn."""
    try:
        question_nums = [float(n) for n in re.findall(r'-?\d*\.?\d+', question)]
        answer_nums = [float(n) for n in re.findall(r'-?\d*\.?\d+', answer)]
        
        if not answer_nums:
            return True
            
        if any(abs(n) > 1000000 for n in answer_nums):
            return False
            
        if question_nums:
            max_question = max(abs(n) for n in question_nums)
            max_answer = max(abs(n) for n in answer_nums)
            if max_answer > max_question * 1000:
                return False
                
        return True
    except:
        return True

def validate_answer(question: str, answer: str, context: str) -> bool:
    """Controleer of het antwoord logisch is."""
    if any(c.isdigit() for c in question) and not any(c.isdigit() for c in answer):
        return False
        
    generic_responses = [
        "ik begrijp je vraag",
        "dat is een goede vraag",
        "laat me je helpen",
    ]
    if any(resp in answer.lower() for resp in generic_responses):
        return False
        
    if context == 'meetkunde' and 'formule' not in answer.lower():
        return False
        
    return verify_numerical_answer(question, answer)

def post_process_response(response: str) -> str:
    """Verwerk en schoon het antwoord op."""
    # Verwijder alle newlines en dubbele spaties
    response = ' '.join(response.split())
    
    # Verwijder metadata opmerkingen
    metadata_patterns = [
        r'\(Note:.*?\)',
        r'\[Note:.*?\]',
        r'\{Note:.*?\}',
        r'This response.*?based\.',
        r'As an AI.*?\.',
        r'I am.*?model\.',
        r'I\'m.*?model\.',
    ]
    
    for pattern in metadata_patterns:
        response = re.sub(pattern, '', response, flags=re.IGNORECASE)
    
    # Zorg dat er een emoji in zit
    if not any(char in response for char in ['🧮', '💯', '🤔', '💪', '✨']):
        response += ' 🧮'
    
    # Houd het kort
    if len(response) > settings.MAX_RESPONSE_LENGTH:
        response = response[:settings.MAX_RESPONSE_LENGTH].rsplit('.', 1)[0] + '! 💯'
    
    return response.strip()

# 🔹 Rate limiter
class RateLimiter:
    """Voorkom misbruik van de API."""
    def __init__(self):
        self._requests: Dict[str, list] = {}
        self._WINDOW_SIZE = 3600  # 1 uur
        self._MAX_REQUESTS = 50   # Max requests per uur
        
    async def check_rate_limit(self, client_ip: str) -> bool:
        now = time.time()
        if client_ip not in self._requests:
            self._requests[client_ip] = []
            
        self._requests[client_ip] = [
            req_time for req_time in self._requests[client_ip]
            if now - req_time < self._WINDOW_SIZE
        ]
        
        if len(self._requests[client_ip]) >= self._MAX_REQUESTS:
            return False
            
        self._requests[client_ip].append(now)
        return True

rate_limiter = RateLimiter()

# 🔹 Cache implementatie (ongewijzigd)
class LocalCache:
    """Cache voor snelle antwoorden."""
    def __init__(self):
        self._items: Dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._items:
            value, timestamp = self._items[key]
            if time.time() - timestamp < settings.CACHE_EXPIRATION:
                return value
            del self._items[key]
        return None

    def set(self, key: str, value: str) -> None:
        self._items[key] = (value, time.time())

    def clear_expired(self) -> None:
        current_time = time.time()
        self._items = {
            k: v for k, v in self._items.items()
            if current_time - v[1] < settings.CACHE_EXPIRATION
        }

    @property
    def size(self) -> int:
        return len(self._items)

cache = LocalCache()

# 🔹 Verbeterde AI response functie
async def get_ai_response(user_question: str, client_ip: str) -> Tuple[str, bool]:
    """Haalt AI-respons op met verbeterde validatie."""
    # Rate limiting
    if not await rate_limiter.check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail=ERROR_MESSAGES["rate_limit"])

    # Valideer wiskundevraag
    if not validate_math_question(user_question):
        return ERROR_MESSAGES["non_math"], False

    # Check cache
    cached_response = cache.get(user_question)
    if cached_response:
        return cached_response, True

    # Identificeer context en bouw prompt
    context = identify_math_context(user_question)
    context_prompt = CONTEXT_PROMPTS[context]
    prompt = SYSTEM_PROMPT.format(context_prompt=context_prompt)

    # Bouw volledige prompt
    full_prompt = f"{prompt}\n\n❓ Vraag: {user_question}\n\n✅ Antwoord:"

    try:
        async with asyncio.timeout(settings.AI_TIMEOUT):
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
                json={
                    "model": "mistral-medium",
                    "messages": [{"role": "system", "content": full_prompt}],
                    "max_tokens": settings.MAX_TOKENS,
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"].strip()

            # Valideer antwoord
            if not validate_answer(user_question, result, context):
                return "Sorry fam, deze snap ik even niet 100%. Kun je het anders vragen? 🤔", False

            # Process en cache antwoord
            processed_response = post_process_response(result)
            cache.set(user_question, processed_response)
            return processed_response, False

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=ERROR_MESSAGES["timeout"])
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail=ERROR_MESSAGES["service"])
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

# 🔹 API models (ongewijzigd)
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=500)

# 🔹 FastAPI app (ongewijzigd)
app = FastAPI(
    title="Wiskoro API",
    version="1.0.0",
    description="Nederlandse wiskunde chatbot met straattaal"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

# 🔹 API endpoints
@app.get("/")
async def root():
    """Status check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/chat")
async def chat(request: ChatRequest, client_request: Request) -> Dict[str, Any]:
    """Wiskunde chatbot endpoint."""
    try:
        response, is_cached = await get_ai_response(
            request.message,
            client_request.client.host
        )
        return {
            "response": response,
            "cached": is_cached,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=ERROR_MESSAGES["invalid"])

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

# 🔹 Startup event
@app.on_event("startup")
async def startup_event():
    """Start cache cleanup taak."""
    async def cleanup_cache():
        while True:
            try:
                cache.clear_expired()
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Cache cleanup error: {str(e)}")

    asyncio.create_task(cleanup_cache())
    logger.info("✅ Wiskoro API started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info"
    )
