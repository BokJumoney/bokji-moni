from bs4 import BeautifulSoup

# HTML Table 구조 추출
# LLM에게 마크다운 전체를 보내면 너무 많은 정보가 들어가고 표 구조 이해가 어려웁
# 그래서 필요한 정보를 json형태로 변환
FIELD_TYPES = {
    "주민등록번호": "resident_number",
    "전화번호": "phone",
    "휴대전화": "mobile",
    "전자우편": "email",
    "주소": "address",
    "금액": "money",
    "연도": "year",
    "기간": "period"
}


def infer_type(text):

    for key, value in FIELD_TYPES.items():
        if key in text:
            return value

    return "text"


def parse_table(form_html):

    soup = BeautifulSoup(form_html, "html.parser")

    table = soup.find("table")

    if not table:
        return None


    result = {
        "table": []
    }


    rows = table.find_all("tr")


    for r_idx, row in enumerate(rows):

        row_data = []

        cells = row.find_all(
            ["td","th"]
        )


        for c_idx, cell in enumerate(cells):

            text = cell.get_text(
                " ",
                strip=True
            )


            if not text:
                continue


            row_data.append(
                {
                    "row":r_idx,
                    "col":c_idx,
                    "text":text,
                    "rowspan":int(
                        cell.get(
                            "rowspan",
                            1
                        )
                    ),
                    "colspan":int(
                        cell.get(
                            "colspan",
                            1
                        )
                    )
                }
            )


        if row_data:
            result["table"].append(
                row_data
            )


    return result