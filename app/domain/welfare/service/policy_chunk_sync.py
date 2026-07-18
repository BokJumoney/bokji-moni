# """정책 청크 문서를 WelfarePolicy 테이블과 안전하게 동기화한다."""
#
# from collections import defaultdict
#
# from langchain_core.documents import Document
# from sqlmodel import Session, select
#
# from app.common.timezone import now_kst
# from app.domain.welfare.entity.models import WelfarePolicy
# # from app.domain.welfare.service.deadline_extractor import (
# #     extract_application_deadline,
# # )
#
#
# def upsert_policy_chunks(session: Session, chunks: list[Document]) -> int:
#     """청크를 ``(service_id, chunk_type)`` 기준으로 추가하거나 갱신한다.
#
#     기존 행을 모두 삭제하지 않는 이유는 PolicySubscription이 정책 행 ID를
#     외래키로 참조하기 때문이다. 같은 청크는 제자리에서 갱신해 구독 연결을
#     유지하고, 새 청크만 추가한다.
#     """
#     grouped: dict[str, list[Document]] = defaultdict(list)
#     for chunk in chunks:
#         grouped[str(chunk.metadata["service_id"])].append(chunk)
#
#     synced = 0
#     now = now_kst()
#     for service_id, policy_chunks in grouped.items():
#         combined = "\n".join(chunk.page_content for chunk in policy_chunks)
#         extracted_deadline = extract_application_deadline(combined, now.year)
#
#         for chunk in policy_chunks:
#             metadata = chunk.metadata
#             chunk_type = str(metadata["chunk_type"])
#             policy = session.exec(
#                 select(WelfarePolicy)
#                 .where(
#                     WelfarePolicy.service_id == service_id,
#                     WelfarePolicy.chunk_type == chunk_type,
#                 )
#                 .order_by(WelfarePolicy.id)
#             ).first()
#
#             if policy is None:
#                 policy = WelfarePolicy(
#                     service_id=service_id,
#                     service_name=str(metadata["service_name"]),
#                     chunk_type=chunk_type,
#                     page_content=chunk.page_content,
#                     application_deadline=extracted_deadline,
#                 )
#             else:
#                 policy.service_name = str(metadata["service_name"])
#                 policy.page_content = chunk.page_content
#                 # 관리자가 입력했거나 검증된 기존 마감일은 덮어쓰지 않는다.
#                 if policy.application_deadline is None:
#                     policy.application_deadline = extracted_deadline
#                 policy.status = "active"
#                 policy.abolished_at = None
#                 policy.updated_at = now
#
#             session.add(policy)
#             synced += 1
#
#     session.commit()
#     return synced
