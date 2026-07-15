from app.domain.chat.graph.state import ChatGraphState
from app.domain.chat.graph.router.intent_router import route_question


async def intent_router(state):

    print("------ INTENT ROUTER ------")

    route = await route_question(state)

    print("ROUTE:", route)

    return {
        "route": route
    }