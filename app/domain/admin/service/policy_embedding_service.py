import psycopg
import re
from pathlib import Path
import uuid

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


class PolicyEmbeddingService:
    def __init__(self):
        self.CONNECTION_STRING= (
            "postgresql://"
            "edu:1234@localhost:5432/edudb" 
        )
        self.EMBEDDING_DIMENSION=1024

    def create_table(self):
        with psycopg.connect(self.CONNECTION_STRING) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS welfare_policy_pdf_vector (
                        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        policy_id VARCHAR(300) NOT NULL,
                        policy_name VARCHAR(100) NOT NULL,
                        chunk_type VARCHAR(30) NOT NULL,
                        content VARCHAR(2000),
                        embedding VECTOR({self.EMBEDDING_DIMENSION}) NOT NULL           
                    );
                    """
                )
        print("policies 테이블 생성 완료")

    def insert_policy(
        self,
        document: dict,
        vector: list[float],
    ) -> None:
        with psycopg.connect(
            self.CONNECTION_STRING
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO welfare_policy_pdf_vector (
                        policy_id,
                        policy_name,
                        chunk_type,
                        content,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        document["policy_id"],
                        document["policy_name"],
                        document["chunk_type"],
                        document["content"],
                        vector,
                    ),
                )

                print(
                    f"[정책 저장 완료] "
                    f"{cursor.rowcount}개"
                )

    # =========================================================
    # TXT 파일 읽기
    # =========================================================

    def read_policy_text(
        self,
        file_path: str,
    ) -> str:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"파일을 찾을 수 없습니다: {path.resolve()}"
            )

        text = path.read_text(
            encoding="utf-8"
        )

        if not text.strip():
            raise ValueError(
                "TXT 파일의 내용이 비어 있습니다."
            )

        print(
            f"[파일 읽기 완료] {path.resolve()}"
        )
        print(
            f"[전체 문자 수] {len(text):,}자"
        )

        return text


    # =========================================================
    # POLICY_START / POLICY_END 기준 분리
    # =========================================================

    def split_policy_blocks(
        self,
        text: str,
    ) -> list[str]:
        """
        [POLICY_START]
        ...
        [POLICY_END]

        시작·종료 구분자를 제외하고
        내부 정책 내용만 반환합니다.
        """

        pattern = re.compile(
            r"\[POLICY_START\](.*?)\[POLICY_END\]",
            flags=re.DOTALL,
        )

        matches = pattern.findall(text)

        policy_blocks: list[str] = []

        for match in matches:
            content = match.strip()

            if not content:
                continue

            policy_blocks.append(content)

        print(policy_blocks)
        if not policy_blocks:
            raise ValueError(
                "[POLICY_START]와 [POLICY_END] 사이의 "
                "정책 데이터를 찾지 못했습니다."
            )

        print(
            f"[정책 분리 완료] {len(policy_blocks)}개"
        )

        return policy_blocks


    # =========================================================
    # 정책명 추출
    # =========================================================

    def extract_policy_name(
        self,
        policy_block: str,
        default_name: str,
    ) -> str:
        match = re.search(
            r"^정책명:\s*(.*)$",
            policy_block,
            flags=re.MULTILINE,
        )

        if not match:
            return default_name

        policy_name = match.group(1).strip()

        if not policy_name:
            return default_name

        return policy_name


    # =========================================================
    # 출처 파일명 추출
    # =========================================================

    def extract_source_file(
        self,
        policy_block: str,
        default_source: str,
    ) -> str:
        match = re.search(
            r"^출처 파일:\s*(.*)$",
            policy_block,
            flags=re.MULTILINE,
        )

        if not match:
            return default_source

        source_file = match.group(1).strip()

        if not source_file:
            return default_source

        return source_file


    def parse_category_documents(self, policy_block: str) -> list[str]:
        result = []
        # 하나의 policy_block을 청크 단위로 분리
        blocks = policy_block.split("======")
        # 정책 명 추출
        policy_name = blocks[0].split(":")[1].replace("\n", "")

        # 정책명은 chunk에서 제외 (prefix로 들어감)
        for block in blocks[1:]:
            chunk_type, content = block.split(":", 1)
            chunk_type = chunk_type.replace("\n", "")
            result.append({
                "policy_name": policy_name,
                "policy_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, policy_name)),
                "chunk_type": chunk_type,
                "content": f"[{policy_name}] {chunk_type} {content}"
            })

        return result

    # =========================================================
    # Document 생성
    # =========================================================

    def create_documents(
        self,
        policy_blocks: list[str]
    ) -> tuple[list[str], list[str]]:
        documents: list[str] = []

        for index, policy_block in enumerate(
            policy_blocks,
            start=1,
        ):
            parsed_documents = self.parse_category_documents(policy_block)
            for document in parsed_documents:
                print(f"[{document["policy_name"]} - {document["chunk_type"]}] : 문서 파싱 완료 ({len(document["content"])}자)")
                documents.append(document)

        return documents

    # document를 vector화 시킨다.
    def parse_document_to_vector(self, documents, embeddings) -> list[list[float]]:
        document_vectors: list[list[float]] = []

        for index, document in enumerate(
            documents,
            start=1,
        ):
            vector = embeddings.embed_documents(
                [document["content"]]
            )[0]

            document_vectors.append(vector)

            print(
                f"[임베딩 완료] "
                f"{index}. "
                f"- 벡터 차원: {len(vector)}"
            )

        print(
            f"[전체 임베딩 완료] "
            f"{len(document_vectors)}개"
        )

        return document_vectors

    # 이게 메인(텍스트 파일을 임베딩 및 저장)
    async def txtfile_embedding(self, file_path: str):
        MODEL_NAME = (
            "dragonkue/"
            "snowflake-arctic-embed-l-v2.0-ko"
        )

        embeddings = HuggingFaceEmbeddings(
            model_name=MODEL_NAME,
            model_kwargs={
                "device": "cpu",      # GPU 사용 시 "cuda"
            },
            encode_kwargs={
                "normalize_embeddings": True,
            },
        )

        text = self.read_policy_text(file_path)
        policies = self.split_policy_blocks(text)
        # document 추출
        documents = self.create_documents(policy_blocks=policies)
        document_vectors = self.parse_document_to_vector(documents, embeddings)

        self.create_table()
        for document, vector in zip(documents, document_vectors):
            self.insert_policy(document, vector)
