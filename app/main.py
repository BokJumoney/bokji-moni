from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.domain.chat.api.chat_router import router as chat_router
from app.infrastructure.config import settings

app = FastAPI(
    title="BokJi-Moni API",
    description="AI 에이전트 기반 복지 정보 제공 서비스 API",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"], # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1/chat", tags=["챗봇"])

@app.get("/")
def home():
    return {
        "message": "복지 데이터 분석 API",
        "database_name": settings.DB_NAME    
    }

@app.get("/db")
def getDB():
    return { "message": "DB 데이터" }