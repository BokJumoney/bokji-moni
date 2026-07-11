# # SQLModel engine 및 SessionLocal 설정
# from SQLModel import SQLModel, create_engine, Session
# from config import settings

# DB_URL = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# engine = create_engine(DB_URL, echo=True) # DB 엔진 생성 (커넥션 풀 관리)

# def init_db():
#     SQLModel.metadata.create_all(engine) # 모든 테이블 모델의 테이블을 생성

# def get_session():
#     with Session(engine) as session: # 세션을 열기
#         return session