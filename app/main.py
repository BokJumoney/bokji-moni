from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.domain.chat.api.chat_router import router as chat_router
from app.domain.user.api.auth_router import router as auth_router
from app.domain.admin.api.admin_router import router as admin_router
from app.domain.admin.api.admin_policy import router as admin_policy_router
from app.infrastructure.config import settings


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


# import json
# from app.parsers.kordoc.kordoc_parser import parse_hwpx
# from app.parsers.kordoc.normalize_markdown import normalize_markdown
# from app.parsers.kordoc.form_splitter import split_forms
# from app.parsers.kordoc.table_parser import parse_table
# from app.parsers.kordoc.document_classifier import extract_document_name
# from app.infrastructure.db.connection import init_db
# #전체 파이프라인 실행
# from app.parsers.kordoc.document_classifier import (
#     classify_document,
#     DocumentType
# )


# from app.infrastructure.llm.structurer_document import (
#     structure_document
# )


# from app.rag.form_loader import (
#     load_form_documents
# )


# from app.rag.ingest_form import (
#     save_documents
# )



# def main():

#     init_db()
#     # ==========================
#     # 1. HWPX Parsing
#     # ==========================
#     #기저귀 조제분유 지원 신청서
#     markdown = parse_hwpx(
#         "data/forms/기저귀 조제분유 지원 신청서.hwpx"
#     )



#     markdown = normalize_markdown(
#         markdown
#     )


#     forms = split_forms(
#         markdown
#     )


#     print(
#         "전체 form:",
#         len(forms)
#     )

#     for i, form in enumerate(forms):

#         print("="*50)
#         print(i)
#         print(form[:200])


#     # ==========================
#     # 2. 신청서 필터링
#     # ==========================

#     applications = []


#     for form in forms:


#         doc_type = classify_document(
#             form
#         )
        

#         if doc_type == DocumentType.APPLICATION or doc_type == DocumentType.REPORT:

#             form_name = extract_document_name(form)
#             print("추출 이름:", form_name)
#             if form_name is None:
#                 continue

#             applications.append(
#                 {
#                     "name": form_name,
#                     "content": form
#                 }
#             )


#     print(
#         "신청서:",
#         len(applications)
#     )



#     # ==========================
#     # 3. LLM 구조화
#     # ==========================

#     all_forms = []


#     for application in applications:

#         form_name = application["name"]

#         form = application["content"]


#         table_json = parse_table(form)


#         if table_json is None:
#                 continue



#         result = structure_document(

#             json.dumps(
#                 table_json,
#                 ensure_ascii=False
#             )

#         )
#         form_name = extract_document_name(form)
#         print("추출 이름:", form_name)  
#         # 신청서 파일 정보 추가
#         for form_data in result["forms"]:

#             form_data["form_name"] = form_name
#             form_data["file_path"] = "data/forms/기저귀 조제분유 지원 신청서.hwpx"
#         all_forms.extend(
#             result["forms"]
#         )
#         print(form_data)

#     schema = {

#         "forms":
#             all_forms

#     }

#     # ==========================
#     # 4. Schema 저장
#     # ==========================

#     with open(

#         "output/form_schema2.json",

#         "w",

#         encoding="utf-8"

#     ) as f:


#         json.dump(

#             schema,

#             f,

#             ensure_ascii=False,

#             indent=2

#         )


#     print(
#         "form_schema 저장 완료"
#     )



#     # ==========================
#     # 5. Vector DB 저장
#     # ==========================


#     documents = load_form_documents()


#     save_documents(
#         documents
#     )


#     print(
#         "Vector DB 저장 완료"
#     )





# if __name__ == "__main__":

#     main()

