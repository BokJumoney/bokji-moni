from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

#LLM 기반 신청서 구조화: 비정형 신청서 → 검색 가능한 구조 데이터 변환 단계

model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

parser = JsonOutputParser()


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            너는 대한민국 복지 신청서 구조화 전문가이다.

            입력은 신청서 1개이다.

            HTML Table은 그대로 이해한다.

            목표는 신청서를 JSON으로 구조화하는 것이다.

            반드시 다음 규칙을 따른다.

            1. 신청서 제목은 form_name

            2. 큰 영역은 section

            3. 입력칸은 fields

            4. 체크박스는 checkbox

            5. 안내문은 description

            6. 원문에 없는 내용 생성 금지

            출력은 JSON만 출력한다.

            출력 형식

            {{
                "forms":[
                    {{

                        "form_name":"",

                        "aliases":[],

                        "description":"",

                        "sections":[

                            {{

                                "title":"",

                                "description":"",

                                "fields":[

                                    {{

                                        "name":"",

                                        "type":"text",

                                        "required":false,

                                        "condition":"",

                                        "options":[]

                                    }}

                                ]

                            }}

                        ]

                    }}
                ]
            }}
            """
        ),
        (
            "human",
            "{document}"
        )
    ]
)


chain = prompt | model | parser


def structure_document(document: str):

    print("=" * 50)

    print("LLM 구조화 시작")

    result = chain.invoke(
        {
            "document": document
        }
    )

    print("LLM 완료")

    print(
        result["forms"][0]["form_name"]
    )

    return result