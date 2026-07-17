"""
intent_router 노드.

여기서 딱 한 번 LLM을 불러서 사용자 질문의 의도를 판단하고,
그 결과를 state["intent"]에 저장한다 (dict를 반환해야 하는 LangGraph 노드 규칙).

실제로 "어디로 갈지"는 이 노드가 아니라, 바로 다음에 실행되는
conditional edge 함수(router/intent_router.py의 route_by_intent)가
state["intent"] 값을 읽어서 결정한다. route_by_intent는 LLM을
또 부르지 않고, 이미 여기서 저장해둔 값만 읽는다.
"""
from app.domain.chat.graph.state2 import ChatState
from app.domain.chat.graph.router.intent_router import question_router


async def intent_router(state: ChatState) -> dict:
    print("------ INTENT ROUTER ------")
    question = state["question"]
    route = await question_router.ainvoke({"question": question})
    print(f"ROUTE: {route.datasource}")
    return {"intent": route.datasource}
