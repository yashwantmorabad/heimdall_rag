# Product Requirements Documents (PRD)

> PRD = What we re building and WHY.

## Product
**heimdall-rag**: is a multi-tenant RAG-as-a-Service API with built-in observability.

## Problem
- Many apps need an AI that answers questions from their own documents, but building the pipeline (parsing, chunking, embedding, search, answer generation) is hard.
- When a RAG answer is wrong, developers cannot tell whether retrieval, ranking, or the LLM failed.

## Target users
1. **Developers and small teams** who want "chat with your documents" in their product without building the pipeline.
2. **Student and portfolio developers** who need a reliable document Q&A backend for projects (for example a college FAQ bot).

## Goal
Let a developer sign up, upload documents, and call `/v1/query` to get cited answers, then open a dashboard to see exactly how each answer was produced.

## Core features
1. Accounts, tenants, and API keys
2. Document upload and background indexing
3. Cited question answering with a "not found in your documents" guardrail
4. Hybrid retrieval (keyword + vector) with reranking
5. Rate limits, quotas, and usage metering
6. Tracing of every query (spans, latency, tokens, cost)
7. Developer dashboard (keys, documents, usage, trace explorer, failure view)
8. Evaluation harness (recall@k, faithfulness)

## MVP (phases 1 to 4 in TASKS.md)
- Sign up and log in to the dashboard
- Create, list, and revoke API keys (stored hashed)
- Upload PDF documents and see indexing status
- `POST /v1/query` returns an answer with citations
- Strict mode: answers only from the tenant's documents, with a not-found response when retrieval is weak
- Per-key rate limiting and monthly quota
- Every query produces a trace with per-step spans
- Dashboard pages: keys, documents, usage, trace list and trace detail
- Tenant A can never read tenant B's data (enforced by automated tests)

## Out of scope for the first version
- Mobile app
- Payments and real billing (usage metering only)
- Fine-tuning or training models
- Multimodal retrieval (images, audio, video)
- OAuth2 client-credentials tokens (possible later)
- Team roles and shared workspaces
- Self-hosted customer deployments

## Stretch goals (after the MVP is deployed)
- Python SDK
- Embeddable chat widget
- Failure clustering by topic
- Evaluation runs triggered by customers
- Optional per-key IP allowlist
- ClickHouse for trace storage if Postgres becomes slow
- MCP server

## Success criteria
A new developer can, using only the dashboard and API docs:
1. Create an account and an API key
2. Upload a PDF and see it become `ready`
3. Call `/v1/query` with the key and receive a cited answer
4. Ask something not in the documents and receive a "not found" response
5. Open the trace for that query and see retrieval, rerank, and generation steps with timings
6. Revoke the key and see further calls rejected

Quality criteria:
- The isolation test suite passes on every commit.
- A documented evaluation run shows recall@k and faithfulness for the default configuration.
- A documented load test shows latency under concurrent requests.
- A public demo link is live.

## Non-functional requirements
- Security: see SECURITY.md
- Reliability: ingestion jobs are retry-safe; tracing failures never break queries
- Observability: structured logs include `trace_id` and `tenant_id`
- Maintainability: layered code as described in ARCHITECTURE.md

## Risks
| Risk | Mitigation |
|---|---|
| Scope grows too large | Only phases 1 to 4 are required; later items are optional |
| Cross-tenant data leak | Tenant filter in SQL, isolation tests in CI, 404 on foreign resources |
| LLM cost | Quotas, cheap or local models in development, usage tracking |
| Trace volume grows quickly | Store chunk IDs and short previews only; retention policy |
| Prompt injection from uploaded documents | Delimited context, instructions to ignore embedded commands, injection test cases |
