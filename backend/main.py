"""
Persona Interview Chatbot — FastAPI Backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import create_tables
from routers import catalog, interview

load_dotenv()

app = FastAPI(
    title="Persona Interview Chatbot",
    description="페르소나 기반 면접 연습 API (Tool Calling + 모델 분리)",
    version="3.0.0"
)

create_tables()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(interview.router)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "3.0.0",
        "models": {
            "chat": interview.MODEL_CHAT,
            "report": interview.MODEL_REPORT,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
