# 복지머니 (BokJi-Moni)

> AI 에이전트 기반 저소득층 복지 정보 제공 및 신청 보조 서비스

복지 정보 수집에 어려움을 겪는 저소득층에게 자연어 대화 기반으로 맞춤형 복지 정보를 제공하여 정보 격차와 복지 사각지대를 완화하는 서비스입니다.

---

## 목차

- [프로젝트 개요](#프로젝트-개요)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 실행](#설치-및-실행)
- [아키텍처 설계](#아키텍처-설계)
  - [백엔드 아키텍처 (FastAPI)](#백엔드-아키텍처-fastapi)
  - [LangGraph 설계](#랭그래프-설계)
  - [데이터베이스 설계](#데이터베이스-설계)
- [API 명세](#api-명세)
- [현재 구현 상태](#현재-구현-상태)

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **팀명** | 복주머니 |
| **팀원** | 두강현(팀장), 김영관, 이민호, 허민영 |
| **프로젝트명** | AI 에이전트를 활용한 저소득층 복지 정보 제공 및 신청 보조 서비스 |

### 선정 배경

- 복지 사각지대로 인한 피해 사례 꾸준히 발생
- 전통적 빈곤층 외 1인 고립가구, 가족 돌봄 청년, 고독사 위험군 등 새로운 형태의 취약계층 증가
- 맞춤형으로 복지 정책을 추천하는 서비스 부족

### 핵심 기능

1. **복지 정보 챗봇** — 자연어 질문에 대한 복지 정책 정보 제공 (RAG)
2. **자격 요건 확인** — 사용자 프로필 기반 맞춤형 자격 매칭
3. **신청 체크리스트** — 복지 신청 절차 및 구비서류 안내
4. **복지 정보 알림** — 신규 정책 등록 시 대상 사용자에게 맞춤형 알림 발송
5. **복지 자료 관리 (관리자)** — 복지 정책 CRUD 및 벡터 DB 재인덱싱

### 기대 효과

- 맞춤 정보 제공을 통한 복지 정책 참여율 확대
- 자연어 기반 접근성 향상으로 정보 수집 피로 감소
- 복지 정보의 사각지대 완화

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| **AI 모델 / 프레임워크** | LangChain, LangGraph, LLM (ChatGPT 5.5 / Qwen 3.5) |
| **백엔드** | Python 3.13, FastAPI |
| **데이터베이스** | PostgreSQL(RDB), pgvector(VectorDB) |
| **프론트엔드** | React (Vite) |
| **협업 / 개발 도구** | Notion, Discord, VSCode, PyCharm, WebStorm, Git & GitHub |

---

## 프로젝트 구조

```
bokji-moni/
├── app/
│   ├── main.py                          # FastAPI 앱 엔트리포인트 (라우터 등록)
│   │
│   ├── common/                          # 공통 유틸리티 및 예외 처리
│   │   ├── exceptions.py
│   │   └── utils.py
│   │
│   ├── domain/                          # 도메인 계층 (DDD 아키텍처)
│   │   ├── chat/                        # 챗봇 도메인
│   │   │   ├── api/chat_router.py
│   │   │   ├── dto/request.py, response.py
│   │   │   ├── entity/models.py
│   │   │   ├── service/chat_service.py  # LangGraph(챗봇 그래프) 호출
│   │   │   └── repository.py
│   │   │
│   │   ├── user/                        # 사용자 및 인증 도메인
│   │   │   ├── api/user_router.py       # 현재 스캐폴드
│   │   │   ├── api/auth_router.py       # [계획] 회원가입·로그인·로그아웃·세션 확인
│   │   │   ├── dto/request.py, response.py
│   │   │   ├── entity/models.py         # [계획] User, AuthSession
│   │   │   ├── service/user_service.py
│   │   │   ├── service/auth_service.py  # [계획] 세션 인증 서비스
│   │   │   ├── service/password_service.py # [계획] Argon2id
│   │   │   ├── dependencies.py          # [계획] get_current_user
│   │   │   └── repository.py
│   │   │
│   │   ├── welfare/                     # 복지 정보 도메인
│   │   │   ├── api/welfare_router.py
│   │   │   ├── dto/request.py, response.py
│   │   │   ├── entity/models.py
│   │   │   ├── service/welfare_service.py
│   │   │   └── repository.py
│   │   │
│   │   ├── notification/                # [계획] 알림 도메인
│   │   │   ├── api/notification_router.py
│   │   │   ├── dto/request.py, response.py
│   │   │   ├── entity/models.py
│   │   │   ├── service/notification_service.py
│   │   │   └── repository.py
│   │   │
│   │   └── admin/                       # [계획] 관리자 도메인
│   │       ├── api/admin_router.py
│   │       ├── dto/request.py, response.py
│   │       ├── service/admin_service.py # LangGraph(관리자 그래프) 호출
│   │       └── repository.py
│   │
│   ├── infrastructure/                  # 인프라스트럭처 계층
│   │   ├── config.py                    # 환경 변수 및 설정 관리
│   │   ├── db/connection.py             # SQLModel 세션 관리
│   │   ├── llm/openai_client.py         # LLM 클라이언트 설정
│   │   ├── graphs/                      # [계획] LangGraph 노드 및 그래프 정의
│   │   │   ├── chatbot_graph.py
│   │   │   ├── notification_graph.py
│   │   │   └── admin_graph.py
│   │   └── scheduler/                   # [계획] 백그라운드 스케줄러
│   │       └── tasks.py
│   │
│   └── analysis/                        # 데이터 분석 모듈
│       └── regional_analysis.py
│
├── data/                                # 정적 데이터 파일
│   └── welfare_20241231.csv
│
└── requirements.txt
```

---

## 설치 및 실행

### 사전 요구사항

- Python 3.13
- **Ollama**가 로컬(`http://localhost:11434`)에서 실행 중이어야 하며, `exaone3.5` 모델이 pull 되어 있어야 합니다. (현재 챗봇 서비스가 Ollama 로컬 모델을 사용)

### 설치 및 실행

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API 서버: `http://127.0.0.1:8000`
- API 문서(Swagger): `http://127.0.0.1:8000/docs`
- 챗봇 엔드포인트: `POST /api/v1/chat/message`

### CORS 설정

CORS는 `localhost:3000` 및 Vite 개발 서버(`localhost:5173`, `127.0.0.1:5173`)에 대해 사전 구성되어 있습니다.

### 데이터 분산 분석 실행

```bash
python -m app.analysis.regional_analysis
```

> `data/welfare_20241231.csv` 파일은 cp949 인코딩이므로, 읽을 때 `encoding="cp949"`를 지정해야 합니다. 저장소 루트에서 실행해야 합니다.

---

## 아키텍처 설계

### 백엔드 아키텍처 (FastAPI)

도메인 주도 설계(DDD) 기반의 계층 구조를 채택합니다. 각 도메인은 `api/`(FastAPI 라우터), `dto/`(Pydantic 요청/응답), `entity/`(ORM 모델), `service/`(비즈니스 로직), `repository.py`(데이터 접근)로 구성됩니다.

#### 인증 및 권한 관리

인증 기능은 **PostgreSQL 기반 서버 세션 방식으로 구현할 예정**입니다. 로그인에 성공하면 서버가 `auth_sessions` 테이블에 세션을 만들고, 브라우저에는 무작위 세션 토큰만 `HttpOnly` 쿠키로 전달합니다. DB에는 원본 토큰이 아니라 SHA-256 해시를 저장하며 JWT access/refresh token은 사용하지 않습니다.

비밀번호는 Argon2id로 해시하고, 보호된 API는 공통 `get_current_user` dependency를 통해 로그인 사용자를 확인합니다. 현재 사용자 도메인은 아직 스캐폴드 상태이므로 아래 권한 표와 인증 API는 목표 설계입니다.

| 권한 | 접근 가능 API | 설명 |
|------|---------------|------|
| 비인증 | `/auth/signup`, `/auth/login` | 회원가입, 로그인 |
| 사용자 세션 | `/chat/*`, `/users/*`, `/welfare/*`, `/notifications/*` | 챗봇, 프로필, 복지 조회, 알림 조회 |
| 관리자 세션 | `/admin/*` + 사용자 권한 전체 | 복지 자료 CRUD, 사용자 관리, 대시보드 |

> 인증 세션과 채팅 세션은 서로 다릅니다. 인증 세션은 로그인 상태를 나타내는 쿠키/DB 레코드이고, 채팅 API의 `session_id`는 대화방 식별자입니다. 두 값을 서로 재사용하지 않습니다.

#### MCP 서버 연동

FastAPI 애플리케이션 내부에 통합된 MCP Server를 통해 LangGraph 에이전트에 필요한 도구(Tools)를 SSE 기반으로 제공합니다.

- `app/mcp/server.py`: 복지 정보 검색, 자격 요건 확인 등 도메인별 Tool 정의
- `app/mcp/router.py`: `/mcp/sse`, `/mcp/messages` 엔드포인트 노출

#### 알림 스케줄러

APScheduler 기반 백그라운드 스케줄러가 매일 09:00에 알림 그래프를 실행합니다.

#### 에러 처리

공통 에러 응답 형식을 사용하며, LLM API 오류 시 503(Service Unavailable)을 반환합니다.

---

### LangGraph 설계

서비스는 **3개의 독립적인 LangGraph 그래프**로 구성됩니다.

| 그래프 | 역할 | 트리거 |
|--------|------|--------|
| **챗봇 그래프** | 사용자 대화 처리 (복지 검색, 자격 확인, 신청 보조, 매칭 알림) | 사용자 메시지 입력 |
| **알림 그래프** | 신규 복지 정책 등록 시 대상 사용자에게 알림 발송 | 스케줄러 / 신규 정책 이벤트 |
| **관리자 그래프** | 복지 자료 CRUD 및 벡터 DB 재인덱싱 | 관리자 API 요청 |

#### 챗봇 그래프 구조

```
[입력 전처리] → [의도 분류]
                    │
        ┌───────────┼───────────┬───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   복지_검색    자격_확인    신청_보조   매칭_알림   일반_대화
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
  RAG 응답 생성  자격 매칭   체크리스트   알림 내역   일반 응답
        │       결과 안내   단계별 안내   응답 생성       │
        └───────────┴───────────┴───────────┴───────────┘
                            │
                            ▼
                   [사용자 정보 추출]
                            │
                            ▼
                      [출력 후처리]
                            │
                            ▼
                    [후속 응답 판단]
                            │
                            ▼
                         [END]
```

**의도 분류 라벨**: `복지_검색`, `자격_확인`, `신청_보조`, `매칭_알림`, `일반_대화`

**주요 노드**:

- `preprocess`: 메시지 정제, 대화 이력 로드, 사용자 프로필 조회
- `classify_intent`: LLM 기반 의도 분류 (대화 이력 포함)
- `search_welfare`: pgvector 유사도 검색 (Tool Calling)
- `generate_rag_response`: 검색 문서 기반 답변 생성
- `check_eligibility`: 사용자 조건 vs 자격 요건 매칭
- `generate_checklist` / `generate_step_guide`: 신청 절차 안내
- `extract_user_info`: 대화에서 사용자 정보 자동 추출 → DB 저장
- `postprocess`: 응답 포맷팅, 대화 이력 DB 저장
- `check_followup`: 멀티턴 제어 (`needs_followup`)

#### 사용자 정보 자동 추출

대화에서 언급된 사용자 정보를 LLM으로 추출하여 DB에 자동 저장합니다.

| 사용자 발화 | 추출 결과 |
|---|---|
| "월 소득이 80만원이에요" | `{"income": 800000}` |
| "서울 사는 35살이고 혼자 살아요" | `{"region": "서울", "age": 35, "family_size": 1}` |
| "장애 3급 판정 받았어요" | `{"disability": {"grade": 3, "has_disability": true}}` |
| "지금 실업 상태입니다" | `{"employment_status": "unemployed"}` |

추출 대상: 소득, 나이, 가구원 수, 가구 유형, 거주 지역, 장애 여부, 재산, 직업 상태

#### 알림 그래프 구조

```
[START] → [신규 정책 감지]
              │
      신규 정책 있음 → [대상 사용자 매칭] → [알림 메시지 생성] → [알림 발송] → [END]
      신규 정책 없음 → [END]
```

#### 관리자 그래프 구조

```
[START] → [관리자 인증]
              │
      인증 성공 → [자료 CRUD 실행] → [벡터 DB 재인덱싱] → [알림 그래프 트리거] → [END]
      인증 실패 → [END]
```

#### 그래프 간 연동

- **관리자 그래프 → 알림 그래프**: 신규/수정 정책 등록 시 알림 그래프 비동기 트리거
- **알림 그래프 → 챗봇 그래프**: 사용자의 "새로운 알림 있나요?" 질문 시 `매칭_알림` 의도로 알림 내역 조회
- **챗봇 그래프 → 사용자 DB**: `extract_user_info` 노드가 추출한 정보를 자동 갱신

---

### 데이터베이스 설계

PostgreSQL + pgvector 기반의 데이터베이스를 사용합니다. 아래는 목표 스키마이며, 사용자·인증 관련 테이블은 아직 구현 전입니다.

세션 인증을 위해 `users (1) → (N) auth_sessions` 관계를 추가합니다. `auth_sessions`에는 원본 쿠키 토큰을 저장하지 않고 토큰 해시, 사용자 ID, idle/absolute 만료 시각, 폐기 시각만 저장합니다.

#### ER 다이어그램

```
┌──────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    users     │     │ user_welfare    │     │  conversations  │
├──────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)      │◄────│ user_id (FK)    │     │ id (PK)         │
│ email        │     │ income          │     │ session_id (UK) │
│ password_hash│     │ age             │     │ user_id (FK)    │
│ name         │     │ family_size     │     │ title           │
│ role         │     │ household_type  │     │ created_at      │
│ created_at   │     │ region          │     │ updated_at      │
└──────┬───────┘     │ disability      │     └───────┬─────────┘
       │              │ assets          │             │
       │              │ employment_stat │             │
       │              └─────────────────┘             │
       │                                              │
       │          ┌─────────────────┐                 │
       │          │    messages     │                 │
       │          ├─────────────────┤                 │
       │          │ id (PK)         │                 │
       │          │ conversation_id │◄────────────────┘
       │          │ role            │
       │          │ content         │
       │          │ intent          │
       │          │ created_at      │
       │          └─────────────────┘
       │
       │     ┌─────────────────┐    ┌────────────────────┐
       │     │  notifications  │    │ welfare_policies   │
       │     ├─────────────────┤    ├────────────────────┤
       ├────►│ user_id (FK)    │    │ id (PK)            │
       │     │ id (PK)         │    │ name               │
       │     │ policy_id (FK)  │◄───│ summary            │
       │     │ message         │    │ category           │
       │     │ is_read         │    │ eligibility        │
       │     │ created_at      │    │ benefits          │
       │     └─────────────────┘    │ application_method │
       │                            │ required_docs      │
       │     ┌─────────────────┐    │ department         │
       │     │welfare_embeddings│   │ start_date         │
       │     ├─────────────────┤    │ end_date           │
       │     │ id (PK)         │    │ created_at         │
       │     │ policy_id (FK)  │◄───│ updated_at          │
       │     │ chunk_text      │    └────────────────────┘
       │     │ embedding(vector)│
       │     │ created_at      │
       │     └─────────────────┘
```

#### 테이블 목록

| 테이블 | 설명 |
|--------|------|
| `users` *(계획)* | 사용자 계정 정보 (이메일, Argon2id 비밀번호 해시, 이름, 권한, 활성 상태) |
| `auth_sessions` *(계획)* | 서버 로그인 세션 (토큰 해시, 사용자 FK, idle/absolute 만료, 폐기 시각) |
| `user_welfare_info` | 사용자 복지 관련 정보 (소득, 나이, 가구원 수, 가구 유형, 거주 지역, 장애 정보, 재산, 직업 상태) |
| `conversations` | 대화 세션 정보 (세션 ID, 제목, 생성/수정 시간) |
| `messages` | 대화 메시지 이력 (역할, 내용, 의도 분류 결과) |
| `welfare_policies` | 복지 정책 정보 (정책명, 요약, 카테고리, 자격 요건, 급여, 신청 방법, 필요 서류, 담당 부서, 신청 기간) |
| `welfare_embeddings` | 복지 정책 임베딩 벡터 (pgvector VECTOR(1536) 타입) |
| `notifications` | 사용자 알림 내역 (관련 정책, 메시지, 읽음 여부) |

---

## API 명세

> 아래는 목표 API 구조입니다. 현재 코드에 등록된 라우터는 `/api/v1/chat`뿐이며, 인증·사용자·알림·관리자 API는 구현 상태 표를 기준으로 확인합니다.

### API 전체 구조

```
/api/v1/
├── auth/                          인증
│   ├── POST   /signup             사용자 회원가입
│   ├── POST   /login              사용자 로그인 (서버 세션 발급)
│   ├── POST   /logout             현재 인증 세션 폐기
│   └── GET    /session            로그인 사용자·세션 상태 조회
│
├── chat/                          챗봇
│   ├── POST   /message            챗봇 메시지 전송 (챗봇 그래프 실행)
│   ├── GET    /sessions           세션 목록 조회
│   ├── GET    /sessions/{id}/history  세션별 대화 이력 조회
│   └── DELETE /sessions/{id}     세션 삭제
│
├── users/                         사용자 프로필
│   ├── GET    /me                 내 프로필 조회
│   ├── PUT    /me                 내 프로필 수정
│   └── GET    /me/welfare-info     내 복지 관련 정보 조회
│
├── welfare/                       복지 정보
│   ├── GET    /policies           복지 정책 목록 조회 (페이지네이션, 필터링)
│   ├── GET    /policies/{id}      복지 정책 상세 조회
│   ├── GET    /policies/{id}/checklist  신청 체크리스트 조회
│   └── GET    /search             복지 정보 텍스트 검색
│
├── notifications/                 알림
│   ├── GET    /                   내 알림 목록 조회
│   ├── GET    /unread-count       미읽 알림 수 조회
│   ├── PATCH  /{id}/read          알림 읽음 처리
│   └── PATCH  /read-all           전체 알림 읽음 처리
│
└── admin/                         관리자
    ├── GET    /policies           복지 정책 전체 목록 (관리용)
    ├── POST   /policies           복지 정책 등록 (관리자 그래프 실행)
    ├── PUT    /policies/{id}      복지 정책 수정 (관리자 그래프 실행)
    ├── DELETE /policies/{id}      복지 정책 삭제 (관리자 그래프 실행)
    ├── GET    /users             사용자 목록 조회
    └── GET    /dashboard          대시보드 통계
```

### 주요 API 상세

#### 인증 API (`/api/v1/auth`)

> 아래 인증 API는 구현 예정입니다. 세션 토큰은 JSON 응답에 포함하지 않고 `HttpOnly` 쿠키로만 전달합니다.

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| POST | `/signup` | 사용자 회원가입 | 없음 |
| POST | `/login` | 사용자 로그인 및 DB 세션 발급 | 없음 |
| POST | `/logout` | 현재 세션 폐기 및 쿠키 삭제 | 선택적 세션 |
| GET | `/session` | 현재 로그인 사용자와 세션 만료 정보 조회 | 세션 |

JWT access token, refresh token 및 `/refresh` 엔드포인트는 사용하지 않습니다. 관리자도 별도의 토큰 API가 아니라 동일한 세션 인증 후 `role`을 검사하는 방식으로 확장합니다.

#### 챗봇 API (`/api/v1/chat`)

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| POST | `/message` | 챗봇 메시지 전송 (챗봇 그래프 실행) | 세션 |
| GET | `/sessions` | 세션 목록 조회 | 세션 |
| GET | `/sessions/{session_id}/history` | 세션별 대화 이력 조회 | 세션 |
| DELETE | `/sessions/{session_id}` | 세션 삭제 | 세션 |

**챗봇 메시지 요청/응답**

```python
# 요청
class ChatMessageRequest(BaseModel):
    message: str                      # 사용자 메시지
    session_id: Optional[str]         # 채팅 세션 ID (인증 세션과 별개, 없으면 새 채팅 생성)

# 응답
class ChatMessageResponse(BaseModel):
    response: str                     # AI 응답 텍스트
    session_id: str                   # 채팅 세션 ID
    intent: str                       # 분류된 의도
    user_info_updated: bool           # 사용자 정보 갱신 여부
    needs_followup: bool              # 후속 대화 필요 여부
    sources: Optional[list[dict]]     # 참조된 복지 정보 출처
```

#### 사용자 프로필 API (`/api/v1/users`)

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| GET | `/me` | 내 프로필 조회 | 세션 |
| PUT | `/me` | 내 프로필 수정 | 세션 |
| GET | `/me/welfare-info` | 내 복지 관련 정보 조회 | 세션 |

#### 복지 정보 API (`/api/v1/welfare`)

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| GET | `/policies` | 복지 정책 목록 조회 (페이지네이션, 필터링) | 세션 |
| GET | `/policies/{policy_id}` | 복지 정책 상세 조회 | 세션 |
| GET | `/policies/{policy_id}/checklist` | 신청 체크리스트 조회 | 세션 |
| GET | `/search` | 복지 정보 텍스트 검색 | 세션 |

#### 알림 API (`/api/v1/notifications`)

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| GET | `/` | 내 알림 목록 조회 | 세션 |
| GET | `/unread-count` | 미읽 알림 수 조회 | 세션 |
| PATCH | `/{notification_id}/read` | 알림 읽음 처리 | 세션 |
| PATCH | `/read-all` | 전체 알림 읽음 처리 | 세션 |

#### 관리자 API (`/api/v1/admin`)

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| GET | `/policies` | 복지 정책 전체 목록 (관리용) | 관리자 세션 |
| POST | `/policies` | 복지 정책 등록 (관리자 그래프 실행) | 관리자 세션 |
| PUT | `/policies/{policy_id}` | 복지 정책 수정 (관리자 그래프 실행) | 관리자 세션 |
| DELETE | `/policies/{policy_id}` | 복지 정책 삭제 (관리자 그래프 실행) | 관리자 세션 |
| GET | `/users` | 사용자 목록 조회 | 관리자 세션 |
| GET | `/dashboard` | 대시보드 통계 | 관리자 세션 |

---

## 현재 구현 상태

> 아래 표는 현재 저장소 코드 기준입니다. 설계된 기능과 구현 완료 기능을 구분합니다.

| 도메인 | 상태 | 비고 |
|--------|------|------|
| **chat** | 구현됨 (초기) | LangGraph로 복지 검색과 일반 대화 분기. 대화 세션은 인메모리 저장소를 사용하여 재시작 시 초기화됨 |
| **user / auth** | 구현 전 | 라우터·DTO·엔티티·서비스·repository가 비어 있고 `main.py`에 등록되지 않음. PostgreSQL 서버 세션 방식으로 구현 예정 |
| **welfare** | 일부 구현 | 정책 SQLModel과 PGVector/BM25 검색 기반은 있으나 API router/service는 스캐폴드 상태 |
| **notification** | 미구현 | 설계만 존재 |
| **admin** | 미구현 | 설계만 존재 |
| **infrastructure** | 일부 구현 | Pydantic Settings, PostgreSQL/SQLModel 연결, PGVector 및 하이브리드 retriever 구현 |
| **DB 연동** | 일부 구현 | 앱 시작 시 PostgreSQL과 pgvector를 초기화함. 사용자·인증·대화 영속화 모델은 아직 없음 |
| **분석 스크립트** | 구현됨 | `app/analysis/regional_analysis.py` (독립 실행 스크립트) |

### 현재 제약사항

- Ollama가 로컬에서 실행되지 않으면 `/api/v1/chat/message`가 "AI 모델 오류" 문자열을 반환합니다.
- 인증 기능이 아직 없어 채팅 API는 임시 `test_user_id`를 사용합니다. 인증 구현 후 `get_current_user`에서 받은 실제 사용자 ID로 교체해야 합니다.
- Ollama URL과 모델명, PostgreSQL, 임베딩 설정은 `app/infrastructure/config.py`에서 관리하며 `.env`로 재정의할 수 있습니다.
- 서버 시작에는 PostgreSQL/pgvector와 벡터 적재에 필요한 OpenAI 임베딩 설정이 필요합니다.
- 테스트, 린트, 타입체크가 구성되어 있지 않습니다.
