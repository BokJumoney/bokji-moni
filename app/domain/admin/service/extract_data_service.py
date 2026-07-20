from pathlib import Path
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.domain.admin.service.admin_file_service import AdminFileService
from app.infrastructure.config import settings
from kiwipiepy import Kiwi
from rank_bm25 import BM25Okapi

class ExtractDataService:
    BM25_QUERY = (
        "정책명 정책 요약 지원 대상 선정 기준 지원 내용 신청 기간 신청 방법 소개"
        "필요 서류 문의처 근거 법령 기준 정보 출처 위치"
    )

    def __init__(self, admin_file_service: AdminFileService):
        self.admin_file_service = admin_file_service
        self.kiwi = Kiwi()

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
                    당신은 대한민국 복지 정책 문서를 읽고 복지 정책별 정보를 구조화해 추출하는 전문가입니다.
                    
                    [문서 특징]
                    - 문서 내용은 다수의 복지 정책을 안내하기 위한 문서일 수 있습니다 유념하여 정보를 추출하세요.
                    - 정책 기준연도, 공고일, 시행일, 신청기간 등은 정책 해석에 중요한 메타데이터입니다.
                    
                    [획득 정보]
                    당신이 얻어야 하는 정책별 정보는 다음과 같습니다.
                    
                    - 정책명
                    - 정책 요약
                    - 지원 대상
                    - 선정 기준
                    - 지원 내용
                    - 신청 기간
                    - 신청 방법
                    - 필요 서류
                    - 문의처
                    - 근거 법령
                    - 기준 정보
                    - 출처 위치
                    - 정보 충돌

                    [출력 규칙]
                    - 문서에서 직접 확인되는 내용만 사용하세요.
                    - 여러 정책이 있으면 정책마다 별도의 블록으로 분리하세요.
                    - 출력 시 ====== 는 각 항목의 구분자로, 아래 요소들을 구분지을 때 사용하세요.
                    - 한 항목의 형식은 `항목: 내용`을 지켜주세요.
                    - 전체 출력 형식은 아래와 같습니다.
                    - 출력 전에 모든 정책이 중복됐는지 확인 후 중복 시 통합해주세요.

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
            threshold_ratio = 0.3
            print(f"[점수 임계 비율] {threshold_ratio}")
            filtered_chunks = self.filter_md_by_bm25(
                path=input_path,
                query=self.BM25_QUERY,
                threshold_ratio=threshold_ratio
            )

            if filtered_chunks:
                markdown_text = "\n\n".join(
                    chunk
                    for chunk in filtered_chunks
                )
                print(
                    f"[BM25 선별] {len(filtered_chunks)}개 청크, "
                    f"{len(markdown_text):,}자"
                )
            else:
                print("[BM25 선별] 일치 청크가 없어 원문 전체를 사용합니다.")

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

    def read_text_file(self, path: str | Path) -> str:
        """UTF-8 텍스트 파일을 읽는다."""
        return Path(path).read_text(encoding="utf-8")

    def tokenize(self, text: str) -> list[str]:
        """Kiwi를 이용해 BM25 검색에 사용할 형태소를 추출한다."""
        return [
            token.form
            for token in self.kiwi.tokenize(text)
            if token.tag.startswith(("N", "V", "M"))
        ]

    def split_markdown(
            self,
            text: str,
            separator: str = "##",
    ) -> list[str]:
        """마크다운 텍스트를 지정된 구분자로 나눈다."""
        return [
            chunk.strip()
            for chunk in text.split(separator)
            if chunk.strip()
        ]

    def filter_md_by_bm25(
            self,
            path: str | Path,
            query: str,
            threshold_ratio: float = 0.3,
            separator: str = "##",
    ) -> list[str]:
        """
        Markdown 문서를 청크로 나눈 후 BM25 점수가
        최고 점수의 threshold_ratio 이상인 청크를 반환한다.

        원본 문서 순서를 유지한다.
        """
        if not 0 <= threshold_ratio <= 1:
            raise ValueError(
                "threshold_ratio는 0 이상 1 이하이어야 합니다."
            )

        markdown_text = self.read_text_file(path)
        chunks = self.split_markdown(markdown_text, separator)

        if not chunks:
            return []

        # BM25 계산용 형태소 토큰
        tokenized_docs = [
            self.tokenize(chunk)
            for chunk in chunks
        ]

        tokenized_query = self.tokenize(query)

        if not tokenized_query:
            raise ValueError("검색어에서 유효한 형태소를 추출하지 못했습니다.")

        bm25 = BM25Okapi(tokenized_docs)

        # scores[i]는 chunks[i]의 점수
        scores = bm25.get_scores(tokenized_query)

        max_score = float(max(scores))

        if max_score <= 0:
            return []

        threshold_score = max_score * threshold_ratio

        results = []

        # 정렬하지 않으므로 원본 문서 순서 유지
        for index, (chunk, score) in enumerate(zip(chunks, scores)):
            score = float(score)

            if score >= threshold_score:
                results.append(chunk)

        return results
