# Parser가 추출한 데이터를 Markdown으로 변환
# Text와 Table의 구조를 최대한 유지하여 LLM이 이해하기 쉽게 생성

def table_to_markdown(table):
    if not table:
        return ""

    column_count = max(len(r) for r in table)
    rows = []

    for row in table:
        row = row + [""] * (column_count - len(row))

        # None 제거만 수행
        row = [
            "" if c is None else str(c)
            for c in row
        ]
        rows.append(row)

    md = []
    md.append("| " + " | ".join(rows[0]) + " |")
    md.append("| " + " | ".join(["---"] * column_count) + " |")

    for row in rows[1:]:
        md.append("| " + " | ".join(row) + " |")

    return "\n".join(md)


def convert_markdown(data):
    # [추가] 1. data가 None이거나 비어있으면 빈 문자열 반환 (TypeError 방지)
    if not data:
        return ""
    
    # [추가] 2. 이미 마크다운 문자열(str) 형태로 들어왔다면 변환 없이 그대로 반환
    if isinstance(data, str):
        return data

    # [추가] 3. 리스트나 딕셔너리가 아닌 다른 타입이 들어왔을 경우 예외 처리
    if not isinstance(data, (list, tuple)):
        return str(data)

    md = []

    for item in data:
        # [추가] item이 딕셔너리가 아니거나 "type" 키가 없는 경우를 대비한 안전장치
        if not isinstance(item, dict) or "type" not in item:
            continue

        if item["type"] == "text":
            text = item.get("content", "")
            if text.strip():
                md.append("")
                md.append("[TEXT_BLOCK]")
                md.append(text)
                md.append("[/TEXT_BLOCK]")
                md.append("")

        elif item["type"] == "table":
            md.append("")
            md.append("[TABLE_BLOCK]")
            md.append(table_to_markdown(item.get("content", [])))
            md.append("[TABLE_BLOCK]")
            md.append("")

    return "\n".join(md)