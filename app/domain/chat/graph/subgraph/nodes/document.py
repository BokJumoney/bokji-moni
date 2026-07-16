async def document(state):

    return {
        "question": state["question"],
        "current_step":"document"
    }