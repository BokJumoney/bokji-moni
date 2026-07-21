from sqlmodel import Session

from app.domain.notification.service.noti_service import send_new_policy_email
from app.domain.welfare.repository import WelfareRepository
from app.domain.welfare.service import parser, chunker, client
from app.domain.welfare.service.rag_update.ingest_new_policy import ingest_to_pgvector, delete_from_pgvector, init_sqlmodel_table
from app.infrastructure.vectorstore.setup_vectorstore import rebuild_bm25

async def insert_new_policy(new_policy_list) -> list:
    new_policy_details = await client.get_new_policy_details(new_policy_list)# detail api 호출 후 xml -> dict로 파싱한 정책 상세 정보 리스트
    df = parser.convert_to_kor(new_policy_details)#한글 df로 변환
    wp_list = init_sqlmodel_table(df) # RDB에 적재.
    chunked_df = chunker.chunk_dataframe(df)  # 청킹된 df 반환
    ingest_to_pgvector(chunked_df) # df -> document -> PGVector 적재

    return wp_list

def delete_expired_policy(repo: WelfareRepository, expired_policy_list: list):
    """폐지 정책을 RDB(WelfarePolicy)와 PGVector에서 모두 삭제."""
    if not expired_policy_list:
        return
    repo.delete_old_policy(expired_policy_list)
    delete_from_pgvector(expired_policy_list)

async def compare_datas(repo:WelfareRepository, api_serv_ids_list: list) -> list: #
    wp_list = []
    #db에 저장된 데이터에서 serv_id만 가져옴
    db_serv_ids_list = repo.get_service_id()
    #가져온 serv_id를 api에서 가져온 데이터와 비교
    expired_policy_list = []
    for db_serv_id in db_serv_ids_list:
        if db_serv_id not in api_serv_ids_list:
            expired_policy_list.append(db_serv_id)

    new_policy_list = []
    for api_serv_id in api_serv_ids_list:
        if api_serv_id not in db_serv_ids_list:
            new_policy_list.append(api_serv_id)

    if not new_policy_list and not expired_policy_list:
        print("신규/폐지 정책 없음 - 업데이트 종료")
        return []

    #폐지 정책 삭제 (RDB + PGVector)
    if expired_policy_list:
        delete_expired_policy(repo, expired_policy_list)
        print("[폐지 정책 삭제 완료]")

    #신규 정책 추가
    if new_policy_list:
        wp_list = await insert_new_policy(new_policy_list)
        print("[신규 정책 추가 완료]")

    # 폐지/신규 반영이 모두 끝난 뒤, DB 전체 청크 기준으로 BM25 재빌드
    rebuild_bm25()
    print("[BM25 리빌드 완료]\n")

    return wp_list

async def api_call_rag_update(session:Session) -> list:
    welfare_repository = WelfareRepository(session)
    api_data = await client.welfare_list_api_call() #정책 list xml로 받앙옴
    serv_id_list = parser.parse_to_list(api_data) #servId 리스트 받음
    wp_list = await compare_datas(welfare_repository, serv_id_list)
    #신규 정책 알림 이메일 전송 그래프 호출
    if wp_list:
        try:
            send_result = await send_new_policy_email(wp_list)
        except Exception as e:
            print(e, "이메일 발송에 실패했습니다.")

    return wp_list
