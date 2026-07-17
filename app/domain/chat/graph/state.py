from typing import Annotated, List
from typing_extensions import TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

#LangGraph에서 공유하는 상태 객체
# 각 노드는 직접 값을 주고받지 않고 State를 통해 데이터를 공유함
class ChatGraphState(TypedDict, total=False):
    question: str
    generation: str
    documents: List[Document]
    chat_history: List[dict]
    #상태 정보 추가
    conversation_mode:str #현재 대화가 어떤 모드인지 저장
    current_step:str       # 신청 진행 단계
    application_info:dict    # 사용자가 입력한 신청 정보
    route: str
    route_source: str  # active_workflow 또는 llm
    # 인증 계층에서 주입한다. LLM이 사용자/채팅방 식별자를 만들지 않는다.
    user_id: str
    conversation_id: str
    subscription_action: str
    subscription_stage: str
    subscription_guard_message: str
    policy_query: str
    candidate_policy_ids: list[int]
    selected_policy_id: int
    # ToolNode가 AIMessage와 ToolMessage를 같은 요청 안에서 이어 붙일 때 사용한다.
    messages: Annotated[List[BaseMessage], add_messages]
