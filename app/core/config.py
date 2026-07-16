from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    # .env는 여러 Settings 클래스가 공유하므로, 여기 정의되지 않은 키는 무시
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()