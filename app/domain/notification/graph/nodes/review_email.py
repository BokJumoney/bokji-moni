#이메일 검사 LLM 노드
from pydantic import Field, BaseModel

from app.domain.notification.graph.state import NotiState
from app.infrastructure.llm.gpt import get_llm_gpt

model = get_llm_gpt("gpt-5.6-terra", 0)

class ReviewEmail(BaseModel):
    confirmed: bool = Field(description="통과 여부")
    feedback: str = Field(description="탈락 시 구체적인 수정 지시사항")

review_email_model = model.with_structured_output(ReviewEmail)

def review_email(state: NotiState):
    content = state.get("content")
    policies = state.get("new_policies")

    prompt = f"""
        작성된 이메일 내용을 보고 이메일 작성 프롬프트를 잘 지켰는지 판단해서 그대로 사용할 지 고칠 지 판단하고, 어떻게 수정해야 하는지 자세하게 수정사항을 알려줘.
    
        <작성된 이메일 내용>
            {content}
        </작성된 이메일 내용>
        
        <이메일 작성 프롬프트>
            "우리 서비스 이용자들에게 보낼 e-mail 본문 작성해줘.
            정책이 여러 개 일 수 있는데 영역을 구분해서 작성해야해.
            정보 전달 위주로 정책 이름, 지원 자격, 지원 내용, 신청 기간 정도만 보기 좋게 적어줘."
        </이메일 작성 프롬프트>
        
    """

    result = review_email_model.invoke(prompt)

    return {"feedback" : result.feedback, "confirmed" : result.confirmed}