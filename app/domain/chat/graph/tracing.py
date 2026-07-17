"""LangGraph 실행 경로를 관찰하기 위한 구조화 로그 콜백."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler

# uvicorn 기본 핸들러를 상속해 별도 logging 설정 없이도 INFO 로그가 보이게 한다.
logger = logging.getLogger("uvicorn.error.langgraph.trace")

_STATE_VALUE_KEYS = (
    "route",
    "route_source",
    "conversation_mode",
    "current_step",
    "subscription_action",
    "subscription_stage",
    "selected_policy_id",
)
_STATE_LIST_KEYS = (
    "documents",
    "chat_history",
    "messages",
    "candidate_policy_ids",
)


def summarize_state(state: Any) -> dict[str, Any]:
    """프롬프트 원문을 제외하고 디버깅에 필요한 상태만 요약한다."""
    if not isinstance(state, Mapping):
        return {"value_type": type(state).__name__}

    summary: dict[str, Any] = {"keys": sorted(str(key) for key in state)}
    for key in _STATE_VALUE_KEYS:
        value = state.get(key)
        if value is not None:
            summary[key] = value
    for key in _STATE_LIST_KEYS:
        value = state.get(key)
        if isinstance(value, (list, tuple)):
            summary[f"{key}_count"] = len(value)

    question = state.get("question")
    if isinstance(question, str):
        summary["question_length"] = len(question)
    generation = state.get("generation")
    if isinstance(generation, str):
        summary["generation_length"] = len(generation)
    return summary


class LangGraphTraceCallback(AsyncCallbackHandler):
    """노드, 상태 변화, 툴 호출을 요청 단위 trace_id로 연결한다."""

    def __init__(self, trace_id: str, conversation_id: str) -> None:
        self.trace_id = trace_id
        self.conversation_id = conversation_id
        self._node_runs: dict[UUID, tuple[str, float]] = {}
        self._tool_runs: dict[UUID, tuple[str, float]] = {}

    def _log(self, event: str, **fields: Any) -> None:
        payload = {
            "event": event,
            "trace_id": self.trace_id,
            "conversation_id": self.conversation_id,
            **fields,
        }
        logger.info("langgraph_trace %s", json.dumps(payload, ensure_ascii=False, default=str))

    async def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        node = (metadata or {}).get("langgraph_node")
        # 노드 안에서 실행되는 프롬프트/LLM 체인에도 node 메타데이터가 전파된다.
        # 실제 Pregel 노드 실행에만 붙는 graph:step 태그로 중복 로그를 막는다.
        if not node or not any(tag.startswith("graph:step:") for tag in tags or []):
            return
        node_name = str(node)
        self._node_runs[run_id] = (node_name, time.perf_counter())
        self._log(
            "node_start",
            node=node_name,
            graph_step=(metadata or {}).get("langgraph_step"),
            state=summarize_state(inputs),
        )

    async def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run = self._node_runs.pop(run_id, None)
        if run is None:
            return
        node, started_at = run
        self._log(
            "node_end",
            node=node,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            state_update=summarize_state(outputs),
        )

    async def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run = self._node_runs.pop(run_id, None)
        if run is None:
            return
        node, started_at = run
        self._log(
            "node_error",
            node=node,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            error_type=type(error).__name__,
            error_message=str(error)[:300],
        )

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = str(serialized.get("name") or "unknown_tool")
        self._tool_runs[run_id] = (tool_name, time.perf_counter())
        self._log(
            "tool_start",
            tool=tool_name,
            input_keys=sorted(str(key) for key in inputs) if inputs else [],
        )

    async def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run = self._tool_runs.pop(run_id, None)
        if run is None:
            return
        tool_name, started_at = run
        artifact = getattr(output, "artifact", None)
        self._log(
            "tool_end",
            tool=tool_name,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            output_type=type(output).__name__,
            artifact_kind=artifact.get("kind") if isinstance(artifact, dict) else None,
        )

    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run = self._tool_runs.pop(run_id, None)
        if run is None:
            return
        tool_name, started_at = run
        self._log(
            "tool_error",
            tool=tool_name,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            error_type=type(error).__name__,
            error_message=str(error)[:300],
        )
