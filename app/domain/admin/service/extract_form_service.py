from pathlib import Path
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.domain.admin.service.admin_file_service import AdminFileService
from app.infrastructure.config import settings

class ExtractFormService:
    def __init__(self, admin_file_service: AdminFileService):
        self.admin_file_service = admin_file_service

    def get_openai_model(self) -> ChatOpenAI:

        return ChatOpenAI(
            model="gpt-5.6-luna",
            temperature=0,
            api_key=settings.OPENAI_API_KEY
        )

    def read_markdown(
        self,
        file_path: str | Path,
    ) -> str:
        path = Path(file_path)

        print(
            f"[파일 경로] {path.resolve()}"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"파일을 찾을 수 없습니다: {path.resolve()}"
            )

        markdown_text = path.read_text(
            encoding="utf-8"
        )

        print(
            f"[파일 문자 수] {len(markdown_text):,}자"
        )

        print(
            "[파일 앞부분]"
        )
        print(
            repr(markdown_text[:300])
        )

        if not markdown_text.strip():
            raise ValueError(
                "마크다운 파일이 비어 있습니다."
            )

        return markdown_text


    def create_embedding_text_chain(self):
        llm = self.get_openai_model()

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    [역할 부여]
                    당신은 대한민국 복지 신청서를 읽고 어떠한 요소를 작성해야 하는지 알려주는 관리자입니다.
                    
                    [주의 사항]
                    - 반드시 제공된 마크다운 전체 문서 내용만 근거로 분석하세요.
                    - 동의서, 
                    여러 정책이 발견되면 정책별로 결과 데이터를 분리해서 반환하세요.

                    [문서 특징]
                    - 문서는 다양한 복지 정보를 소개하기 위한 사업 정보들입니다.
                    - 문서 내부에는 1개의 복지 정보 뿐만 아니라 다수의 정책이 포함될 수 있습니다.
                    - 정책 기준연도, 공고일, 시행일, 신청기간 등은 정책 해석에 중요한 메타데이터입니다.

                    [출력 규칙]
                    - 문서에서 직접 확인되는 내용만 사용하세요.
                    - 여러 정책이 있으면 정책마다 별도의 블록으로 분리하세요.
                    - 출력 시 ====== 는 각 항목의 구분자로, 아래 요소들을 구분지을 때 사용하세요.
                    - 한 항목의 형식은 `항목: 내용`을 지켜주세요.
                    - 전체 출력 형식은 아래와 같습니다.

                    [출력 형식]
                    [POLICY_START]
                    정책명:
                    ======
                    정책 요약:
                    ======
                    지원 대상:
                    ======
                    선정 기준:
                    ======
                    지원 내용:
                    ======
                    신청 기간:
                    ======
                    신청 방법:
                    ======
                    필요 서류:
                    ======
                    문의처:
                    ======
                    근거 법령:
                    ======
                    기준 정보:
                    ======
                    출처 위치:
                    ======
                    정보 충돌:
                    ======
                    문서 핵심 키워드:
                    [POLICY_END]
                        """.strip(),
                ),
                (
                    "human",
                    """
    출처 파일명:
    {source_file_name}

    마크다운 문서:
    {markdown_content}
    """.strip(),
                ),
            ]
        )

        return prompt | llm


    def clean_model_output(
        self,
        text: str,
    ) -> str:
        cleaned_text = text.strip()

        cleaned_text = re.sub(
            r"^```(?:text|markdown|md)?\s*",
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        )

        cleaned_text = re.sub(
            r"\s*```$",
            "",
            cleaned_text,
        )

        return cleaned_text.strip()


    def convert_markdown_to_embedding_text(
        self,
        markdown_text: str,
        source_file_name: str,
    ) -> str:
        if not markdown_text.strip():
            raise ValueError(
                "LLM 입력 텍스트가 비어 있습니다."
            )

        print(
            f"[LLM 입력 문자 수] "
            f"{len(markdown_text):,}자"
        )

        chain = self.create_embedding_text_chain()

        response = chain.invoke(
            {
                "source_file_name": source_file_name,
                "markdown_content": markdown_text,
            }
        )

        print(
            f"[응답 타입] {type(response).__name__}"
        )
        print(
            f"[응답 metadata] {response.response_metadata}"
        )
        print(
            f"[토큰 사용량] {response.usage_metadata}"
        )

        result_text = response.text.strip()

        if not result_text:
            finish_reason = (
                response.response_metadata.get(
                    "finish_reason"
                )
            )

            raise ValueError(
                "모델 응답에 텍스트가 없습니다. "
                f"finish_reason={finish_reason}, "
                f"content={repr(response.content)}"
            )

        return self.clean_model_output(
            result_text
        )


    def save_text(
        self,
        text: str,
        output_path: Path,
    ) -> None:
        output_path.write_text(
            text,
            encoding="utf-8",
        )

        print(
            f"[저장 완료] {output_path.resolve()}"
        )

    # 이게 메인(.md파일을 gpt에게 요청 후 txt파일로 저장)
    async def parse_md_to_txt(self, file_path: str, output_path: str):
        try:
            input_path = Path(
                file_path
            )

            markdown_text = self.read_markdown(
                input_path
            )

            result_text = (
                self.convert_markdown_to_embedding_text(
                    markdown_text=markdown_text,
                    source_file_name=input_path.name,
                )
            )

            output_path = Path(
                output_path
            )

            self.save_text(
                result_text,
                output_path,
            )

        except Exception as error:
            print(
                f"[오류] "
                f"{type(error).__name__}: {error}"
            )
