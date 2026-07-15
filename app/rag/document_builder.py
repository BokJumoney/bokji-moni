import json
import textwrap
from langchain_core.documents import Document


def json_to_documents(path):

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)


    documents = []


    for form in data.get("forms", []):

        form_name = form.get("form_name", "")
        description = form.get("description", "")

        # 추가된 alias 처리
        aliases = form.get("aliases", [])


        for section in form.get("sections", []):

            fields = section.get("fields", [])


            # fields 없는 안내문 section은 제외
            if not fields:
                continue


            field_texts = []
            keywords = []


            for field in fields:

                name = field.get("name", "")

                if name:
                    keywords.append(name)


                field_content = f"""
- 항목명: {name}
"""


                if field.get("required"):
                    field_content += "- 필수항목\n"


                if field.get("condition"):
                    field_content += (
                        f"- 작성 조건: "
                        f"{field.get('condition')}\n"
                    )


                options = field.get("options", [])

                if options:
                    field_content += (
                        "- 선택지:\n"
                    )

                    for option in options:
                        field_content += (
                            f"  - {option}\n"
                        )


                field_texts.append(
                    field_content.strip()
                )


            content = textwrap.dedent(f"""
                문서 종류: 복지 신청서


                신청서명:
                {form_name}


                관련 신청서명:
                {", ".join(aliases)}


                신청서 설명:
                {description}


                작성 영역:
                {section.get("title","")}


                영역 설명:
                {section.get("description","")}


                작성해야 하는 항목:

                {chr(10).join(field_texts)}
            """)


            documents.append(
                Document(
                    page_content=content.strip(),

                    metadata={
                        "category": "복지 신청서",

                        "form_name": form_name,

                        "aliases": ",".join(aliases),

                        "section": section.get(
                            "title",
                            ""
                        ),

                        "keywords": ",".join(keywords),
                        "has_fields": len(fields) > 0
                    }
                )
            )


    return documents