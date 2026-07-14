from app.domain.chat.graph.state import ChatGraphState
async def application_entry(state: ChatGraphState):

    return {
        "conversation_mode": "application",
        "current_step": "qualification"
    }