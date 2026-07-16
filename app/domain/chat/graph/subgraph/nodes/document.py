async def document(state):

    print("document 분기 확인")

    return {
        "question": state["question"],
        "current_step":"document"
    }