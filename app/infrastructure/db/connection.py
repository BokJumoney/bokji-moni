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
    # 엔티티 메타데이터 등록 보장
    from app.domain.chat.entity import models as _chat_models  # noqa: F401
    from app.domain.welfare.entity import models as _welfare_models  # noqa: F401
    from app.domain.subscription.entity import models as _subscription_models  # noqa: F401
    from app.domain.user.entity import models as _user_models  # noqa: F401

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    SQLModel.metadata.create_all(engine)
    _ensure_welfare_subscription_columns()


def _ensure_welfare_subscription_columns() -> None:
    """기존 개발 DB의 welfare_policies에 구독용 컬럼을 비파괴적으로 추가한다.

    SQLModel.create_all()은 새 테이블만 만들고 기존 테이블에 컬럼을 추가하지
    않는다. 정식 마이그레이션 도구를 도입하기 전까지 IF NOT EXISTS DDL로
    스키마 차이만 보완하며, 기존 정책 행을 삭제하거나 변경하지 않는다.
    """
    statements = (
        "ALTER TABLE welfare_policies ADD COLUMN IF NOT EXISTS application_deadline DATE",
        "ALTER TABLE welfare_policies ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'",
        "ALTER TABLE welfare_policies ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE welfare_policies ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE welfare_policies ADD COLUMN IF NOT EXISTS abolished_at TIMESTAMP",
        "CREATE INDEX IF NOT EXISTS ix_welfare_policies_application_deadline ON welfare_policies (application_deadline)",
        "CREATE INDEX IF NOT EXISTS ix_welfare_policies_status ON welfare_policies (status)",
    )
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def get_session():
    """FastAPI 의존성 주입용 세션 제공"""
    with Session(engine) as session:
        yield session
