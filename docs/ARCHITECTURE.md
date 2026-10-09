# Architecture

ARCHITECTURE = HOW the system works.

Read together with PRD.md, RULES.md, DECISIONS.md, and SECURITY.md. Last updated: 2026-10-09

## 1.Project Overview
**Heimdall** is a **RAG-as-a-Service API with built-in observability**.

Developers can:
1.Upload documents.
2.Have them processed and indexed in the background.
3.Query them through an API
4.Receive an answer with sources.
5.Inspect the complete RAG pipeline through the Watchtower dashboard.

The API is free to use, and the system is free to operate.
• Multi-tenant
• API-first
• Observable
• Secure
• Locally runnable and dockerized
• Free to operate
• Based on open-source software wherever possible

## 2.Zero-Cost Constraint
Heimdall is a ₹0-budget project. Everything required for development is free.

## Rules:
• Prefer open-source software and local extensions.
  Do not require paid APIs, paid cloud infrastructure, or credit card for the development setup.
• External free tires are optional extras only, and only if genuinely free.
  Their limits change often, so verify them before relying on them.
• The complete development environment must work locally.
• If no free hosting is suitable, the project stays fully runnable locally rather than requiring payment.

AI models
• LLM:a local open-sourced model through Ollama by default.
• Embeddings:Sentence Transformers, running locally.
• Rernker:a cross-Encoder, running locally.
• The LLM provider is configurable through settings(LLM_BASE_URL,
  LLM_API_KEY, LLM_MODEL_NAME,LLM_API_KEY) using an OPENAI-compatible interface, so another provider can be added later without redesiging the pipeline. 
• Hardware note:local models nned enough RAM. Confirm the development
  machine can run the choosen Ollama model before building features that depend on it, and keep a smaller fallback model in mind.   

## 3.Technology Stack
| Layer           | Component| Purpose|
|-----------------|----------|--------|
| Language         | python 3.11 | Backend API |
| Backend API      | FastAPI | Backend API |
| Database         | PostgreSQL 16 | Database |
| Vector search    | pgvector | Vector search |
| Keyword search|PostgreSQL full-text search(tsvector +GIN index)|Keyword search |
| Cache/ queue | Redis |
| Background workers | arq |
| Embeddings | Sentence Transformers |
| Reranker | Cross-Encoder |
| LLM | Local open-sourced model through Ollama |
| Frontend | Next.js + TypeScript |
| Styling | Tailwind CSS |
| Migrations | Alembic |
| Backend testing | pytest |
| E2E testing | Playwright |
| Containers | Docker + Docker Compose |
| Version control | Git+GitHub |

arq is choose over RQ and Celery: it is  async like FastAPI, lighter than Celery,
and runs on Windows development machines (RQ does not run natively on windows).
Recorded as ADR in 'DECISIONS.md'.

---

## 4. High-level Architecture

```text
 Developer application                Developer browser
          │                                   │
      X-API-Key                         Session cookie
          │                                   │
          ▼                                   ▼
 ┌────────────────────────────────────────────────────┐
 │                      FastAPI                       │
 │  Authentication · Tenant resolution · Rate limits  │
 │  Validation · RAG pipeline · Trace recording       │
 └───────┬──────────────────┬──────────────────┬──────┘
         │                  │                  │
         ▼                  ▼                  ▼
  PostgreSQL + pgvector   Redis            Ollama (local LLM)
         ▲                  │
         │                  ▼
         │            arq workers
         │          (document ingestion)
         │
         └──────── read by ───────► Watchtower (Next.js)
```
 
---

## 5. Multi-Tenancy

A tenant is a developer, application, organisation using Heimadall.

```text
Tenant
 ├── Users
 ├── API keys
 ├── Documents ── Chunks
 ├── Usage events
 ├── Traces ── Spans
 └── Feedback
```

Tenant data must never leak between tenants.

### Tenant resoultion

```text
X-API-Key ──► authenticate ──► tenant_id ──► request
```

