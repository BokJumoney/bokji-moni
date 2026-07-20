"""
Answer Generator.

tool_executor가 모아온 근거 자료(state.context)를 바탕으로 최종
자연어 답변을 만든다. general_response_tool만 실행된 경우엔 이
노드 자체가 호출되지 않는다(post_tool_router.py 참고).

tool 선택(information_agent)은 gpt-4o-mini(저렴/빠름)를 쓰고,
최종 답변 생성은 좀 더 좋은 모델(gpt-4o)을 쓰도록 역할을 분리했다.

[구비서류 체크리스트 포맷팅] "구비서류/필요서류/체크리스트/준비물"을
묻는 질문은 문장으로 풀어쓰지 않고 체크박스 목록으로 정리하도록
프롬프트에 별도 규칙을 추가했다. 프론트엔드가 마크다운을 렌더링하지
않는 환경도 있을 수 있어 "- [ ]" 대신 어디서나 그대로 텍스트로 보이는
유니코드 체크박스(☐)를 쓰도록 지정했다. 마크다운 렌더링 환경이라면
"- [ ]"로 바꿔도 된다.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.domain.chat.graph.state2 import ChatState
from app.infrastructure.config import settings

OLLAMA_MODEL = settings.LOCAL_MODEL
OLLAMA_BASE_URL = settings.LOCAL_LLM_URL

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=settings.OPENAI_API_KEY,
    temperature=0,
)

generate_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """당신은 복지 정책 안내 서비스의 답변 생성 담당입니다.

아래 [문서]는 사용자 질문에 대해 검색된 근거 자료입니다. 반드시 이 문서
내용에 기반해서만 답변하세요. 문서에 없는 내용을 추측하거나 일반 지식으로
지어내지 마세요. 복지 지원 대상, 금액, 신청 방법 같은 정보는 틀리면
사용자에게 실질적인 피해를 줄 수 있습니다.

문서가 "관련 문서 없음"이거나 질문에 답할 만한 내용이 없으면, 아는 척
답하지 말고 다음처럼 솔직하게 안내하세요:
"정확한 정보를 찾지 못했습니다. 복지로(www.bokjiro.go.kr)나 관할
주민센터에 문의해보시기 바랍니다."
링크에만 하이퍼링크를 다세요.

답변 형식은 질문 종류에 따라 다르게 마크다운 형식으로 내보내세요.

1) 구비서류 / 필요 서류 / 체크리스트 / 준비물처럼 "서류 목록"을
   요청하는 질문이면, 문장으로 풀어쓰지 말고 아래 형식처럼 정리하세요.

   [정책명] 구비서류
   ☐ 서류명 (필요하면 짧은 비고)
   ☐ 서류명
   ☐ 서류명

   - 문서에서 확인된 서류만 나열하고, 없는 서류를 추측해서 채우지 마세요.
   - "해당자만 제출", "온라인 신청 시 생략 가능" 같은 조건은 그 서류
     항목 뒤에 괄호로 짧게 붙이세요.
   - 목록 앞뒤로 불필요한 인사말이나 부연 설명은 넣지 마세요.

2) 그 외 질문(지원 대상, 신청 방법, 정책 설명 등)이면 기존처럼
   2~5문장 정도의 자연스러운 문장으로 간결하게 답하세요. 굳이
   목록으로 쪼개지 않아도 되는 내용을 억지로 나열하지 마세요.

문서에 있는 문의처 전화번호, 근거 법령, 카드사 목록 같은 세부사항은
질문과 직접 관련 없으면 생략하세요.""",
        ),
        (
            "human",
            "질문:{question}\n\n문서:{documents}",
        ),
    ]
)

rag_chain = generate_prompt | llm


async def generate(state: ChatState):
    print("------ GENERATE START ------")
    question = state["question"]

    # tool_executor가 채운 근거 텍스트 (문자열 리스트)
    documents = state.get("context", [])

    documents_text = "\n\n".join(documents) if documents else "관련 문서 없음"

    print("LLM 호출 전")
    response = await rag_chain.ainvoke(
        {
            "question": question,
            "documents": documents_text,
        }
    )
    print("LLM 응답 완료")

    return {
        "answer": response.content
    }