"""
Pydantic 데이터 모델 정의
"""

from pydantic import BaseModel
from typing import Optional, List


class PersonaInfo(BaseModel):
    """페르소나 정보"""
    id: str
    name: str
    description: str


class Question(BaseModel):
    """면접 질문"""
    id: int
    question: str
    difficulty: str  # easy, medium, hard
    category: str  # self-intro, experience, skill, etc


class InterviewStartRequest(BaseModel):
    """면접 세션 시작 요청"""
    persona: str  # "hr", "technical", "executive"
    session_id: Optional[str] = None
    lang: str = "ko"  # "ko" | "ja"


class InterviewStartResponse(BaseModel):
    """면접 세션 시작 응답"""
    session_id: str
    persona: str
    status: str  # "ready"
    first_question: str
    questions: List[dict]  # 페르소나별 질문 리스트


class AnswerRequest(BaseModel):
    """사용자 답변 요청"""
    session_id: str
    question_id: int
    answer: str


class AnswerScore(BaseModel):
    """답변 평가 점수"""
    question_id: int
    question: str
    score: int  # 1-10
    feedback: str


class InterviewResultsResponse(BaseModel):
    """면접 결과 조회 응답"""
    session_id: str
    persona: str
    total_questions: int
    answered_count: int
    accuracy_rate: float  # 0.0 ~ 1.0
    answers: List[AnswerScore]


class ResetRequest(BaseModel):
    """세션 초기화 요청"""
    session_id: str