- `tenant_id` comes **only** from authenticated credentials (API key or dashboard session).
- `tenant_id` is **never** read from the request body, query string, or caller-controlled headers.
- Every tenant-owned database query is scoped to the authenticated tenant.
- A resource owned by another tenant returns **404**, not 403, so its existence is not revealed.

---
## 6. Authentication

Two seperate mechanisms.

### 6.1 API authentication (developer applications)

```http
X-API-Key: hk_live_xxxxxxxxx
```

API keys are:
1. Generated with a crytpographically secure random source (at least 32 bytes).
2. Shown to the user **once**, at creation.
3. Stored only as a SHA-256 hash (keys are high-entropy random values, so a fst hash table is appropirate).
4. Compared in constasnt time.
5. Never stored in plaintext and never written to logs.

Stored per key:
```text
tenant_id, name, key_prefix, key_hash,
scopes, expires_at, revoked_at, last_used_at, created_at
```

Key lifecycle:
 
- **Scopes:** `query`, `documents`, `admin` (a key gets only what it needs).
- **Expiry:** optional `expires_at`; expired keys are rejected.
- **Revoke:** `revoked_at` immediately disables a key.
- **Rotate:** create a new key, switch over, revoke the old one.
- **Limit:** a maximum number of active keys per tenant (configurable, default 5).
- **`last_used_at`** is updated on use so unused keys can be found and removed.
- The prefix lets the dashboard identify a key without exposing the secret.

### 6.2 Dashboard authentication (Watchtower)
- Email and password, with passwords hashed using **argon2id** (or bcrypt).
- Session stored in an **HTTP-only, Secure, SameSite** cooki., 
- Login and signup endpoints are rate limited.

Dashboard sessions and API keys are seperate mechanisms and are never inter changeable.

---

## 7. Document Ingestion

Ingestion is asynchronous. The API never blocks on processing.

```text
POST /v1/documents
        │
        ▼
Validate file (type, size, filename)
        │
        ▼
Save file + create document record (status = queued)
        │
        ▼
Redis queue ──► arq worker
                   │
                   ├─ status = processing
                   ├─ Parse
                   ├─ Clean
                   ├─ Chunk
                   ├─ Embed
                   └─ Store chunks
                   │
                   ▼
              status = ready   (or failed, with an error message)
```

Rules:
- **Statuses:** `queued`, `processing`, `ready`, `failed`.
- Jobs are **idempotent**: retrying a job never creates duplicate chunks.
- Failures keep a short error message on the document record.
- Deleting a document deletes its chunks

### Supported documents
- PDF, TXT, Markdown
- Maximum **10 MB** per file (configurable)
- Type is checked by content as well as extension
- Filenames are sanitized and never used as filesystem paths

### File storage

- Local development: uploaded files go to a storage directory (a Docker volume), outside any web-served path.
- The original file is needed only until processing finishes. Whether originals are kept afterwards is a setting; discarding them keeps storage small and suits free hosting without persistent disks.
- S3-compatible storage is a future extension.

## 8. Chunking and Embeddings

```text
Document ─► extract text ─► clean ─► chunk ─► embed ─► store
```

Each chunk stores: 'tenant_id', `document_id`, content, position (and page where available), embedding, embedding model name, and a full-text `tsv` column.
 
- Chunk size and overlap are settings. Defaults are starting points, tuned only with evaluation results.
- Chunking is structure-aware where possible (headings for Markdown, pages for PDF).
- Embeddings are generated locally. Example model: `BAAI/bge-small-en-v1.5` (384 dimensions).
- The pgvector column dimension **must match** the embedding model.
- The embedding model name is stored with every chunk, so a model change can be detected and the corpus re-indexed. Do not mix vectors from different models in one search.

---

## 9. Vector Storage
 
PostgreSQL with pgvector holds vectors, avoiding a separate paid vector database.
 
```text
chunks
 ├── id
 ├── tenant_id
 ├── document_id
 ├── content
 ├── chunk_index
 ├── embedding          (vector)
 ├── embedding_model
 ├── tsv                (full-text)
 └── created_at
```
 
