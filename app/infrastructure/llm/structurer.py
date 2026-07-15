# Markdown 문서를 GPT에게 전달하여 신청서 구조를 JSON으로 변환

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

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
너는 대한민국 공공기관 신청서(HWP/HWPX/PDF) 구조화 전문가이다.

입력 문서는 이미 하나의 신청서(Form) 단위로 분리되어 있다.

목표는 사람이 작성하는 신청서를
LLM과 프로그램이 사용할 수 있는 JSON Schema로 변환하는 것이다.

절대 내용을 요약하지 않는다.
원문의 구조를 최대한 유지한다.

========================
[1. Form 규칙]
========================

입력 문서는 하나의 Form이다.

forms 배열에는 반드시 하나의 form만 생성한다.

form_name은

가장 실제 신청서 제목을 사용한다.

예)

자산형성지원사업 참여(변경) 신청서
금융정보 등 제공 동의서
근로활동 및 소득신고서

"희망저축계좌 및 청년내일저축계좌 관련 서식"
같은 문서집 제목은 form_name으로 사용하지 않는다.

그런 문구는 description에 넣는다.

form_number에는

서식1
서식20
별지 제1호
별지 제1호의3

등을 저장한다.

aliases에는

신청 대상

사업명

계좌명

등 실제 문서 안에서 확인 가능한 이름만 저장한다.

예)

희망저축계좌Ⅰ

희망저축계좌Ⅱ

청년내일저축계좌

========================
[2. Section 규칙]
========================

Section은

큰 제목

상위 행(Row Header)

그룹 제목

기준으로 나눈다.

예)

신청자

가입자

근무정보

적립정보

저축목적

등

설명문은 description에 저장한다.

예)

"신청자와 가입자가 다른 경우 작성"

"해당하는 경우만 작성"

"중복참여자는 제한"

========================
[3. Field 규칙]
========================

사용자가 직접 입력하는 항목만 fields에 저장한다.

예)

성명

주소

전화번호

주민등록번호

직업

근무지명

저축금액

등

Field 형식

{
"name":"",
"type":"",
"required":false,
"condition":"",
"options":[]
}

========================
[4. required 규칙]
========================

다음 문구가 존재하면 required=true

필수

반드시

필

필수서류

미작성 시

작성하여야

작성 필

그 외에는 false

========================
[5. condition 규칙]
========================

다음 조건을 condition에 저장한다.

신청자와 가입자가 다른 경우

해당하는 경우 작성

선택한 경우 작성

군입대 예정인 경우

중복참여인 경우

재가입인 경우

조건이 없으면 ""

========================
[6. type 규칙]
========================

다음 규칙을 사용한다.

□ -> checkbox

○ -> radio

날짜 -> date

주민등록번호 -> resident_number

전화번호 -> phone

휴대전화 -> mobile

전자우편 -> email

금액 -> money

주소 -> address

숫자 -> number

그 외 -> text

========================
[7. Checkbox 규칙]
========================

□ 항목은

type="checkbox"

options에 모두 저장한다.

예)

□ 최초

□ 재가입

↓

"type":"checkbox"

"options":[
"최초",
"재가입"
]

새로운 선택지를 생성하지 않는다.

========================
[8. Description 규칙]
========================

다음은 절대 삭제하지 않는다.

작성방법

유의사항

조건

안내문

비고

처리기간

설명

section.description에 저장한다.

========================
[9. 출력 규칙]
========================

원문에 없는 내용 생성 금지

JSON 외 출력 금지

설명 금지

Markdown 금지

반드시 아래 형식만 출력

{
  "forms":[
    {
      "form_name":"",
      "form_number":"",
      "aliases":[],
      "description":"",
      "sections":[
        {
          "title":"",
          "description":"",
          "fields":[]
        }
      ]
    }
  ]
}
"""
),
(
"user",
"""
문서

{document}
"""
)
]
)

chain = prompt | model | parser


def structure_document(markdown: str):

    print("=" * 60)
    print("LLM 구조화 시작")
    print(f"문서 길이 : {len(markdown):,} chars")

    result = chain.invoke(
        {
            "document": markdown
        }
    )

    print("LLM 구조화 완료")

    forms = result.get("forms", [])

    print(f"Form 개수 : {len(forms)}")

    for idx, form in enumerate(forms, 1):
        print(f"[{idx}] {form.get('form_name')}")
        print(f"    Sections : {len(form.get('sections', []))}")

    print("=" * 60)

    return result