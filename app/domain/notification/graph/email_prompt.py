from app.domain.notification.graph.state import EmailPromptRoute

COMMON_PROMPT = f"""
    우리 서비스 이용자들에게 보낼 e-mail 제목과 본문 작성해줘. 제목, 본문에 서비스ID는 넣지마.
    Markdown쓰지말고 일반 텍스트로 작성해줘.
    적절한 들여쓰기도 해줘. 기호는 사용해도 상관없지만 과하면 안돼.
    본문에서 제목처럼 쓰이는 정책명은 []로 감싸서 강조해줘.
    이메일 작성에 필요한 정보가 부족하면 web_search_tool로 검색해서 보강해.
    특히 신청기간에 대한 정보가 없으면 web_search_tool을 적극적으로 사용해.
    이미 알고있는 정보에 대해서는 검색하지마.
    정보 전달 위주로 정책 이름, 지원 자격, 지원 내용, 신청 기간 등을 보기 좋게 적어줘.
    정책 데이터에 없는 내용은 절대로 지어내지 마.
    최종 결과는 반드시 WriteEmailForm으로 제출해.
"""

NEW_POLICIES_PROMPT = f"""
        제목은
        "[복지모니 신규 정책 알림]" 뒤에 이어서 간단하게 작성해줘.
        본문은
        "안녕하세요.
        복지 정책 알림 서비스, "복지모니"입니다. [정책 개수]개의 신규 정책이 신설되어 안내드립니다." 로 시작해줘.
        정책이 여러 개 일 수 있으니, 영역을 구분해서 작성해야해.
"""

INDV_POLICY_START_PROMPT = """
        제목은
        "[복지모니 정책 알림 - 정책명:"정책명"]" 뒤에 이어서 간단하게 작성해줘.
        본문은
        "안녕하세요.
        복지 정책 알림 서비스, "복지모니"입니다. 알림 구독하신 {정책명} 정책 신청일이 3일 앞으로 다가와 안내드립니다." 로 시작해줘.
"""

INDV_POLICY_END_PROMPT = f"""
        제목은
        "[복지모니 정책 알림 - 정책명:"정책명"]" 뒤에 이어서 간단하게 작성해줘.
        본문은
        "안녕하세요.
        복지 정책 알림 서비스, "복지모니"입니다. 알림 구독하신 [정책명] 정책 신청 마감일이 3일 밖에 남지 않아 다시 안내드립니다." 로 시작해줘.
"""

INDV_POLICY_REMIND_PROMPT = """
        제목은
        "[복지모니 정책 알림 - 정책명:"정책명"]" 뒤에 이어서 간단하게 작성해줘.
        본문은
        "안녕하세요.
        복지 정책 알림 서비스, "복지모니"입니다. 알림 구독하신 [정책명] 정책은 잊지 않고 신청하셨나요?" 로 시작해줘.
        뒤로는 복지 정책에 대한 매우 간단한 정보와 함께 꼭 신청하라는 신청 유도 멘트도 넣어줘.
"""

WRITE_PROMPT = """
        {common_prompt}
        {policy_prompt}
        <정책 데이터>
            {policies_text}
        </정책데이터>
"""

REWRITE_PROMPT = """
        이메일 다시 작성해.
        {policies_text}
        
        <필수 수정 사항>
            {feedback}
        </필수 수정 사항>
        
        <e-mail 작성 시 주의사항>
            {common_prompt}
            {policy_prompt}
        </e-mail 작성 시 주의사항>
        
        <웹 검색 결과>
            {last_web_search_datas}
        </웹 검색 결과>
"""

REVIEW_PROMPT = """
        작성된 이메일 내용을 보고 이메일 작성 프롬프트를 잘 지켰는지 판단해서 그대로 사용할 지 고칠 지 판단하고, 어떻게 수정해야 하는지 자세하게 수정사항을 알려줘.
        웹 검색 결과에서 참고해야 할 데이터도 잘 적용했는지 판단해줘.
        <정책 데이터>
            {policies_text}
        </정책 데이터>

        <작성된 이메일 내용>
            [제목]
            {title}
            [본문]
            {content}
        </작성된 이메일 내용>

        <웹 검색 결과>
            {web_search_data}
        </웹 검색 결과>

        <이메일 작성 프롬프트>
            {common_prompt}
            {policy_prompt}
        </이메일 작성 프롬프트>
"""

PROMPT_MAP = {
    EmailPromptRoute.NEW_POLICY: NEW_POLICIES_PROMPT,
    EmailPromptRoute.APPLY_START: INDV_POLICY_START_PROMPT,
    EmailPromptRoute.APPLY_END: INDV_POLICY_END_PROMPT,
    EmailPromptRoute.REMIND_POLICY: INDV_POLICY_REMIND_PROMPT,
}