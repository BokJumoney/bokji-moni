# 이메일 작성 LLM 노드
from pydantic import BaseModel, Field

from app.domain.chat.graph.tools.web_search import web_search_tool
from app.domain.notification.graph.format_policy import format_policy
from app.domain.notification.graph.email_prompt import (
    COMMON_PROMPT,
    REWRITE_PROMPT,
    PROMPT_MAP, WRITE_PROMPT,
)
from app.domain.notification.graph.state import NotiState, EmailPromptRoute
from langchain_core.messages import HumanMessage
from app.infrastructure.llm.gpt import get_llm_gpt

model = get_llm_gpt("gpt-4o-mini", 0, reasoning_effort=None, use_responses_api=True)


class WriteEmailForm(BaseModel):
    title: str = Field(description="이메일의 제목")
    content: str = Field(description="이메일의 본문")


model_with_tools = model.bind_tools([WriteEmailForm, web_search_tool])


async def write_email(state: NotiState):
    policies = state["new_policies"]
    noti_type = state.get("noti_type", EmailPromptRoute.NEW_POLICY)
    feedback = state.get("feedback")
    count = state.get("iter_count", 0)
    last_web_search_datas = state.get("web_search_data", "")

    policies_text = format_policy(policies)

    print(f"e-mail 작성 중...{count + 1}회 시도")

    if not feedback:
        prompt = WRITE_PROMPT.format(
            common_prompt=COMMON_PROMPT,
            policy_prompt=PROMPT_MAP[noti_type],
            policies_text=policies_text,
        )
    else:
        print(f"e-mail 고치는 중... : {feedback}")
        prompt = REWRITE_PROMPT.format(
            policies_text=policies_text,
            feedback=feedback,
            last_web_search_datas=last_web_search_datas,
            common_prompt=COMMON_PROMPT,
            policy_prompt=PROMPT_MAP[noti_type],
        )

    messages = [HumanMessage(prompt)]
    web_search_datas = []
    email_form = None

    for _ in range(5):
        response = await model_with_tools.ainvoke(messages)
        # 툴 콜링이 없을 때
        if not response.tool_calls: # 그냥 AI 메시지, Human 메시지만 넣음
            messages.append(response)
            messages.append(
                HumanMessage("최종 이메일은 반드시 WriteEmailForm 도구로 제출해.")
            )
            continue
        # 툴 콜링이 있을 때
        messages.append(response)
        for call in response.tool_calls:
            # WriteEmailForm 툴을 호출했다면,
            if call["name"] == "WriteEmailForm":
                email_form = WriteEmailForm(**call["args"]) #title, content 형태의 데이터 리턴
            # WriteEmailForm이 아니면 web_search_tool 요청
            else:
                print(f"웹 검색: {call['args']}")
                tool_msg = await web_search_tool.ainvoke(call)
                web_search_datas.append(str(tool_msg.content))
                messages.append(tool_msg)
        if email_form:
            break

    if email_form is None:  # 5바퀴에도 제출 안 하면 오류.
        raise RuntimeError("WriteEmailForm 제출 안됌. 이메일 작성 중단.")

    mixed_web_search_datas = "\n\n".join(x for x in [last_web_search_datas, *web_search_datas] if x)

    return {"title": email_form.title, "content": email_form.content, "iter_count": count + 1, "web_search_data": mixed_web_search_datas}
