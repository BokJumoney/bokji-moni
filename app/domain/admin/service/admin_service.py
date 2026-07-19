from langchain_core.documents import Document

from app.domain.admin.repository import AdminRepository


class AdminService:
    def __init__(self, admin_repository: AdminRepository):
        self.admin_repository = admin_repository

    async def save_pdf_embedding(self, policy_uuid, policy_name, documents: list[Document]):
        self.admin_repository.save_pdf_file(policy_uuid, policy_name)
        self.admin_repository.save_pdf_embedding(documents)

    def save_hwp_form(self, service_id, origin_file_name, hwp_uuid):
        hwp_file = self.admin_repository.save_hwp_file(
            origin_file_name,
            hwp_uuid,
        )
        self.admin_repository.save_welfare_policy_hwp_mapping(
            service_id,
            hwp_file.hwp_uuid,
        )

    def get_pdf_files(self):
        return self.admin_repository.find_pdf_files()

    def get_hwp_files(self):
        return self.admin_repository.find_hwp_files()


