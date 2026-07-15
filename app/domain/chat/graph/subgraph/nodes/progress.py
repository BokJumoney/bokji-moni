async def progress(state):

    step = state["current_step"]

    if step == "qualification":
        return {
            "current_step":"document"
        }

    elif step == "document":
        return {
            "current_step":"form"
        }

    elif step == "form":
        return {
           "current_step":"form"
        }

    return {}