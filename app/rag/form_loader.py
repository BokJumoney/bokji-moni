import json
from langchain_core.documents import Document
# json 스킴마 -> 렝체인 다큐먼트 변환
# LLM이 생성한 JSON은 사람이 보기 좋은 구조지만 rag검색에는 바로 사용할 수 없다.
# LangChain에서는 Document 형태가 필요하다 form_schema.json-> LnagChain 다큐먼트 

def load_form_documents():

    with open("output/form_schema2.json", encoding="utf-8") as f:
        data = json.load(f)

    documents = []

    for form in data["forms"]:
        form_name = form["form_name"]

        # ==========================
        # 신청서 전체 요약 Document
        # ==========================

        summary_sections = []


        for section in form["sections"]:

            fields = section.get(
                "fields",
                []
            )


            field_names = [
                field["name"]
                for field in fields
            ]


            if field_names:

                summary_sections.append(
                    f"""
영역:
{section["title"]}

작성 항목:
{", ".join(field_names)}
"""
                )


        summary_content = f"""
신청서명:
{form_name}


신청서 구성:
{chr(10).join(summary_sections)}
"""


        summary_metadata = {
            "document_type": "application_form_summary",
            "form_name": form_name,
            "section": "전체",
            "has_fields": True,
            "file": form.get("file"),
        }


        documents.append(
            Document(
                page_content=summary_content,
                metadata=summary_metadata
            )
        )



        # ==========================
        # 기존 영역별 Document
        # ==========================

        for section in form["sections"]:

            section_title = section["title"]

            fields = section.get(
                "fields",
                []
            )


            if not fields:
                continue


            field_text = []


            for field in fields:

                name = field["name"]

                options = field.get(
                    "options",
                    []
                )


                text = name


                if options:

                    text += "\n선택항목:\n"

                    text += "\n".join(options)


                field_text.append(text)



            content = f"""
신청서명:
{form_name}


영역:
{section_title}


작성 항목:
{chr(10).join(field_text)}
"""


            metadata = {
                "document_type": "application_form",
                "form_name": form_name,
                "section": section_title,
                "has_fields": True,
                "file": form.get("file"),
            }


            documents.append(
                Document(
                    page_content=content,
                    metadata=metadata
                )
            )


    return documents
