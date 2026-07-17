# 이메일 작성 LLM 노드
from app.domain.notification.graph.format_policy import format_policy
from app.domain.notification.graph.state import NotiState
from app.infrastructure.llm.gpt import get_llm_gpt

model = get_llm_gpt("gpt-5.6-luna", 0)

def write_email(state: NotiState):
    policies = state["new_policies"]
    feedback = state.get("feedback")
    count = state.get("iter_count", 0)

    policies_text = format_policy(policies)

    print(f"e-mail 작성 중...{count + 1}회 시도")

    if not feedback:
        prompt = f"""우리 서비스 이용자들에게 보낼 e-mail 본문 작성해줘.
        {policies_text}
        정책이 여러 개 일 수 있는데 영역을 구분해서 작성해야해.
        정보 전달 위주로 정책 이름, 지원 자격, 지원 내용, 신청 기간 정도만 보기 좋게 적어줘.
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
            정보 전달 위주로 정책 이름, 지원 자격, 지원 내용, 신청 기간 정도만 보기 좋게 적을 것.
            정책이 여러 개일 경우, 구분을 확실히 할 것.
        """

    msg = model.invoke(prompt)

    return {"content": msg.content, "iter_count": count+1}