from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "복지 데이터 분석 API"}