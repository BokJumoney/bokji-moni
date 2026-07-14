import json
from app.parsers.kordoc.kordoc_parser import parse_hwpx
from app.parsers.kordoc.normalize_markdown import normalize_markdown
from app.parsers.kordoc.form_splitter import split_forms
from app.parsers.kordoc.table_parser import parse_table
from app.parsers.kordoc.document_classifier import extract_document_name

#전체 파이프라인 실행
from app.parsers.kordoc.document_classifier import (
    classify_document,
    DocumentType
)


from app.infrastructure.llm.structurer_document import (
    structure_document
)


from app.rag.form_loader import (
    load_form_documents
)


from app.rag.ingest_form import (
    save_documents
)



def main():


    # ==========================
    # 1. HWPX Parsing
    # ==========================
    #기저귀 조제분유 지원 신청서
    markdown = parse_hwpx(
        "data/forms/기저귀 조제분유 지원 신청서.hwpx"
    )


    markdown = normalize_markdown(
        markdown
    )


    forms = split_forms(
        markdown
    )


    print(
        "전체 form:",
        len(forms)
    )

    for i, form in enumerate(forms):

        print("="*50)
        print(i)
        print(form[:200])


    # ==========================
    # 2. 신청서 필터링
    # ==========================

    applications = []


    for form in forms:


        doc_type = classify_document(
            form
        )
        

        if doc_type == DocumentType.APPLICATION or doc_type == DocumentType.REPORT:

            form_name = extract_document_name(form)
            print("추출 이름:", form_name)
            if form_name is None:
                continue

            applications.append(
                {
                    "name": form_name,
                    "content": form
                }
            )


    print(
        "신청서:",
        len(applications)
    )



    # ==========================
    # 3. LLM 구조화
    # ==========================

    all_forms = []


    for application in applications:

        form_name = application["name"]

        form = application["content"]


        table_json = parse_table(form)


        if table_json is None:
                continue



        result = structure_document(

            json.dumps(
                table_json,
                ensure_ascii=False
            )

        )
        form_name = extract_document_name(form)
        print("추출 이름:", form_name)  
        # 신청서 파일 정보 추가
        for form_data in result["forms"]:

            form_data["form_name"] = form_name
            form_data["file"] = {
                "path": "data/forms/기저귀 조제분유 지원 신청서.hwpx"
            }
        all_forms.extend(
            result["forms"]
        )


    schema = {

        "forms":
            all_forms

    }



    # ==========================
    # 4. Schema 저장
    # ==========================

    with open(

        "output/form_schema2.json",

        "w",

        encoding="utf-8"

    ) as f:


        json.dump(

            schema,

            f,

            ensure_ascii=False,

            indent=2

        )


    print(
        "form_schema 저장 완료"
    )



    # ==========================
    # 5. Vector DB 저장
    # ==========================


    documents = load_form_documents()


    save_documents(
        documents
    )


    print(
        "Vector DB 저장 완료"
    )





if __name__ == "__main__":

    main()