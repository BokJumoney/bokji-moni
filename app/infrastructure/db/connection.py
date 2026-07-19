# SQLModel engine 및 SessionLocal 설정
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from app.domain.welfare.entity.models import WelfarePolicy
from app.domain.welfare.entity.welfareform import WelfareForm
from app.infrastructure.config import settings

# 엔진 생성 (psycopg 드라이버 사용)
engine = create_engine(settings.database_url, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """
    DB 초기화:
    - pgvector 확장 활성화
    - SQLModel 메타데이터 기반 테이블 생성

    create_all() 전에 모든 엔티티 모듈이 import 되어 SQLModel metadata 에
    등록되어야 한다. auth 엔티티는 main lifespan 의 router import 경로를 통해
    이미 등록되지만, chat 엔티티는 repository 가 늦게 import 될 수 있으므로
    여기서 명시적으로 import 한다.
    """
    # 아래 import는 모델을 metadata에 등록할 뿐 기존 엔티티 정의를 수정하지 않는다.
    # create_all은 없는 테이블을 만들지만 기존 테이블 컬럼을 ALTER하지 않는다.
    from app.domain.chat.entity import models as _chat_models  # noqa: F401
    from app.domain.subscription.entity import models as _subscription_models  # noqa: F401
    from app.domain.user.entity import models as _user_models  # noqa: F401
    from app.domain.welfare.entity import models as _welfare_models  # noqa: F401

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPI 의존성 주입용 세션 제공"""
    with Session(engine) as session:
        yield session
