#이메일 검사 LLM 노드
from pydantic import Field, BaseModel

from app.domain.notification.graph.format_policy import format_policy
from app.domain.notification.graph.email_prompt import (
    COMMON_PROMPT,
    REVIEW_PROMPT,
    PROMPT_MAP,
)
from app.domain.notification.graph.state import NotiState, EmailPromptRoute
from app.infrastructure.llm.gpt import get_llm_gpt

model = get_llm_gpt("gpt-5.6-terra", 0)

class ReviewEmail(BaseModel):
    confirmed: bool = Field(description="통과 여부")
    feedback: str = Field(description="탈락 시 구체적인 수정 지시사항")

review_email_model = model.with_structured_output(ReviewEmail)

def review_email(state: NotiState):
    title = state["title"]
    content = state["content"]
    policies = state["new_policies"]
    noti_type = state.get("noti_type", EmailPromptRoute.NEW_POLICY)
    web_search_data = state.get("web_search_data", "")

    policies_text = format_policy(policies)

    prompt = REVIEW_PROMPT.format(
        policies_text=policies_text,
        title=title,
        content=content,
        web_search_data=web_search_data,
        common_prompt=COMMON_PROMPT,
        policy_prompt=PROMPT_MAP[noti_type],
    )

    result = review_email_model.invoke(prompt)

    return {"feedback" : result.feedback, "confirmed" : result.confirmed}