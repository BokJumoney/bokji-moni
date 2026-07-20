def format_policy(policies: list[dict]) -> str:
    blocks = []
    for policy in policies:
        lines = [f"### {policy['service_name']} (ID: {policy['service_id']})"]
        for key, value in policy.items():
            if key in ("service_id", "service_name"):
                continue  # 헤더에 이미 있음
            if value:  # 빈 문자열 필드는 생략
                lines.append(f"[{key}]\n{value}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)