Tenant filtering happens **inside** the database query:
 
```text
Incorrect:  search all vectors ─► filter by tenant afterwards
Correct:    search vectors WHERE tenant_id = authenticated_tenant
```
 
---

## 10. Query Pipeline
 
```text
POST /v1/query
      │
      ▼
Authenticate ─► Resolve tenant ─► Rate limit ─► Quota check
      │
      ▼
Start trace
      │
      ▼
Retrieve ── vector search ─┐
         └─ keyword search ┴─► merge (Reciprocal Rank Fusion)
      │
      ▼
Rerank (cross-encoder)
      │
      ▼
Guardrail: enough evidence?
      │
      ├── NO ──► abstain ("I couldn't find enough information.")
      │
      └── YES ─► LLM ─► answer + sources
      │
      ▼
Record usage ─► finish trace ─► respond (with trace ID)
```

### 10.1 Hybrid retrieval
 
- **Vector search** finds semantically similar chunks.
- **Keyword search** (PostgreSQL full-text) finds exact or lexical matches.
- Both are tenant-scoped.
- Results are merged with **Reciprocal Rank Fusion (RRF)**, which combines rankings without needing comparable scores.
- Candidate counts (`RETRIEVAL_TOP_K`) and final counts (`RERANK_TOP_K`) are settings.

### 10.2 Reranking
 
A cross-encoder scores each `(query, chunk)` pair, and the best candidates go to the LLM. The reranker runs locally.
 
### 10.3 Guardrail
 
- If evidence is insufficient, Heimdall abstains and **does not call the LLM**.
- The threshold is a setting and is calibrated using the evaluation dataset, not chosen arbitrarily.
- The abstention response is a normal, successful API response, clearly marked as "not found".
### 10.4 Generation
 
- The prompt tells the model to answer only from the provided context and to cite chunks.
- Retrieved text is placed inside clearly delimited context blocks and treated as **untrusted data**. The model is told to ignore instructions found inside documents (prompt-injection defense).
- The LLM sits behind a service interface (`generate()` plus configuration), so providers can be swapped.
### 10.5 Sources and citations
 
The response includes the sources used, for example document, chunk, and page, with enough information for a developer to see where the answer came from.
 
---

## 11. Observability

Every query is a **trace**; each operation isnde it is a **span**.

```text
Trace
 ├── trace_id, tenant_id, request_id
 ├── status, total_latency
 └── spans[]
      ├── retrieval
      ├── reranking
      ├── llm
      └── result
```

| Span | Records |
|---|---|
| Retrieval | candidate count, method, scores, chunk IDs, latency, status |
| Reranking | input count, final top-k, latency, status |
| LLM | model, token counts when available, latency, status |
| Result | success, abstention, or error; user feedback when available |

Rules:
 
- Traces store chunk IDs and short previews, **not** full document text.
- The response includes the `trace_id` (header `X-Trace-Id`) so feedback and the dashboard can link to it.
- **Retention:** traces and spans are kept for a configurable period (default 30 days), then deleted.
- Logs are structured and include `trace_id` and `tenant_id`.

### Trace reliability
 
Tracing must never break the main request.
 
```text
Incorrect:  tracing fails ─► the whole request fails
Correct:    tracing fails ─► log the error ─► the request continues
```
 
---

## 12. Redis, Rate Limiting, and Quotas
 
Redis is used for:
 
- Rate limiting
- The background job queue (arq)
- Temporary state where appropriate
### Rate limiting
 
- Limits apply **per API key** and **per IP address**, checked before any expensive RAG work.
- Exceeding a limit returns **HTTP 429** with a `Retry-After` header.
- If Redis is unavailable, query requests are rejected with 503 rather than running without limits (to protect the local LLM). This choice can be revisited in `DECISIONS.md`.
### Quotas and usage
 
