from app.rag.ingest_form import search_document

questions = [
    # "직업 및 근무 정보에는 무엇을 작성해야 하나요?",
    # "신청서 작성할 때 직장 관련해서 어떤 정보를 적나요?",
    "자산형성지원사업 참여 신청서에는 어떤 내용이 있나요?",

    # "자산형성지원사업 참여 신청서의 가입자 정보에는 무엇을 작성하나요?",
    # "자산형성지원사업 참여 신청서 작성할 때 신청자 정보에는 어떤 내용을 입력하나요?",
    # "희망저축계좌 신청서의 가입정보 영역에는 무엇을 작성해야 하나요?",
    # "희망저축계좌 신청 시 선택해야 하는 항목이 있나요?",
    # "근무형태는 어떤 것을 선택할 수 있나요?",
    # "적립 및 기타정보에는 어떤 내용을 작성해야 하나요?",
    # "이전에 참여한 자산형성사업 여부는 어디에 작성하나요?",
    # "금융정보 제공 동의서는 어떤 내용을 작성해야 하나요?"
]

for question in questions:

    print("=" * 60)
    print("질문:")
    print(question)

    results = search_document(question)

    if not results:
        print("검색 결과가 없습니다.")
        continue

    for result in results:

        metadata = result["metadata"]
        content = result["content"]

        print("=" * 40)

        print("FORM:")
        print(metadata.get("form_name", ""))

        print("SECTION:")
        print(metadata.get("section", ""))

        print("CONTENT:")
        print(content)

        print()