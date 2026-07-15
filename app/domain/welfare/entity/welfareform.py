from typing import Optional
from sqlmodel import SQLModel, Field

class WelfareForm(SQLModel, table=True):
    __tablename__ = "welfare_forms"

    id: Optional[int] = Field(default=None, primary_key=True)

    policy_code: str = Field(default="yet")

    form_name: str
    section: str
    file_path: str
    page_content: str