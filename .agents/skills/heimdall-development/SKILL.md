---
name: heimdall-development
description: Core project rules for Heimdall (heimdall-rag), a multi-tenant RAG-as-a-Service API with built-in observability (FastAPI, PostgreSQL + pgvector, Redis, arq, Ollama, Next.js). Use for ANY work in this repository, including planning, endpoints, database, workers, the RAG pipeline, tracing, tests, and documentation. Covers the project map, the zero-cost constraint, tenant isolation, working agreement, and definition of done. Load it first, even for small changes.
---

# Heimdall development

Heimdall lets developers upload documents and call `/v1/query` to get cited answers. Every query is traced, and the Watchtower dashboard shows how each answer was produced.

## Read first
1. `docs/PRD.md` (what and why)
2. `docs/ARCHITECTURE.md` (how; the source of truth for technical decisions)
3. `TASKS.md` and `docs/MEMORY.md` (what to do next)
4. `docs/RULES.md` and `docs/SECURITY.md`

If anything here conflicts with `docs/ARCHITECTURE.md`, follow the architecture and record any approved change in `docs/DECISIONS.md`.

## Hard constraints
- **Rs 0 budget:** no paid APIs, paid cloud services, or credit card. Prefer open-source and local tools.
- **Local-first:** the full system must run on a laptop. Free hosting is optional.
- **Limited hardware and disk:** prefer small models; do not add heavy dependencies without a reason.

## Fixed decisions
- Python 3.11, FastAPI, PostgreSQL 16 + pgvector, Redis, **arq** (never Celery or RQ), Next.js + TypeScript + Tailwind, Alembic.
- Local LLM through Ollama; provider configurable. Embeddings: Sentence Transformers (`BAAI/bge-small-en-v1.5`, 384 dimensions). Local cross-encoder reranker.
- API auth: **`X-API-Key`** header. Dashboard auth: session cookie.

## Folder map
```
backend/app/
  core/        settings, security, logging, rate limiting
  api/         deps.py (auth + tenant), v1/ (thin endpoints)
  schemas/     Pydantic models
  db/          models/, session.py
  services/    business logic
  rag/         ingestion/, retrieval/, reranking/, generation/, pipeline.py
  tracing/     tracer and spans
  workers/     arq jobs
backend/tests/ unit/, integration/, isolation/
evals/         datasets/, run_eval.py, reports/
frontend/      Next.js Watchtower dashboard
```

## Tenant isolation (highest priority)
- Every tenant-owned table has `tenant_id NOT NULL` and an index on it.
- Every query on tenant data filters by `tenant_id` **inside the database query**, including vector and keyword search.
- `tenant_id` comes only from the authenticated API key or session. Never from the request body, query string, or caller-controlled headers.
- Resources owned by another tenant return **404**.
- Every new tenant-scoped endpoint or query path gets a cross-tenant isolation test.

## Other non-negotiables
- API keys are hashed, shown once, and never logged.
- Document text is untrusted input.
- Tracing must never break a request.
- Schema changes use Alembic migrations only.
- Endpoints stay thin; logic lives in `services/` and `rag/`.
- Changes to chunking, embeddings, retrieval, reranking, thresholds, or prompts need `make eval` before and after.
- Never commit `.env` or secrets.

## Working agreement
- One task from `TASKS.md` at a time; do not change unrelated files.
- For changes touching more than two files, present a plan and wait for approval.
- Explain important unfamiliar concepts before introducing them (this is also a learning project).
- Loop: READ, UNDERSTAND, PLAN, IMPLEMENT, TEST, REVIEW, FIX, COMMIT, UPDATE docs.

## Commands
`make up`, `make down`, `make dev`, `make migrate`, `make test`, `make test-isolation`, `make lint`, `make eval`. If `make` is unavailable, run the commands from the `Makefile` directly.

## Definition of done
1. Tests pass, including isolation tests for new tenant-scoped paths.
2. `make eval` run before and after retrieval-related changes, with both results reported.
3. Diff reviewed for secrets, unrelated edits, and unsafe logging.
4. `TASKS.md` and `docs/MEMORY.md` updated.

## Related skills
`backend-development`, `database`, `rag-engineering`, `redis-workers`, `security`, `testing`, `observability`, `frontend-development`.
