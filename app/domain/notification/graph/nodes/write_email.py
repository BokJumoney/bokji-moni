# 이메일 작성 LLM 노드
from pydantic import BaseModel

from app.domain.notification.graph.format_policy import format_policy
from app.domain.notification.graph.new_policy_prompt import BASE_PROMPT
from app.domain.notification.graph.state import NotiState
from app.infrastructure.llm.gpt import get_llm_gpt

model = get_llm_gpt("gpt-5.6-luna", 0)

class WriteEmailForm(BaseModel):
    title: str
    content: str

write_email_model = model.with_structured_output(WriteEmailForm)

def write_email(state: NotiState):
    policies = state["new_policies"]
    feedback = state.get("feedback")
    count = state.get("iter_count", 0)

    policies_text = format_policy(policies)

    print(f"e-mail 작성 중...{count + 1}회 시도")

    if not feedback:
        prompt = BASE_PROMPT + """
        <정책 데이터>
            {policies_text}
        </정책데이터>
    """
    else:
        print(f"e-mail 고치는 중... : {feedback}")
        prompt = f"""
            이메일 다시 작성해.
            {policies_text}
            
            <필수 수정 사항>
            {feedback}
            </필수 수정 사항>
            
            <e-mail 작성 시 주의사항>
            "안녕하세요.
            복지 정책 알림 서비스, "복지모니"입니다. [정책 개수]개의 신규 정책이 신설되어 안내드립니다." 로 시작할 것.
            
            정보 전달 위주로 정책 이름, 지원 자격, 지원 내용, 신청 기간 정도를 보기 좋게 적을 것.
            정책이 여러 개일 경우, 구분을 확실히 할 것.
            전달된 데이터에 없는 정보를 지어내지 말 것.
        """

    result = write_email_model.invoke(prompt)

    return {"title": result.title, "content": result.content, "iter_count": count+1}