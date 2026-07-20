from typing import List
from typing import TypedDict

class NotiState(TypedDict):
    # 정책 정보
    new_policies: List[dict]

    #e-mail 발송 대상 유저 정보
    user_names: List[str]
    user_emails: List[str]

    #생성된 e-mail 제목, 내용
    title: str
    content: str

    #e-mail 검사 결과
    confirmed: bool #통과 여부
    feedback: str #반려 시 피드백
    iter_count: int #반복 횟수(반려 횟수)
