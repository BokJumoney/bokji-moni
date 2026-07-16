from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.domain.chat.api.chat_router import router as chat_router
from app.domain.user.api.auth_router import router as auth_router
from app.infrastructure.config import settings
from app.domain.admin.api.admin_router import router as admin_router
from app.domain.admin.api.admin_policy import router as admin_policy_router
from app.infrastructure.config import settings
from app.domain.subscription.api.subscription_router import router as subscription_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 기동 시: DB 초기화 + vectorstore 자동 적재
    from app.infrastructure.db.connection import init_db
    from app.infrastructure.vectorstore.ingest import ensure_ingested

    print("------ DB 초기화 ------")
    init_db()

    print("------ Vectorstore 적재 확인 ------")
    ensure_ingested()

    yield

    # 종료 시: 리소스 정리 (필요시)
    print("------ 서버 종료 ------")


app = FastAPI(
    title="BokJi-Moni API",
    description="AI 에이전트 기반 복지 정보 제공 서비스 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1/chat", tags=["챗봇"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["인증"])
app.include_router(admin_router, tags=["파일 업로드"])
app.include_router(
    subscription_router,
    prefix="/api/v1/subscriptions",
    tags=["정책 구독"],
)
app.include_router(admin_policy_router)

@app.get("/")
def home():
    return {
        "message": "복지 데이터 분석 API",
        "database_name": settings.DB_NAME,
    }


@app.get("/db")
def get_db_info():
    return {"message": "DB 데이터"}
