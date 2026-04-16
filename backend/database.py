"""
데이터베이스 연결 설정

- 로컬: SQLite (설정 없이 바로 실행)
- 프로덕션: DATABASE_URL 환경변수로 PostgreSQL 전환
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./persona_interview.db")

# SQLite는 멀티스레드 허용 필요, PostgreSQL은 불필요
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def create_tables():
    """애플리케이션 시작 시 테이블 생성"""
    Base.metadata.create_all(bind=engine)
