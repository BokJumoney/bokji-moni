#이메일 검사 LLM 노드
from pydantic import Field, BaseModel

from app.domain.notification.graph.format_policy import format_policy
from app.domain.notification.graph.new_policy_prompt import BASE_PROMPT
from app.domain.notification.graph.state import NotiState
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

    policies_text = format_policy(policies)

    prompt = f"""
        작성된 이메일 내용을 보고 이메일 작성 프롬프트를 잘 지켰는지 판단해서 그대로 사용할 지 고칠 지 판단하고, 어떻게 수정해야 하는지 자세하게 수정사항을 알려줘.
        <정책 데이터>
            {policies_text}
        </정책 데이터>
    
        <작성된 이메일 내용>
            [제목]
            {title}
            
            [본문]
            {content}
        </작성된 이메일 내용>
        
        <이메일 작성 프롬프트>
        """ + BASE_PROMPT + """
        </이메일 작성 프롬프트>
        """

    result = review_email_model.invoke(prompt)

    return {"feedback" : result.feedback, "confirmed" : result.confirmed}