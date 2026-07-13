# AGENTS.md

Compact guidance for OpenCode sessions working in `bokji-moni`.

## Stack

FastAPI (`app/main.py`) on Python 3.13, served by uvicorn. LLM chat backed by a local Ollama instance. Data analysis via pandas on a cp949-encoded CSV.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload        # from repo root; app import path is `app.main`
```

- API root: `http://127.0.0.1:8000`. Docs at `/docs`. Chat endpoint: `POST /api/v1/chat/message`.
- CORS is preconfigured for `localhost:3000` and Vite dev servers on `:5173`/`127.0.0.1:5173` — do not widen without reason.

## External prerequisites

- **Ollama must be running locally** at `http://localhost:11434` with model `exaone3.5` pulled, or `/api/v1/chat/message` returns an "AI 모델 오류" string instead of failing fast. URL/model are hardcoded in `app/domain/chat/service/chat_service.py` (`OLLAMA_API_URL`, `OLLAMA_MODEL`) — there is no `.env` or config module.

## Architecture

Domain-driven layout under `app/domain/<bounded_context>/` with `api/` (FastAPI routers), `dto/` (pydantic request/response), `entity/` (models), `service/`, and `repository.py` per context.

- **`chat`** — only implemented domain. Routers wired in `app/main.py`.
- **`user`, `welfare`** — scaffolded only; routers/services are empty (`#`). Do not assume they expose endpoints. They are imported nowhere; adding them requires an explicit `app.include_router` in `main.py`.
- **`app/analysis/regional_analysis.py`** — standalone script, not imported by the API. Reads `data/welfare_20241231.csv` with `encoding="cp949"` via a relative path, so it must be run **from the repo root**: `python -m app.analysis.regional_analysis`. The CSV is cp949 (Korean); always pass `encoding="cp949"` when reading it, default utf-8 will fail.
- `app/common/` and `app/domain/*/repository.py` are placeholders unless populated.

## State

Chat sessions live in an **in-memory dict** (`sessions_db` in `app/domain/chat/service/chat_service.py`) keyed by uuid. State is lost on reload/restart. There is no DB or persistence layer yet.

## Conventions

- Comments, docstrings, and user-facing strings are in **Korean**; keep that when editing.
- DTOs are pydantic `BaseModel`; route I/O goes through `dto/` not raw dicts.
- No tests, lint, typecheck, or codegen are configured. `requirements.txt` has unpinned names only. Verify Python work by running `uvicorn` (or `python -m ...`) rather than assuming a test suite exists.
- `__init__.py` files exist throughout; treat `app/...` as a package and run from repo root.