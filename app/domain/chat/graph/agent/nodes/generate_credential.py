import json
from typing import Literal

from app.domain.chat.graph.agent.states.credential_state import CredentialState
from app.infrastructure.llm.gpt import get_llm_gpt
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

_llm = get_llm_gpt()

PROMPT = ChatPromptTemplate.from_template("""
    당신은 사용자가 복지 정책 신청 자격을 가지고 있는지 판별하는 역할을 수행합니다.

    [규칙]
    1. 아래에 제공된 자격 요건과 사용자 정보만 비교합니다.
    2. 조건을 충족한다는 근거가 충분하면 eligible, 충족하지 않는 조건이 명확하면 ineligible로 판단합니다.
    3. 판정에 필요한 사용자 정보나 정책 기준이 빠져 있으면 추측하지 말고 undetermined로 판단합니다.
    4. reason에는 핵심 비교 근거를 한국어로 간결하게 작성합니다.
    5. missing_information에는 판정에 필요한데 사용자 정보에서 확인되지 않는 항목만 작성합니다.

    복지 정책
    {policy_name}

    자격 요건
    {credential}

    사용자 정보
    {user_background}
""")


class CredentialAssessment(BaseModel):
    eligibility: Literal["eligible", "ineligible", "undetermined"]
    reason: str = Field(description="자격 요건과 사용자 정보를 비교한 핵심 근거")
    missing_information: list[str] = Field(
        default_factory=list,
        description="판정에 필요하지만 사용자 정보에서 확인할 수 없는 항목",
    )


def _format_user_background(user_background) -> str:
    if hasattr(user_background, "model_dump"):
        data = user_background.model_dump()
    elif isinstance(user_background, dict):
        data = user_background
    else:
        return str(user_background)

    public_data = {
        key: value
        for key, value in data.items()
        if key not in {"user_id", "created_at", "updated_at"}
    }
    return json.dumps(public_data, ensure_ascii=False, default=str)


def _render_answer(policy_name: str, assessment: CredentialAssessment) -> str:
    status = {
        "eligible": "현재 제공된 정보 기준으로 신청 자격을 충족하는 것으로 판단됩니다.",
        "ineligible": "현재 제공된 정보 기준으로 신청 자격을 충족하지 않는 것으로 판단됩니다.",
        "undetermined": "현재 정보만으로는 신청 자격을 확정하기 어렵습니다.",
    }[assessment.eligibility]

    answer = f"{policy_name}: {status}\n판단 근거: {assessment.reason}"
    if assessment.missing_information:
        missing = ", ".join(assessment.missing_information)
        answer += f"\n추가 확인이 필요한 정보: {missing}"
    return answer + "\n※ 실제 선정 결과는 담당 기관의 심사에서 달라질 수 있습니다."


async def generate_credential(state: CredentialState) -> dict:
    policy_name = state.get("policy_name") or "해당 정책"
    structured_llm = _llm.with_structured_output(CredentialAssessment)
    assessment = await structured_llm.ainvoke(
        PROMPT.format_messages(
            policy_name=policy_name,
            credential=state.get("credential") or "확인할 수 없음",
            user_background=_format_user_background(state.get("user_background")),
        )
    )
    return {"answer": _render_answer(policy_name, assessment)}
