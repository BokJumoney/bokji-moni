from enum import Enum
from bs4 import BeautifulSoup
import re
# 문서 유형 분류
# 모든 문서를 LLM 구조화하면 비용과 시간이 증가하고 불필요한 데이터가 저장됨
class DocumentType(Enum):

    APPLICATION = "application"
    CONSENT = "consent"
    REPORT = "report"
    CERTIFICATE = "certificate"
    GUIDE = "guide"
    UNKNOWN = "unknown"


def classify_document(text):
    name = extract_document_name(text)

    if name is None:
        return DocumentType.UNKNOWN

    if "신청서" in text:
        return DocumentType.APPLICATION
    if "동의서" in text:
        return DocumentType.CONSENT
    if "신고서" in text:
        return DocumentType.REPORT
    if "확인서" in text:
        return DocumentType.CERTIFICATE
    if "안내" in text:
        return DocumentType.GUIDE

    return DocumentType.UNKNOWN

# 신청서 이름 추출
def extract_document_name(text):

    soup = BeautifulSoup(
        text,
        "html.parser"
    )


    first_table = soup.find("table")

    if not first_table:
        return None


    cells = first_table.find_all(
        ["th", "td"]
    )


    keywords = [
        "이의신청서",
        "동의서",
        "신고서",
        "확인서",
        "계획서",
        "신청서"
    ]


    for cell in cells:

        content = cell.get_text(
            " ",
            strip=True
        )


        # 체크박스 제거
        content = re.sub(
            r"^\[\s*[^\]]*\]\s*",
            "",
            content
        )


        for keyword in keywords:

            if keyword in content:


                index = content.find(keyword)


                title = content[
                    :index + len(keyword)
                ].strip()


                # "신청서" 단독 제외
                if title in keywords:
                    continue


                # 너무 긴 본문 제외
                if len(title) > 80:
                    continue


                return title


    return None