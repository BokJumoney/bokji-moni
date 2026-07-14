# SQLModel engine 및 SessionLocal 설정
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

from app.infrastructure.config import settings

# 엔진 생성 (psycopg 드라이버 사용)
engine = create_engine(settings.database_url, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """
    DB 초기화:
    - pgvector 확장 활성화
    - SQLModel 메타데이터 기반 테이블 생성
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 의존성 주입용 세션 제공"""
    with Session(engine) as session:
        yield session
