from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
import uuid


class WelfarePolicyPdfVector(SQLModel, table=True):
    __tablename__ = "welfare_policy_pdf_vector"

    chunk_id: int | None = Field(primary_key=True, default=None)
    policy_id: uuid.UUID = Field(max_length=300)
    policy_name: str = Field(max_length=100)
    chunk_type: str = Field(max_length=20)
    content: str = Field(max_length=2000)
    embedding: list[float] = Field(
        sa_column=Column(Vector(1024), nullable=False)
    )


class PdfWelfareList(SQLModel, table=True):
    __tablename__ = "pdf_welfare_list"

    policy_uuid: uuid.UUID = Field(primary_key=True)
    policy_name: str = Field(max_length=100)


class WelfarePolicyHwp(SQLModel, table=True):
    __tablename__ = "welfare_policy_hwp"

    hwp_uuid: uuid.UUID = Field(primary_key=True)
    origin_file_name: str = Field(max_length=100)


class PolicyHwpMapping(SQLModel, table=True):
    """신청서 파일과 원천 복지 정책(service_id) 간의 연결 정보."""

    __tablename__ = "policy_hwp_mapping"

    id: int = Field(primary_key=True)
    service_id: str = Field(foreign_key="policies.service_id", max_length=25)
    hwp_uuid: uuid.UUID = Field(
        foreign_key="welfare_policy_hwp.hwp_uuid"
    )
