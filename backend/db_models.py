"""
SQLAlchemy ORM 모델 (DB 테이블 정의)

테이블 구조:
  sessions  → 면접 세션 (페르소나, 언어)
  messages  → 대화 히스토리 (user / assistant / tool_result)
  answers   → Tool Calling으로 구조화된 답변 평가 데이터
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    persona    = Column(String, nullable=False)
    lang       = Column(String, default="ko")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    messages = relationship(
        "MessageRecord",
        back_populates="session",
        order_by="MessageRecord.id",
        cascade="all, delete-orphan",
    )
    answers = relationship(
        "AnswerRecord",
        back_populates="session",
        order_by="AnswerRecord.id",
        cascade="all, delete-orphan",
    )


class MessageRecord(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    role       = Column(String, nullable=False)   # "user" | "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("SessionRecord", back_populates="messages")


class AnswerRecord(Base):
    __tablename__ = "answers"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    session_id     = Column(String, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    question_id    = Column(Integer, nullable=False)
    question       = Column(Text, nullable=False)
    answer         = Column(Text, nullable=False)
    score          = Column(Integer, default=5)
    feedback       = Column(Text)                    # Haiku 실시간 피드백 텍스트
    # Tool Calling으로 추출된 구조화 데이터
    answer_summary = Column(Text, nullable=True)     # 1~2문 요약
    keywords       = Column(Text, nullable=True)     # JSON 배열 문자열 ["키워드1", ...]
    red_flags      = Column(Text, nullable=True)     # JSON 배열 문자열 ["우려점1", ...]
    input_tokens   = Column(Integer, default=0)
    output_tokens  = Column(Integer, default=0)
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("SessionRecord", back_populates="answers")
