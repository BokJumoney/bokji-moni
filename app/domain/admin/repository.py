from langchain_core.documents import Document
from sqlmodel import Session, select

from app.domain.admin.entity.models import (
    PdfWelfareList,
    PolicyHwpMapping,
    WelfarePolicyHwp,
)
from app.domain.welfare.entity.models import WelfarePolicy
from app.infrastructure.vectorstore.setup_vectorstore import get_huggingface_vectorstore


class AdminRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_pdf_file(self, policy_uuid, policy_name):
        self.session.add(
            PdfWelfareList(policy_uuid=policy_uuid, policy_name=policy_name)
        )
        self.session.commit()

    def save_hwp_file(self, origin_file_name, hwp_uuid):
        hwp_file = WelfarePolicyHwp(
            hwp_uuid=hwp_uuid,
            origin_file_name=origin_file_name,
        )
        self.session.add(hwp_file)
        self.session.commit()
        self.session.refresh(hwp_file)
        return hwp_file

    def save_welfare_policy_hwp_mapping(self, service_id, hwp_uuid):
        self.session.add(
            PolicyHwpMapping(
                service_id=service_id,
                hwp_uuid=hwp_uuid,
            )
        )
        self.session.commit()

    def save_pdf_embedding(self, documents: list[Document]):
        get_huggingface_vectorstore().add_documents(documents)

    def find_pdf_files(self):
        return list(
            self.session.exec(
                select(PdfWelfareList).order_by(PdfWelfareList.policy_name)
            ).all()
        )

    def find_hwp_files(self):
        """드롭다운과 파일 목록에 사용할 HWP 파일·연결 정책명 목록을 반환한다."""
        statement = (
            select(WelfarePolicyHwp, WelfarePolicy.service_name)
            .select_from(WelfarePolicyHwp)
            .join(
                PolicyHwpMapping,
                PolicyHwpMapping.hwp_uuid == WelfarePolicyHwp.hwp_uuid,
                isouter=True,
            )
            .join(
                WelfarePolicy,
                WelfarePolicy.service_id == PolicyHwpMapping.service_id,
                isouter=True,
            )
            .order_by(WelfarePolicyHwp.origin_file_name)
        )
        return list(self.session.exec(statement).all())
