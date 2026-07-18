# 신규 정책 상세 데이터를 받아서 전처리
import xmltodict
import pandas as pd

# 단일 태그
TAG_COLUMN_MAP = {
    "servId": "서비스ID",
    "servNm": "서비스명",
    "jurMnofNm": "소관부처명",
    "tgtrDtlCn": "대상자상세내용",
    "slctCritCn": "선정기준내용",
    "alwServCn": "급여서비스내용",
    "crtrYr": "기준연도",
    "rprsCtadr": "문의처",
    "wlfareInfoOutlCn": "서비스요약",
    "sprtCycNm": "지원주기",
    "srvPvsnNm": "제공유형",
    "trgterIndvdlArray": "가구유형",
    "lifeArray": "생애주기",
    "intrsThemaArray": "관심주제",
    "joinPrcs": "신청방법",
    "srvDocs": "필요서류",
}

# 반복 태그(list) -> 컬럼명
LIST_COLUMN_MAP = {
    "inqplCtadrList": "문의처목록",
    "inqplHmpgReldList": "홈페이지목록",
    "baslawList": "근거법령목록",
}

def parse_to_list(data):
    dict_data = xmltodict.parse(data) # xml -> dict로
    serv_list = dict_data["wantedList"]["servList"] # 겉 껍질 벗기기
    if isinstance(serv_list, dict):
        serv_list = [serv_list]
    serv_ids = [serv["servId"] for serv in serv_list] # servId만 추출

    return serv_ids

def _as_list(value):
    """xmltodict은 태그가 1개면 dict, 여러 개면 list로 준다. 항상 list로 통일."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]

def _clean(text):
    """문자열이면 양쪽 공백 제거, 아니면 빈 문자열."""
    return text.strip() if isinstance(text, str) else ""

def _get_list_text(detail, list_tag):
    """목록 태그를 '이름: 링크' 형태로 개행 연결."""
    items = []
    for elem in _as_list(detail.get(list_tag)):
        name = _clean(elem.get("servSeDetailNm"))
        link = _clean(elem.get("servSeDetailLink"))
        if name and link:
            items.append(f"{name}: {link}")
        elif name:
            items.append(name)
        elif link:
            items.append(link)
    return "\n".join(items)

def _get_application_steps(detail):
    """신청절차(applmetList)를 번호 붙여 개행 연결."""
    steps = []
    for idx, applmet in enumerate(_as_list(detail.get("applmetList")), start=1):
        content = _clean(applmet.get("servSeDetailLink"))
        if content:
            steps.append(f"{idx}. {content}")
    return "\n".join(steps)

def _parse_one(detail):
    """wantedDtl dict 하나 -> row dict."""
    row = {}
    for tag, column_name in TAG_COLUMN_MAP.items():
        row[column_name] = _clean(detail.get(tag))

    row["처리절차"] = _get_application_steps(detail)

    for list_tag, column_name in LIST_COLUMN_MAP.items():
        row[column_name] = _get_list_text(detail, list_tag)

    return row

def convert_to_kor(data):
    rows = []
    for item in data:
        detail = item.get(
            "wantedDtl", item
        )  # wantedDtl 래핑이 없으면 item 자체 사용
        if not detail:
            continue
        # 성공 응답만 처리
        if detail.get("resultCode") not in (None, "0"):
            print(
                f"응답 실패 skip: {detail.get('servId')} / {detail.get('resultMessage')}"
            )
            continue
        rows.append(_parse_one(detail))

    return pd.DataFrame(rows)
