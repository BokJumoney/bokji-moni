from enum import Enum
from typing import List
from typing import TypedDict

class EmailPromptRoute(str, Enum):
    NEW_POLICY = "new_policy"
    APPLY_START = "apply_start"
    APPLY_END = "apply_end"

class NotiState(TypedDict):
    # 정책 정보
    new_policies: List[dict]

    noti_type: EmailPromptRoute # 신규(new) / 시작 전(start) / 마감 전(end) 기본값 = 신규

    #e-mail 발송 대상 유저 정보
    user_names: List[str]
    user_emails: List[str]

    #웹 검색 결과
    web_search_data: str

    #생성된 e-mail 제목, 내용
    title: str
    content: str

    #e-mail 검사 결과
    confirmed: bool #통과 여부
    feedback: str #반려 시 피드백
    iter_count: int #반복 횟수(반려 횟수)
