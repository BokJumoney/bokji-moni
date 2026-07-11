from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from pydantic import BaseModel, Field

from app.domain.chat.graph.state import GraphState
from app.infrastructure.config import settings

OLLAMA_MODEL = settings.LOCAL_MODEL
OLLAMA_BASE_URL = settings.LOCLAL_LLM_URL

llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

# CSV 파일을 읽고 청크 단위로 텍스트를 잘라 리스트로 담아 반환
def read_csv_and_split_text(csv_path, chunk_size=1000, chunck_overlap=150):
    print(f'CSV: {csv_path} ------')
    df = pd.read_csv(csv_path)
    documents = []

    for index, row in df.iterrows():
        # 2. 메타데이터 구성 (필터링 및 식별 용도)
        # Chroma의 where 절에서 활용할 수 있도록 정형 데이터 위주로 지정합니다.
        metadata = {
            "service_id": str(row["서비스ID"]),
            "service_name": str(row["서비스명"]),
            "department": str(row["소관부처명"]),
            "year": int(row["기준연도"]) if pd.notnull(row["기준연도"]) else 0,
            "cycle": str(row["지원주기"]) if pd.notnull(row["지원주기"]) else "",
            "type": str(row["제공유형"]) if pd.notnull(row["제공유형"]) else "",
            "life_cycle": str(row["생애주기"]) if pd.notnull(row["생애주기"]) else "",
            "topic": str(row["관심주제"]) if pd.notnull(row["관심주제"]) else "",
            "household_type": str(row["가구유형"]) if pd.notnull(row["가구유형"]) else ""
        }

        # 3. 본문 텍스트 구조화 (벡터 검색 및 의미 파악 용도)
        # LLM과 임베딩 모델이 문맥을 이해하기 쉽도록 서술형 템플릿으로 재조합합니다.
        page_content = f"""
            [서비스명: {row['서비스명']}]
            소관부처: {row['소관부처명']}
            서비스 요약: {row['서비스요약']}

            # 대상자 상세 내용
            {row['대상자상세내용']}

            # 선정 기준 및 자격 요건
            {row['선정기준내용']}

            # 급여 및 서비스 내용 (지원 혜택)
            {row['급여서비스내용']}

            # 신청 절차 및 방법
            {row['신청절차']}

            # 안내 및 문의
            - 문의처: {row['문의처']}
            - 문의처 목록: {row['문의처목록']}
            - 홈페이지: {row['홈페이지목록']}
            - 근거 법령: {row['근거법령목록']}
        """

        # Document 객체 생성
        doc = Document(page_content=page_content.strip(), metadata=metadata)
        documents.append(doc)

    # 3. 긴 텍스트를 위한 Chunking 처리
    # 선정 기준이나 지원 내용이 매우 길기 때문에 벡터 DB의 한계를 넘지 않도록 분할
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunck_overlap,
        separators=["\n# ", "\n\n", "\n", " ", ""]
    )

    # 최종적으로 벡터 DB에 들어갈 청크 리스트
    split_docs = text_splitter.split_documents(documents)

    print(f'Number of splits: {len(split_docs)}\n')

    return split_docs

# vectorstore 설정
embedding = OpenAIEmbeddings(
    base_url="http://localhost:1234/v1",
    model="text-embedding-bge-m3-ko",
    check_embedding_ctx_length=False
)

persist_directory='./chroma_store'

if os.path.exists(persist_directory):
    print("Loading existing Chroma store")
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding
    )
else:
    print("Creating new Chroma Store")

    vectorstore = None
    for g in glob('./data/*.csv'):
        chunks = read_csv_and_split_text(g)
        # 100개씩 나눠서 저장
        for i in range(0, len(chunks), 100):
            if vectorstore is None:
                vectorstore = Chroma.from_documents(
                    documents=chunks[i:i+100],
                    embedding=embedding,
                    persist_directory=persist_directory
                )
            else:
                vectorstore.add_documents(
                    documents=chunks[i:i+100]
                )

# 1. 키워드 검색기(BM25) 설정
bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 3

# 2. 벡터 검색기(Chroma) 설정
chroma_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 3. 하이브리드 앙상블 검색기 생성 (가중치를 5:5로 설정)
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, chroma_retriever],
    weights=[0.5, 0.5]
)

async def retrieve(state):
    """
    vectorstore에서 질문에 대한 문서를 검색한다.

    :param
        state (dict): 현재 graph state
    :return:
        state (dict): 검색된 문서와 사용자 질문을 포함하는 새로운 graph state
    """
    print("------ RETRIEVE ------")
    question = state['question']

    #Retrieve documents
    documents = ensemble_retriever.invoke(question)
    return {"documents": documents, "question": question}


generate_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        당신은 복지 정책 도우미입니다.
        아래 문서를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하세요.
        문서에 관련 정보가 없는 경우, 일반적인 지식으로 답변하세요.
    """),
    ("human", "질문: {question}\n\n문서: {documents}"),
])

rag_chain = generate_prompt | llm


async def generate(state: GraphState) -> dict:
    """
    검색된 문서와 사용자 질문을 바탕으로 최종 답변을 생성한다.
    """
    question = state["question"]
    documents = state.get("documents", [])
    documents_text = "\n".join(documents) if documents else "관련 문서 없음"

    response = await rag_chain.ainvoke(
        {"question": question, "documents": documents_text}
    )
    return {"generation": response.content}


casual_prompt = ChatPromptTemplate.from_messages([
    ("system", """
        당신은 친근하고 따뜻한 대화 파트너입니다.
        사용자와 자연스러운 일상 대화를 나누세요.
        대화 기록을 참고하여 맥락에 맞는 답변을 제공하세요.
    """),
    ("human", "{question}"),
])

casual_chain = casual_prompt | llm


async def casual_talk(state: GraphState) -> dict:
    """
    복지 정책과 관련 없는 일상적인 대화에 대한 답변을 생성한다.
    """
    question = state["question"]
    response = await casual_chain.ainvoke({"question": question})
    return {"generation": response.content}