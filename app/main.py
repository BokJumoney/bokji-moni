from fastapi import FastAPI

from app.domain.admin.api.admin_router import router as admin_router

app = FastAPI()
app.include_router(admin_router)

@app.get("/")
def home():
    return {"message": "복지 데이터 분석 API"}
