# 환경 변수 (Pydantic Settings)
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 실행 환경
    APP_ENV: Literal["development", "test", "production"] = "development"

    # PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "edudb"
    DB_USER: str = "edu"
    DB_PASSWORD: str = "1234"

    # Ollama (로컬 LLM)
    LOCAL_MODEL: str = "exaone3.5"
    LOCAL_LLM_URL: str = "http://localhost:11434"

    # OpenAI (임베딩용)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # 공공데이터포털 (공데포 저소득 복지 정책 API 키)
    WELFARE_API_KEY: str = ""

    #웹 검색 툴
    TAVILY_API_KEY:str ="TAVILY_API_KEY"

    # pgvector / Vectorstore 초기 데이터
    VECTOR_COLLECTION_NAME: str = "welfare_policy_vector"
    VECTOR_EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_EMBEDDING_DIMENSION: int = 1536

    # PDF 벡터
    VECTOR_PDF_COLLECTION_NAME: str = "welfare_policy_pdf_vector"
    VECTOR_FORM_COLLECTION_NAME: str = "welfare_forms"

    # CSV 적재
    WELFARE_CSV_PATH: str = "data/welfare_policy_details.csv"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150 #<-- 여기 바꿔야댐

    # 인증 세션 / 쿠키
    SESSION_COOKIE_NAME: str = "bokji_auth"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    SESSION_IDLE_MINUTES: int = 30
    SESSION_ABSOLUTE_HOURS: int = 24
    SESSION_TOUCH_INTERVAL_SECONDS: int = 300

    #알림 e-mail 발송
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_SENDER: str = ""
    SMTP_APP_PASSWORD: str = ""
    EMAIL_BACKEND: str = "console"

    REMINDER_DEMO_DELAY_SECONDS: int = 90
    REMINDER_AFTER_DAYS: int = 7

    # CORS 허용 origin
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def _validate_auth_settings(self) -> "Settings":
        # 운영 환경에서는 Secure 쿠키가 필수
        if self.APP_ENV == "production" and not self.SESSION_COOKIE_SECURE:
            raise ValueError(
                "APP_ENV=production 일 때 SESSION_COOKIE_SECURE=true 여야 합니다."
            )
        # SameSite=None 은 Secure 쿠키에서만 허용
        if (
            self.SESSION_COOKIE_SAMESITE == "none"
            and not self.SESSION_COOKIE_SECURE
        ):
            raise ValueError(
                "SESSION_COOKIE_SAMESITE='none' 일 때 SESSION_COOKIE_SECURE=true 여야 합니다."
            )
        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
