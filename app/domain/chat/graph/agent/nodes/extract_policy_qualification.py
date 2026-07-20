from app.domain.chat.graph.agent.states.credential_state import CredentialState
from app.infrastructure.llm.gpt import get_llm_gpt
from app.rag.policy_retriever import search_policy_info
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

_llm = get_llm_gpt()

PROMPT = ChatPromptTemplate.from_template(
    """
    당신은 복지 정책의 신청 조건을 판단하는 역할을 수행합니다.

    [규칙]
    1. 문서에 없는 정보는 추론하지 말고, 문서에 있는 정보만을 기반으로 판단합니다.
    2. 주어진 정책과 직접 관련된 신청 대상, 소득·재산·나이·거주지 등 판정 조건을 추출합니다.
    3. 문서가 없거나 주어진 정책과 관련된 자격 조건을 확인할 수 없다면 qualification을 null로 반환합니다.
    4. 단순한 신청 방법, 기간, 제출 서류는 자격 조건으로 사용하지 않습니다.

    [정책 이름]
    {policy_name}

    [문서 목록]
    {docs}
    """
)


class ExtractedQualification(BaseModel):
    qualification: str | None = Field(
        default=None,
        description="문서에서 확인한 정책 신청 자격 조건. 확인할 수 없으면 null",
    )


def _format_docs(docs: list) -> str:
    formatted: list[str] = []
    for index, doc in enumerate(docs, start=1):
        content = getattr(doc, "page_content", str(doc))
        metadata = getattr(doc, "metadata", {})
        formatted.append(f"[{index}] metadata={metadata}\n{content}")
    return "\n\n".join(formatted)


async def extract_policy_qualification(state: CredentialState) -> dict:
    policy_name = (state.get("policy_name") or "").strip()
    if not policy_name:
        return {"credential": None}

    docs = await search_policy_info(
        f"{policy_name} 신청 자격 지원 대상 선정 기준 소득 재산 나이",
        5,
    )
    if not docs:
        return {"credential": None}

    structured_llm = _llm.with_structured_output(ExtractedQualification)
    response = await structured_llm.ainvoke(
        PROMPT.format_messages(
            policy_name=policy_name,
            docs=_format_docs(docs),
        )
    )
    qualification = (response.qualification or "").strip() or None
    return {"credential": qualification}
