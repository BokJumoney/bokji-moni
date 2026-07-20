from app.domain.chat.graph.agent.states.credential_state import CredentialState
from app.infrastructure.llm.gpt import get_llm_gpt
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from app.domain.chat.graph.agent.states.search_form_state import SearchFormState

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
        당신은 사용자와의 대화 내역을 보고 사용자가 언급한 복지 정책을 추출하는 역할을 수행합니다.
        복지 정책명 하나만을 추출하세요

        규칙:
        1. 가장 최근 사용자 메시지를 우선해서 판단합니다.
        2. "그 정책", "아까 말한 지원금", "그거"처럼 대명사로 표현했다면
          이전 대화에서 가장 가까운 정책명을 찾아 반환합니다.
        3. 정책명은 대화에 등장한 표현을 최대한 그대로 반환합니다.
        4. 새로운 정책명을 임의로 만들어내지 않습니다.
        5. 복수의 정책이 언급되었으면 가장 최근에 언급된 정책 하나를 반환합니다.
        6. 어떤 정책인지 특정할 수 없으면 mentioned_policy를 None으로 반환합니다.
        7. 일반 단어인 "복지 정책", "지원금", "정책"만 등장했다면
          구체적인 정책명으로 판단하지 않습니다.

          {messages}
        """
    )
])

class ExtractLatestPolicy(BaseModel):
    mentioned_policy: str | None = Field(
        default=None, 
        description="state에서 가장 최근에 언급된 정책을 추출한 결과"
    )

def _format_messages(messages: list) -> str:
    lines: list[str] = []
    for message in messages:
        if isinstance(message, BaseMessage):
            role = message.type
            content = message.content
        elif isinstance(message, dict):
            role = str(message.get("role", "unknown"))
            content = message.get("content", "")
        else:
            role = "unknown"
            content = str(message)
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def extract_latest_policy(state: SearchFormState | CredentialState) -> dict:
    """
    state에서 가장 최근에 언급된 정책을 추출하는 함수
    """
    messages = _format_messages(state.get("messages", []))

    _llm = get_llm_gpt()
    _structured_llm = _llm.with_structured_output(ExtractLatestPolicy)

    response = await _structured_llm.ainvoke(PROMPT.format(messages=messages))

    return {"policy_name": response.mentioned_policy}
