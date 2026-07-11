# 환경 변수 (Pydantic Settings)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "edudb"
    DB_USER: str = "edu"
    DB_PASSWORD: int = 1234
    LOCAL_MODEL: str = "exaone3.5"
    LOCLAL_LLM_URL: str = "http://localhost:11434"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()