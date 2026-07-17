from langchain_core.documents import Document

from sqlmodel import Session, select

from app.domain.admin.entity.models import WelfarePolicyHwp, PdfWelfareList, PdfHwpMapping
from app.infrastructure.vectorstore.setup_vectorstore import get_huggingface_vectorstore

class AdminRepository:

    def __init__(self, session: Session):
        self.session = session

    # pdf 기반 정책 list 테이블 저장
    def save_pdf_file(self, policy_uuid, policy_name):
        pdfWelfareList = PdfWelfareList(policy_uuid=policy_uuid, policy_name=policy_name)
        self.session.add(pdfWelfareList)
        self.session.commit()

    # hwp 파일 경로명 저장
    def save_hwp_file(self, origin_file_name, hwp_uuid):
        hwpWelfareFile = WelfarePolicyHwp(hwp_uuid = hwp_uuid, origin_file_name = origin_file_name)
        self.session.add(hwpWelfareFile)
        self.session.commit()
        self.session.refresh(hwpWelfareFile)
        return hwpWelfareFile

    # mapping 테이블 데이터 저장
    def save_pdf_hwp_mapping(self, policy_uuid, hwp_uuid):
        pdfHwpMapping = PdfHwpMapping(policy_uuid=policy_uuid, hwp_uuid=hwp_uuid)
        self.session.add(pdfHwpMapping)
        self.session.commit()

    # PDF 파일 임베딩 데이터 저장
    def save_pdf_embedding(self, documents : list[Document]):
        vectorstore = get_huggingface_vectorstore()
        vectorstore.add_documents(documents)

    def find_pdf_files(self) -> list[PdfWelfareList]:
        return list(
            self.session.exec(
                select(PdfWelfareList).order_by(PdfWelfareList.policy_name)
            ).all()
        )

    def find_hwp_files(self):
        statement = (
            select(WelfarePolicyHwp, PdfWelfareList.policy_name)
            .select_from(WelfarePolicyHwp)
            .join(
                PdfHwpMapping,
                PdfHwpMapping.hwp_uuid == WelfarePolicyHwp.hwp_uuid,
                isouter=True,
            )
            .join(
                PdfWelfareList,
                PdfWelfareList.policy_uuid == PdfHwpMapping.policy_uuid,
                isouter=True,
            )
            .order_by(WelfarePolicyHwp.origin_file_name)
        )
        return list(self.session.exec(statement).all())
