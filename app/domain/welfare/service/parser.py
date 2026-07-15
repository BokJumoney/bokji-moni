import pandas as pd

# 청크
CHUNK_FIELD_MAP = {
    "기본정보": ["서비스ID", "서비스명", "소관부처명", "서비스요약", "기준연도"],
    "대상": ["생애주기", "관심주제", "가구유형", "대상자상세내용", "선정기준내용"],
    "지원내용": ["급여서비스내용", "지원주기", "제공유형"],
    "신청": ["처리절차", "신청방법", "필요서류"],
    "문의근거": ["문의처", "문의처목록", "홈페이지목록", "근거법령목록"],
}

# 임베딩 할 용어로 변경
FIELD_LABEL_MAP = {
    "서비스ID" : "정책ID",
    "서비스명": "정책명",
    "소관부처명": "담당부처",
    "서비스요약": "정책요약",
    "기준연도": "기준연도",
    "생애주기": "생애주기",
    "관심주제": "관심주제",
    "가구유형": "가구유형",
    "대상자상세내용": "지원대상 상세",
    "선정기준내용": "선정기준",
    "급여서비스내용": "지원내용",
    "지원주기": "지원주기",
    "제공유형": "제공유형",
    "신청방법" : "신청방",
    "필요서류" : "필요서류",
    "처리절차": "처리절차",
    "문의처": "문의처",
    "문의처목록": "문의처 목록",
    "홈페이지목록": "관련 홈페이지",
    "근거법령목록": "근거법령",
}


def is_empty(value) -> bool:
    """NaN, 빈 문자열, 공백만 있는 값 판별"""
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def build_chunk_content(service_name: str, chunk_type: str, row: pd.Series, fields: list[str]) -> str | None:
    """헤더 + 라벨:값 형태로 청크 텍스트 생성. 유효 필드가 하나도 없으면 None."""
    parts = []
    for field in fields:
        value = row.get(field)
        if is_empty(value):
            continue
        label = FIELD_LABEL_MAP.get(field, field)
        # 개행은 공백으로 바꿈
        clean_value = str(value).replace("\n", " ").strip()
        parts.append(f"{label}: {clean_value}")

    if not parts:
        return None

    header = f"[{service_name}] {chunk_type}"
    return header + " - " + " / ".join(parts)


def chunk_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    policies = []
    for _, row in df.iterrows():
        service_id = row["서비스ID"]
        service_name = row["서비스명"]

        for chunk_type, fields in CHUNK_FIELD_MAP.items():
            content = build_chunk_content(service_name, chunk_type, row, fields)
            if content is None:
                continue  # 이 청크에 해당하는 필드가 전부 비어있으면 row 자체를 만들지 않음

            policies.append({
                "service_id" : service_id,
                "service_name" : service_name,
                "chunk_type" : chunk_type,
                "content": content,
            })

    return pd.DataFrame(policies)


if __name__ == "__main__":
    # df = pd.read_csv("detail_policy_all.csv")
    df = pd.read_csv("testdata.csv")
    chunk_df = chunk_dataframe(df)

    print(f"원본 서비스 수: {len(df)}")
    print(f"생성된 청크 수: {len(chunk_df)}")
    print(chunk_df["chunk_type"].value_counts())
    print()
    print(chunk_df.head(5).to_string())

    chunk_df.to_csv("welfare_chunks5.csv", index=False)
