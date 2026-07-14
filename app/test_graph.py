import asyncio

from app.domain.chat.graph.chat_graph import graph


async def test():

    result = await graph.ainvoke(
        {
            "question": "실업자를 위한 지원 정책이 있나요?",
            "chat_history": [],
            "documents": [],
            "generation": "",
            "conversation_mode": "",
            "current_step": "",
            "application_info": {},
            "route": ""
        }
    )

    print("====================")
    print(result)
    print("====================")

    print("답변:")
    print(result.get("generation"))


if __name__ == "__main__":
    asyncio.run(test())