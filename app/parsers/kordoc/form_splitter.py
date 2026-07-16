from bs4 import BeautifulSoup


FORM_KEYWORDS = [
    "신청서",
    "동의서",
    "확인서",
    "통지서",
    "신고서",
    "계획서"
]


def has_form_title(text):

    return any(
        keyword in text
        for keyword in FORM_KEYWORDS
    )


def split_forms(markdown):

    soup = BeautifulSoup(
        markdown,
        "html.parser"
    )

    forms = []

    current_form = []

    tables = []

    for table in soup.find_all("table"):

        # 중첩 table 제외
        if table.find_parent("table"):
            continue

        tables.append(table)



    for table in tables:

        text = table.get_text(
            "\n",
            strip=True
        )


        # 새로운 문서 제목 발견
        if has_form_title(text):

            if current_form:
                forms.append(
                    "\n".join(current_form)
                )

                current_form = []


        current_form.append(
            str(table)
        )


    if current_form:
        forms.append(
            "\n".join(current_form)
        )


    return forms