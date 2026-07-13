# 환경 변수 (Pydantic Settings)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "edudb"
    DB_USER: str = "edu"
    DB_PASSWORD: str = "1234"

    # Ollama (로컬 LLM)
    LOCAL_MODEL: str = "exaone3.5"
    LOCLAL_LLM_URL: str = "http://localhost:11434"

    # OpenAI (임베딩용)
    OPENAI_API_KEY: str = ""

    # pgvector / Vectorstore
    VECTOR_COLLECTION_NAME: str = "welfare_policies"
    VECTOR_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # CSV 적재
    WELFARE_CSV_PATH: str = "data/detail_policy1.csv"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

settings = Settings()