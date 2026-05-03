import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from agent import VoteGuideAgent
import tools
import firebase_service

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="VoteGuide API",
    description="Interactive Election Process Education Assistant",
    version="2.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize agent once at startup
agent = VoteGuideAgent()
logger.info("VoteGuide API started successfully")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    language: str = "en"

    @validator("message")
    def message_must_not_be_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 500:
            raise ValueError("Message cannot exceed 500 characters")
        return v

    @validator("language")
    def language_must_be_supported(cls, v):
        supported = ["en", "hi", "es", "fr", "ar", "pt", "bn", "zh", "sw"]
        if v not in supported:
            return "en"
        return v


class QuizAnswerRequest(BaseModel):
    question_id: int
    answer: int


class QuizScoreRequest(BaseModel):
    player_name: str
    score: int
    total: int

    @validator("player_name")
    def name_must_not_be_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Player name cannot be empty")
        if len(v) > 30:
            v = v[:30]
        return v

    @validator("score")
    def score_must_be_valid(cls, v):
        if v < 0 or v > 10:
            raise ValueError("Score must be between 0 and 10")
        return v


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    firebase_ok = firebase_service.is_available()
    return JSONResponse(content={
        "status": "ok",
        "service": "VoteGuide",
        "version": "2.0.0",
        "firebase": "connected" if firebase_ok else "unavailable"
    })


@app.get("/api/stages")
async def get_stages():
    data = tools.get_all_stages()
    response = JSONResponse(content={"stages": data})
    response.headers["Cache-Control"] = "max-age=3600"
    return response


@app.get("/api/stages/{stage_id}")
async def get_stage(stage_id: int):
    stage = tools.get_stage_by_id(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail=f"Stage {stage_id} not found")
    return JSONResponse(content=stage)


@app.get("/api/timeline")
async def get_timeline():
    data = tools.get_timeline()
    response = JSONResponse(content=data)
    response.headers["Cache-Control"] = "max-age=3600"
    return response


@app.get("/api/roles")
async def get_roles():
    data = tools.get_all_roles()
    response = JSONResponse(content={"roles": data})
    response.headers["Cache-Control"] = "max-age=3600"
    return response


@app.get("/api/glossary")
async def get_glossary():
    data = tools.get_glossary_sorted()
    return JSONResponse(content={"terms": data})


@app.get("/api/glossary/search/{query}")
async def search_glossary(query: str):
    results = tools.search_glossary(query)
    return JSONResponse(content={"terms": results, "query": query})


@app.get("/api/quiz")
async def get_quiz():
    # SECURITY: strips correct field server-side
    data = tools.get_quiz_questions_safe()
    return JSONResponse(content={"questions": data})


@app.post("/api/quiz/check")
async def check_answer(request: QuizAnswerRequest):
    result = tools.check_quiz_answer(request.question_id, request.answer)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return JSONResponse(content=result)


@app.post("/api/quiz/score")
async def save_score(request: QuizScoreRequest):
    """Save a quiz score to Firestore leaderboard."""
    result = await firebase_service.save_quiz_score(
        player_name=request.player_name,
        score=request.score,
        total=request.total
    )
    if not result:
        raise HTTPException(status_code=503, detail="Leaderboard service unavailable")
    return JSONResponse(content={"saved": True, "id": result})


@app.get("/api/leaderboard")
async def get_leaderboard():
    """Fetch top-10 quiz scores from Firestore."""
    scores = await firebase_service.get_leaderboard(limit=10)
    return JSONResponse(content={"leaderboard": scores})


@app.post("/api/chat")
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest):
    result = agent.chat(body.message)
    response_text = result["response"]

    if body.language != "en":
        try:
            translated = await firebase_service.translate_text(
                response_text, body.language
            )
            if translated:
                response_text = translated
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Fall back to English silently

    return JSONResponse(content={
        "response": response_text,
        "suggested_stage": result["suggested_stage"],
        "language": body.language
    })


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
