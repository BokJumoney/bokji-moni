"""
Tool 선택 정확도 평가 스크립트.

아래 EVAL_SET에 정의된 (질문, 기대 tool) 30개 쌍을 실제
information_agent(LLM tool-calling)에 그대로 돌려서
  - 전체 정확도
  - ambiguous(경계 케이스)로 표시되지 않은 항목만의 정확도
  - confusion (기대 tool -> 실제 tool 카운트)
  - 틀린 케이스 상세 목록
을 출력한다.

tool을 실제로 실행하지 않고 information_agent(tool 선택 단계)만
호출하므로 DB/Tavily 비용은 들지 않고 OPENAI_API_KEY 비용만 든다
(질문 30개 * LLM 호출 1회).

실행:
    python -m app.test_agent_eval
"""

import asyncio
from collections import Counter

from app.domain.chat.graph.nodes.information_agent import information_agent

# (id, category, question, expected_tool, ambiguous)
EVAL_SET = [
    (1, "policy", "청년내일저축계좌 지원 대상 알려줘", "policy_search_tool", False),
    (2, "policy", "기초생활수급자 신청 방법이 궁금해요", "policy_search_tool", False),
    (3, "policy", "청년월세지원 신청할 때 필요한 서류가 뭐예요?", "policy_search_tool", False),
    (4, "policy", "국민취업지원제도 자격 요건이 어떻게 되나요?", "policy_search_tool", False),
    (5, "policy", "장애인 활동지원 서비스는 어떤 사람이 받을 수 있어요?", "policy_search_tool", False),
    (6, "policy", "한부모가족 지원금 신청 절차 알려줘", "policy_search_tool", False),
    (7, "policy", "청년구직활동지원금 지원 금액이 얼마예요?", "policy_search_tool", False),
    (8, "policy", "노인장기요양보험 등급 판정 기준이 뭐야?", "policy_search_tool", False),
    (9, "policy", "기초연금 수급 나이 조건 알려줘", "policy_search_tool", False),
    (10, "policy", "청년내일채움공제 가입 조건이 뭔가요?", "policy_search_tool", False),
    (11, "freshness", "2026년 청년 정책 변경된 내용 있어?", "web_search_tool", False),
    (12, "freshness", "올해 새로 생긴 복지 정책 있나요?", "web_search_tool", False),
    (13, "freshness", "청년내일저축계좌 신청 기간이 바뀌었나요?", "web_search_tool", False),
    (14, "freshness", "최근에 기초생활수급 기준 완화됐다는 뉴스 있던데 진짜야?", "web_search_tool", False),
    (15, "freshness", "2026년 하반기 복지 정책 발표 내용 알려줘", "web_search_tool", False),
    (16, "freshness", "이번 달에 새로 시작하는 지원사업 있어?", "web_search_tool", False),
    (17, "freshness", "청년월세지원 예산이 올해 늘었다던데 맞아?", "web_search_tool", False),
    (18, "freshness", "내년부터 바뀌는 복지 제도 있으면 알려줘", "web_search_tool", False),
    (19, "general", "오늘 날씨 알려줘", "general_response_tool", False),
    (20, "general", "파이썬 공부법 알려줘", "general_response_tool", False),
    (21, "general", "맛있는 김치찌개 레시피 알려줘", "general_response_tool", False),
    (22, "general", "제주도 여행 코스 추천해줘", "general_response_tool", False),
    (23, "general", "주식 투자 어떻게 시작해?", "general_response_tool", False),
    (24, "general", "오늘 저녁 뭐 먹을지 추천해줘", "general_response_tool", False),
    (25, "general", "넷플릭스 볼만한 드라마 추천해줘", "general_response_tool", False),
    (26, "ambiguous", "기초생활수급자 조건이 올해 바뀌었나요?", "web_search_tool", True),
    (27, "ambiguous", "청년내일저축계좌 신청하려면 뭐가 필요하고 언제까지 신청 가능해?", "policy_search_tool", True),
    (28, "ambiguous", "복지 정책 중에 요즘 인기있는 거 뭐야?", "web_search_tool", True),
    (29, "ambiguous", "장애인 지원 제도 있으면 알려주고 최근에 확대됐는지도 알려줘", "policy_search_tool", True),
    (30, "ambiguous", "안녕 너는 뭐하는 봇이야?", "general_response_tool", True),
]


async def _predict(question: str) -> str:
    result = await information_agent({"question": question})
    message = result["messages"][0]

    if not message.tool_calls:
        return "(tool_call 없음)"

    return message.tool_calls[0]["name"]


async def main() -> None:
    correct = 0
    correct_non_ambiguous = 0
    total_non_ambiguous = 0
    confusion: Counter = Counter()
    mismatches = []

    for id_, category, question, expected, is_ambiguous in EVAL_SET:
        actual = await _predict(question)
        confusion[(expected, actual)] += 1

        is_correct = actual == expected
        if is_correct:
            correct += 1
        if not is_ambiguous:
            total_non_ambiguous += 1
            if is_correct:
                correct_non_ambiguous += 1

        if not is_correct:
            mismatches.append((id_, question, expected, actual, is_ambiguous))

    total = len(EVAL_SET)
    print(f"전체 정확도: {correct}/{total} ({correct / total:.1%})")
    if total_non_ambiguous:
        print(
            f"명확한 케이스만 정확도: {correct_non_ambiguous}/{total_non_ambiguous} "
            f"({correct_non_ambiguous / total_non_ambiguous:.1%})"
        )

    print("\n=== Confusion (기대 -> 실제) ===")
    for (expected, actual), count in sorted(confusion.items()):
        marker = "" if expected == actual else "  <-- MISMATCH"
        print(f"  {expected:22s} -> {actual:22s} : {count}{marker}")

    if mismatches:
        print("\n=== 틀린 케이스 ===")
        for id_, question, expected, actual, ambiguous in mismatches:
            tag = "[ambiguous] " if ambiguous else ""
            print(f"  {tag}#{id_} {question}")
            print(f"      기대: {expected} / 실제: {actual}")


if __name__ == "__main__":
    asyncio.run(main())