- A **monthly query quota** per tenant is checked before the pipeline runs.
- Every query and upload records a `usage_events` row (counts, tokens, bytes), so usage numbers match what was actually sent.
---

## 13. Database
 
PostgreSQL is the primary store.
 
| Table | Key columns |
|---|---|
| `tenants` | id, name, created_at |
| `users` | id, tenant_id, email, password_hash |
| `api_keys` | id, tenant_id, name, key_prefix, key_hash, scopes, expires_at, revoked_at, last_used_at |
| `documents` | id, tenant_id, filename, status, error, created_at |
| `chunks` | id, tenant_id, document_id, content, embedding, embedding_model, tsv |
| `usage_events` | id, tenant_id, api_key_id, kind, tokens, bytes, created_at |
| `traces` | id, tenant_id, status, latency_ms, question_preview, created_at |
| `spans` | id, trace_id, tenant_id, name, duration_ms, status, attributes |
| `feedback` | id, trace_id, tenant_id, rating, comment |
 
- Every tenant-owned table has `tenant_id NOT NULL` and an index on it.
- Schema changes use **Alembic migrations only**. The first migration enables the `vector` extension.
- Time-based indexes support trace queries and retention cleanup.
---

Public endpoints are versioned under `/v1/`.
 
```text
POST   /v1/documents
GET    /v1/documents
GET    /v1/documents/{document_id}
DELETE /v1/documents/{document_id}
 
POST   /v1/query
 
GET    /v1/keys
POST   /v1/keys
DELETE /v1/keys/{key_id}
 
GET    /v1/traces
GET    /v1/traces/{trace_id}
POST   /v1/feedback
 
GET    /v1/usage
```

Breaking changes require a new version.
 
### Errors
 
Errors are structured and predictable (`code`, `message`, and `trace_id` when available).
 
```text
400 invalid request        401 authentication failure
403 forbidden              404 not found
409 conflict               413 file too large
422 validation error       429 rate limit or quota exceeded
500 internal error         503 service unavailable
```
 
Internal details and secrets are never exposed to clients.
 
---
 
## 15. Code Structure
 
### Backend
 
```text
backend/
└── app/
    ├── main.py
    ├── core/            config, security, logging, rate limiting
    ├── api/
    │   ├── deps.py      authentication and tenant resolution
    │   └── v1/          thin endpoints
    ├── schemas/
    ├── db/
    │   ├── models/
    │   └── session.py
    ├── services/        business logic (keys, usage, quotas)
    ├── rag/
    │   ├── ingestion/
    │   ├── retrieval/
    │   ├── reranking/
    │   ├── generation/
    │   └── pipeline.py
    ├── tracing/
    └── workers/         arq jobs
```
 
### Frontend
 
```text
frontend/
└── app/
    ├── dashboard/
    ├── documents/
    ├── traces/
    ├── usage/
    └── settings/
```
 
The frontend talks to FastAPI through the API. Business logic is not duplicated in the frontend.
 
### Tests and evaluation
 
```text
backend/tests/   unit/  integration/  isolation/
evals/           datasets/  run_eval.py  reports/
```
 
---

## 16. Testing and Evaluation
 
Tests cover authentication, validation, the RAG pipeline, database operations, retrieval, **tenant isolation**, rate limiting, document processing, and error handling. Every new tenant-scoped endpoint needs a cross-tenant isolation test.
 
RAG quality is evaluated separately from software tests. Metrics:
 
- Retrieval Recall@K
- Retrieval relevance
- Abstention accuracy
- Answer correctness
Any change to chunking, embeddings, retrieval, reranking, thresholds, or prompts is evaluated **before and after**.
 
---
 
## 17. Watchtower Dashboard
 
```text
Next.js ─► FastAPI ─► Authentication · Documents · Keys · Traces · Usage
```
 
It provides: overview, API key management, documents, query traces, trace details (latency, retrieval, reranking, LLM, errors), feedback, and usage statistics.
 
Design direction:
 
```text
Background: #0F172A    Primary: #6366F1
Font: Inter            Code font: JetBrains Mono
```
 
