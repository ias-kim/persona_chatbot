from fastapi import APIRouter
from personas import get_all_personas
from questions import get_all_questions

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/personas")
async def get_personas():
    personas = get_all_personas()
    return {"personas": personas, "count": len(personas)}


@router.get("/questions")
async def get_questions(lang: str = "ko"):
    questions = get_all_questions(lang)
    return {"questions": questions, "total": len(questions), "lang": lang}
