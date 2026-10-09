# Project Context
 
> A short orientation for any human or AI agent starting a session. It summarizes and points to the detailed documents; it does not replace them.
> **If this file conflicts with another document, follow `ARCHITECTURE.md`, then `PRD.md`, then `TASKS.md`.**
 
Last updated: 2026-10-09
 
## 1. What this project is
 
**Heimdall** (repository: `heimdall-rag`) is a multi-tenant **RAG-as-a-Service API with built-in observability**.
 
- Developers upload documents and call `/v1/query` to get cited answers.
- Every query is traced, and the **Watchtower** dashboard shows how each answer was produced (retrieval, reranking, generation, timings).
- It is both a software project and a learning project, so clear explanations and good documentation matter.
## 2. Hard constraints
 
- **₹0 budget.** No paid APIs, paid cloud services, or credit card. Everything required must be free.
- **Local-first.** The complete system must run on a developer laptop. Free hosting is optional.
- **Limited hardware and disk space.** Prefer small models and keep Docker and model storage modest.
- **Open-source preference** wherever possible.
## 3. Key decisions (already made)
 
| Area | Decision |
|---|---|
| Language | Python 3.11 |
| API | FastAPI, versioned under `/v1/` |
| Database | PostgreSQL 16 + pgvector |
| Keyword search | PostgreSQL full-text search (`tsvector` + GIN) |
| Retrieval | Hybrid (vector + keyword), merged with Reciprocal Rank Fusion, then cross-encoder reranking |
| Queue and cache | Redis; background jobs use **arq** (not Celery, not RQ) |
| LLM | Local model through **Ollama**; provider configurable (`LLM_BASE_URL`, `LLM_MODEL_NAME`, `LLM_API_KEY`) |
| Embeddings | Sentence Transformers, `BAAI/bge-small-en-v1.5` (384 dimensions) |
| API authentication | **`X-API-Key`** header; keys stored as SHA-256 hashes, shown once |
| Dashboard authentication | Email and password (argon2id) with an HTTP-only session cookie |
| Tenant isolation | `tenant_id` from authenticated identity only; filter inside SQL; foreign resources return 404 |
| Guardrail | Abstain without calling the LLM when evidence is weak; threshold calibrated with the evaluation dataset |
| Redis outage | Fail closed: query requests return HTTP 503 |
| Tracing | Must never break a request; store chunk IDs and short previews; 30-day default retention |
| Frontend | Next.js + TypeScript + Tailwind |
| Migrations | Alembic only |
 
## 4. Document map
 
| File | Purpose |
|---|---|
| `docs/PRD.md` | What we are building and why |
| `docs/ARCHITECTURE.md` | How the system works (source of truth for technical decisions) |
| `TASKS.md` | Ordered task list by phase |
| `docs/RULES.md` | How code and AI agents should work |
| `docs/SECURITY.md` | Security requirements |
| `docs/TEST_PLAN.md` | What "working" means |
| `docs/DESIGN.md` | Watchtower look and feel |
| `docs/DECISIONS.md` | Why important choices were made (ADRs) |
| `docs/MEMORY.md` | Current project state and next step |
| `AGENTS.md` | Instructions for AI coding agents |
| `.agents/skills/` | Project skills for Antigravity (and `.opencode/skills/` for opencode) |
 
## 5. Current status
 
- Phase: **0, Setup and planning**
- Implementation has not started.
- See `docs/MEMORY.md` for the exact current task, blockers, and next step.
## 6. Development environment
 
- Windows, working in Git Bash, with the project at `E:\heimdall_rag`.
- Docker Desktop runs PostgreSQL (with pgvector) and Redis; the backend, worker, and frontend can run on the host.
- Common commands: `make up`, `make dev`, `make test`, `make test-isolation`, `make lint`, `make eval`. If `make` is not installed, run the commands from the `Makefile` directly.
## 7. Non-negotiable rules (short version)
 
1. Every tenant-owned query filters by `tenant_id` inside the database query.
2. Every new tenant-scoped endpoint gets a cross-tenant isolation test.
3. API keys are hashed, shown once, and never logged.
4. Document text is untrusted input (prompt-injection defense).
5. Changes to chunking, embeddings, retrieval, reranking, thresholds, or prompts need `make eval` before and after.
6. Schema changes use Alembic migrations only.
7. Endpoints stay thin; logic lives in `services/` and `rag/`.
8. Never commit `.env` or secrets.
9. Architecture changes are recorded in `DECISIONS.md`.
## 8. How to work on a task
 
1. READ the relevant documents
2. UNDERSTAND the current code
3. PLAN (and wait for approval if more than two files change)
4. IMPLEMENT only the intended task
5. TEST
6. REVIEW the diff
7. FIX
8. COMMIT
9. UPDATE `TASKS.md` and `docs/MEMORY.md`
## 9. Open questions
 
- Exact local LLM model (decide in TASK-012 based on hardware and disk space)
- Whether a genuinely free public demo host is suitable (optional; verify limits before relying on any host)