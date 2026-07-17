"""LangGraph 구조화 추적 로그 테스트."""

import json
import logging
import unittest

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from app.domain.chat.graph.tracing import LangGraphTraceCallback, summarize_state


class _State(TypedDict, total=False):
    question: str
    route: str
    documents: list


class LangGraphTracingTest(unittest.IsolatedAsyncioTestCase):
    def test_state_summary_does_not_log_content(self):
        summary = summarize_state(
            {
                "question": "민감한 사용자 질문",
                "generation": "민감한 모델 답변",
                "route": "vectorstore",
                "documents": [object(), object()],
            }
        )

        self.assertEqual("vectorstore", summary["route"])
        self.assertEqual(2, summary["documents_count"])
        self.assertEqual(len("민감한 사용자 질문"), summary["question_length"])
        self.assertNotIn("민감한 사용자 질문", str(summary))
        self.assertNotIn("민감한 모델 답변", str(summary))

    async def test_callback_logs_node_and_tool_events(self):
        @tool
        def sample_tool(value: int) -> str:
            """테스트 값을 문자열로 반환한다."""
            return str(value)

        builder = StateGraph(_State)

        async def route_node(_: _State) -> dict:
            return {"route": "tool"}

        builder.add_node("route_node", route_node)
        builder.add_node("sample_tools", ToolNode([sample_tool]))
        builder.add_edge(START, "route_node")
        builder.add_edge("route_node", END)
        graph = builder.compile()

        callback = LangGraphTraceCallback("trace-test", "conversation-test")
        with self.assertLogs("uvicorn.error.langgraph.trace", level=logging.INFO) as captured:
            await graph.ainvoke(
                {"question": "로그에 남으면 안 되는 질문"},
                config={"callbacks": [callback]},
            )
            await sample_tool.ainvoke(
                {"value": 7},
                config={"callbacks": [callback]},
            )

        payloads = [
            json.loads(line.split("langgraph_trace ", 1)[1])
            for line in captured.output
            if "langgraph_trace " in line
        ]
        events = {payload["event"] for payload in payloads}
        self.assertTrue({"node_start", "node_end", "tool_start", "tool_end"} <= events)
        self.assertTrue(any(item.get("node") == "route_node" for item in payloads))
        self.assertTrue(any(item.get("tool") == "sample_tool" for item in payloads))
        self.assertNotIn("로그에 남으면 안 되는 질문", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
