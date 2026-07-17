from app.domain.admin.repository import AdminRepository
from langchain_core.documents import Document

class AdminService:

    def __init__(self, admin_repository: AdminRepository):
        self.admin_repository = admin_repository

    # pdf 파일 임베딩
    async def save_pdf_embedding(self, policy_uuid, policy_name, documents: list[Document]):
        self.admin_repository.save_pdf_file(policy_uuid, policy_name)
        self.admin_repository.save_pdf_embedding(documents)

    # hwp 파일 저장 시 메소드
    def save_hwp_form(self, policy_uuid, origin_file_name, hwp_uuid):
        # hwp 데이터 테이블 저장
        hwpWelfareFile = self.admin_repository.save_hwp_file(origin_file_name, hwp_uuid)

        self.admin_repository.save_pdf_hwp_mapping(policy_uuid, hwpWelfareFile.hwp_uuid)

    def get_pdf_files(self):
        return self.admin_repository.find_pdf_files()

    def get_hwp_files(self):
        return self.admin_repository.find_hwp_files()