Every view has loading, empty, and error states. An API key is shown once, in a modal, with a copy button.
 
---

## 18. Docker and Environments
 
Docker Compose runs PostgreSQL + pgvector and Redis. The backend, arq worker, frontend, and Ollama can run on the host or in containers. The project must remain reproducible from the repository.
 
| Environment | Purpose |
|---|---|
| **Local** | Full development: backend, worker, frontend, PostgreSQL, Redis, Ollama |
| **Preview** | Optional, only if a free host is suitable |
| **Demo** | Optional public demo using only free resources |
 
Notes for a free demo (verify current terms first):
 
- Free servers may sleep when idle, so the first request can take about a minute. State this in the README.
- Free servers may have little RAM and no persistent disk. Local embedding and reranker models may need to be lighter, or replaced by free APIs, and the embedding model must stay the same as in development to avoid re-indexing.
- Free LLM APIs have small quotas and different data policies, so load tests and automated tests use a fake LLM.
---
 
## 19. Security Summary
 
- API keys are hashed, never logged, shown once, with scopes, expiry, and revoke.
- Dashboard passwords use argon2id; sessions use secure cookies.
- Tenant IDs come only from authentication; all queries, including vector search, are tenant-scoped in SQL.
- Uploads are validated (type, size, filename).
- Input is validated with schemas.
- Prompt injection is handled by delimiting context and treating documents as untrusted.
- Secrets live in environment variables; `.env` is never committed.
- Internal errors are not exposed.
Details belong in `SECURITY.md`.
 
---
 
## 20. Architectural Non-Negotiables
 
1. Python version is **3.11**.
2. Heimdall must remain usable at **₹0 cost**; paid APIs are never required.
3. Prefer open-source and local AI models; the LLM provider is configurable.
4. PostgreSQL + pgvector is the vector storage layer; keyword search uses PostgreSQL full-text search.
5. Redis is used for the queue and rate limiting.
6. Background jobs use **arq** (not Celery or RQ).
7. Every tenant-owned table contains `tenant_id NOT NULL`.
8. Every tenant-scoped query filters by `tenant_id`, including vector and keyword search, inside the database query.
9. `tenant_id` comes only from authenticated identity.
10. Foreign-tenant resources return 404.
11. API keys are hashed with SHA-256, shown once, and support scopes, expiry, revoke, and an active-key limit.
12. Rate limits and quotas run before expensive RAG work.
13. The guardrail abstains without calling the LLM when evidence is weak; its threshold comes from evaluation.
14. Document text is untrusted input.
15. Tracing must never break the main request; traces store IDs and previews, not full documents, and have a retention period.
16. The embedding model name is stored with every chunk, and vectors from different models are never mixed.
17. Database changes use Alembic migrations only.
18. API endpoints remain thin; RAG logic lives in the RAG and service layers.
19. Every new tenant-scoped endpoint requires an isolation test.
20. Retrieval-related changes require evaluation before and after.
21. Secrets are never committed to Git.
22. Architecture changes are recorded in `DECISIONS.md`.
---
 
## 21. Development Principle
 
Heimdall is both a software project and a learning project. Work follows:
 
```text
READ ─► UNDERSTAND ─► PLAN ─► IMPLEMENT ─► TEST ─► REVIEW ─► FIX ─► COMMIT ─► UPDATE MEMORY
```
 
Agents should explain important unfamiliar concepts before introducing them.
 
---
 
## 22. Future Extensions
 
- Additional embedding models and LLM providers
- Better rerankers
- S3-compatible file storage
- Graph-based retrieval
- Customer-run evaluation pipelines
- Distributed tracing
- ClickHouse for large-scale traces
- Python SDK (**Hofund**)
- Optional per-key IP allowlist
These must not complicate the initial ₹0 implementation unnecessarily.
 
---
 
> **Core principle:** Heimdall should provide a complete, observable, multi-tenant RAG API while remaining fully usable locally and without requiring paid services.
 