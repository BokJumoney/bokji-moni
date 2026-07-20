def policy_not_found_in_state(_state=None):
    return {"error_message": "어떤 정책에 대한 신청서를 찾으시나요? 정책명을 알려주시면 해당 정책에 대한 신청서를 찾아드릴 수 있습니다."}

def credential_policy_not_found(_state=None):
    return {"error_message": "어떤 정책의 신청 자격을 확인할까요? 정책명을 알려주세요."}

def policy_id_not_found_in_state(_state=None):
    return {"error_message": "정책 ID를 찾을 수 없습니다. 정책명을 더 자세히 알려주시면 해당 정책에 대한 신청서를 찾아드릴 수 있습니다."}

def policy_forms_not_found_in_state(_state=None):
    return {"error_message": "아직 신청서가 준비되지 않아 제공해드릴 수 없습니다."}

def policy_qualification_not_found(_state=None):
    return {"error_message": "자격 조건 데이터가 없어 자격증명을 수행할 수 없습니다."}

def user_background_not_found(_state=None):
    return {"error_message": "등록된 사용자 상세 정보가 없어 신청 자격을 확인할 수 없습니다. 먼저 마이페이지에서 복지 정보를 입력해 주세요."}
