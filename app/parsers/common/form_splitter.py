import re


def split_forms(table):

    """
    하나의 TABLE에서 신청서 단위 추출

    기준:
    - 표 첫 번째 제목 행
    - 서식 번호
    - 신청서/동의서/확인서 등 문서명
    """

    lines = table.splitlines()


    forms = []

    current = []


    for line in lines:


        # 새로운 Form 시작 후보
        if is_form_title(line):

            # 이전 저장
            if current:
                forms.append(
                    "\n".join(current)
                )

                current = []


        current.append(line)


    if current:
        forms.append(
            "\n".join(current)
        )


    return [
        f.strip()
        for f in forms
        if len(f) > 300
    ]



def is_form_title(line):

    text = line.replace("|","").strip()


    # 실제 서식 시작 기준
    patterns = [

        r"^서식\s*\d+",
        r"^\[.*면\]",

    ]


    for pattern in patterns:

        if re.search(pattern, text):
            return True


    return False