# Enterprise AI Knowledge Assistant

Ask questions about your company's documents and get answers with sources. Upload PDFs, Word, Markdown or text files; the assistant retrieves the relevant passages and answers with Gemini, citing where each fact came from.

| Layer | Tech |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2, JWT auth |
| Agent | LangGraph (agentic RAG), LangChain, Gemini API |
| Retrieval | PostgreSQL + pgvector (HNSW) + Postgres full-text, fused with RRF |
| Optional HF | Hugging Face embeddings and a cross-encoder reranker |
| UI | React 18 + Vite |
| Ship | Docker Compose, GitHub Actions (CI + GHCR release) |

## Quick start

```bash
cp .env.example .env        # add GOOGLE_API_KEY and a random JWT_SECRET
docker compose up --build
```

Open http://localhost:3000, register (the **first account becomes admin**), upload a document on the *Documents* tab, wait for status `ready`, then ask questions on the *Chat* tab. API docs: http://localhost:8000/docs.

## How a question is answered

```mermaid
flowchart LR
    Q[Question] --> C[condense<br/>resolve follow-ups]
    C --> R{route}
    R -- chit-chat --> D[direct reply]
    R -- needs docs --> RT[retrieve<br/>vector + keyword + RRF]
    RT --> G{grade<br/>LLM relevance filter}
    G -- relevant --> GEN[generate<br/>cited answer]
    G -- none, retries left --> RW[rewrite query] --> RT
    G -- none --> FB[fallback<br/>"couldn't find it"]
```

- **Hybrid retrieval**: cosine search over pgvector plus Postgres `websearch_to_tsquery`, merged with reciprocal rank fusion. Exact terms (policy codes, names) and meaning both match.
- **Grading + rewrite**: an LLM pass discards irrelevant chunks; if nothing useful survives, the query is rewritten once and retried, then the assistant says it doesn't know instead of guessing.
- **Citations**: the model cites passages as `[1]`, `[2]`; the API returns filename, page and snippet for each cited passage.
- **Access control**: every search is filtered in SQL by visibility. Documents are `org` (everyone) or `private` (owner only).
- Retrieved text is treated as untrusted data in the prompts (basic prompt-injection hygiene).

## Project layout

```
backend/app/
  main.py, config.py, db.py, models.py, schemas.py, security.py, deps.py
  routers/   auth.py  documents.py  chat.py
  rag/       loaders.py (extract + chunk)  embeddings.py  vectorstore.py
             fusion.py  retrieval.py  pipeline.py (background ingestion)
  agent/     graph.py (LangGraph)  runtime.py (Gemini wiring)
backend/tests/   security, loaders, RRF, and graph-routing tests (stubbed LLM)
frontend/src/    App, api.js, components/{Login,Chat,Documents}
.github/workflows/  ci.yml  release.yml
```

## API

| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | login is OAuth2 password form; returns a bearer token |
| GET | `/api/auth/me` | current user |
| POST | `/api/documents` | multipart `file` + `visibility`; returns `202`, ingestion runs in the background |
| GET / DELETE | `/api/documents`, `/api/documents/{id}` | owner or admin can delete |
| POST | `/api/chat` | `{question, conversation_id?}` → `{conversation_id, answer, citations[]}` |
| GET / DELETE | `/api/conversations`, `/api/conversations/{id}/messages` | per-user history |

## Configuration

All settings are environment variables (see `.env.example` and `backend/app/config.py`).

**Using Hugging Face.** Set `EMBEDDING_PROVIDER=huggingface`, `EMBEDDING_DIM=384` (for all-MiniLM-L6-v2) and build with `INSTALL_HF=true` (installs PyTorch, so the image is large). Set `RERANKER_ENABLED=true` to add a cross-encoder rerank step on top of either embedding provider.

**Changing embedding provider or dimension** changes the `chunks.embedding` column size. Drop the `chunks` table (or the volume: `docker compose down -v`) and re-upload documents.

## Local development

```bash
# database
docker compose up db -d

# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env   # then edit; DATABASE_URL defaults to localhost:5432
uvicorn app.main:app --reload
pytest && ruff check .

# frontend (proxies /api to :8000)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

## CI/CD

- `ci.yml` (push to `main`, every PR): ruff + pytest, frontend build, then Docker builds of both images.
- `release.yml` (tags like `v1.0.0`): builds and pushes `ghcr.io/<owner>/<repo>-backend` and `-frontend`.

## Before going to production

- Set a strong `JWT_SECRET`, change `POSTGRES_PASSWORD`, set `ALLOW_REGISTRATION=false` once users exist, and put TLS in front (reverse proxy or load balancer).
- Replace `create_all` in `db.py` with Alembic migrations once the schema starts changing.
- Ingestion uses FastAPI background tasks, which is fine for modest volume. For heavy use, move it to a queue (Celery, RQ, or Arq).
- Add rate limiting and SSO (OIDC) as your environment requires.
