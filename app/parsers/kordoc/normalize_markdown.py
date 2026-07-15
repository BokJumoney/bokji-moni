import re

# 마크다운 전처리 HWPX 변환하면 불필요한 줄바꿈이나 서식 번호 등이 섞여 나옴
def normalize_markdown(markdown: str):

    markdown = markdown.replace("\r\n", "\n")

    markdown = re.sub(
        r"\n{3,}",
        "\n\n",
        markdown
    )

    markdown = re.sub(
        r"[ \t]+",
        " ",
        markdown
    )

    markdown = re.sub(
        r"(서식\s*\d+)",
        r"\n\n\1\n",
        markdown
    )

    markdown = re.sub(
        r"(별지\s*제.*?서식)",
        r"\n\n\1\n",
        markdown
    )

    markdown = re.sub(
        r"(\[\d+\s*면\])",
        r"\n\1\n",
        markdown
    )

    return markdown.strip()