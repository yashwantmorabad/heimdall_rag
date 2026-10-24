# Tasks
 
Work one task at a time: **read, understand, plan, implement, test, review, fix, commit, then update project memory**. Mark a task complete only when its acceptance criteria are met.
 
Use `PRD.md` for what Heimdall must do and `ARCHITECTURE.md` for how it must work. If a task conflicts with the finalized architecture, follow the architecture and record any approved architecture decision in `DECISIONS.md`.
 
Last updated: 2026-10-09
 
## Phase 0: Setup (about 3 days)
 
- [x] **TASK-001** Create the GitHub repository and push the starter project.
  - Done when: the repository contains the starter files, and `.env` or other secrets are not committed.
- [x] **TASK-002** Install Docker Desktop, Python 3.11, Node.js LTS, and Git.
  - Done when: each tool's version command runs successfully.
- [x] **TASK-003** Copy `.env.example` to `.env` and fill in local development values.
  - Done when: required settings are present, `.env` is ignored by Git, and no secrets are committed.
- [x] **TASK-004** Run `make up`; confirm PostgreSQL with pgvector and Redis are healthy.
  - Done when: both services report healthy and can be reached locally.
- [x] **TASK-005** Create the backend virtual environment and install dependencies using `pip install -e "backend[dev]"`.
  - Done when: installation succeeds inside the intended Python 3.11 environment.
  - Depends on: TASK-013 (dependencies must match the architecture first).
- [x] **TASK-006** Run the starter API and tests (`make dev`, `/health`, `/docs`, `make test`).
  - Done when: the health endpoint responds, API docs open, and the existing test suite passes. If the starter is incomplete, record the specific blocker instead of marking the task complete.
- [x] **TASK-007** Add or verify `backend/app/core/config.py` (settings loaded from environment variables).
  - Done when: required settings are validated at startup and secrets are not hard-coded.
- [x] **TASK-007b** Add structured logging.
  - Done when: logs are structured and can include `trace_id` and `tenant_id`.
- [x] **TASK-008** Set up Alembic; create the first migration and enable the PostgreSQL `vector` extension.
  - Done when: migrations apply successfully to a clean local database.
- [x] **TASK-009** Create migrations for `tenants`, `users`, and `api_keys`.
  - Done when: tables have the required fields, constraints, and tenant-related indexes defined by the architecture (including `key_prefix`, `key_hash`, `scopes`, `expires_at`, `revoked_at`, `last_used_at`).
- [ ] **TASK-010** Write the first tenant-isolation test.
  - Done when: the test demonstrates that one tenant cannot access another tenant's data. A temporary failure before the feature exists is acceptable during test-first development, but the test must pass before the relevant implementation is considered complete.
- [ ] **TASK-011** Confirm CI runs on push.
  - Done when: GitHub Actions runs the configured checks and reports their results.
- [x] **TASK-012** Verify the local AI runtime and model configuration.
  - Done when: Ollama can run the selected local LLM, and the selected embedding and reranking models can be loaded locally. Record any hardware limitation and use a suitable smaller fallback model, without making a paid service mandatory.
- [ ] **TASK-013** Align the starter files with the finalized architecture.
  - Done when: `backend/pyproject.toml` uses **arq** (not Celery) and includes an argon2 password-hashing library; `.env.example` contains the settings used by the architecture (`LLM_BASE_URL`, `LLM_MODEL_NAME`, `LLM_API_KEY`, embedding and reranker models, thresholds, limits); the `heimdall-rag` skill and `AGENTS.md` use the `X-API-Key` header and arq; `DECISIONS.md` records arq, `X-API-Key`, and Redis fail-closed (503); and no file still mentions Celery.

- [x] **TASK-032** Cleaner (rag/ingestion/cleaner.py) plus tests. Done when whitespace and control characters are normalized, with no injection filtering.
- [x] **TASK-033** Parser (parser.py) plus tests. Done when PDF, TXT, and Markdown are read; PDFs are checked by magic bytes; empty, scanned, and encrypted PDFs fail clearly; page numbers are kept.
- [x] **TASK-034** Chunker (chunker.py) plus tests. Done when chunks follow headings or pages, use settings for size and overlap, and count tokens with the model tokenizer.
- [x] **TASK-035** Separate test database. Done when heimdall_test exists, TEST_DATABASE_URL is used by tests, and tests never touch the dev database.
- [x] **TASK-036** Embedder and storage plus integration tests. Done when chunks are stored with the model name; re-ingesting a document replaces its chunks in one transaction; status changes are saved separately.
- [x] **TASK-037** Pipeline and CLI: init-dev and ingest. Done when ingest samples/hostel_rules.pdf (and the other two) works, and the dev tenant is refused outside ENVIRONMENT=development.
- [ ] **TASK-038** CLI ask. Done when a question gets a cited answer from qwen3:4b with per-step timings (depends on TASK-031).  
## Phase 1: Core RAG API (weeks 1 to 3)
 
Recommended order: 020, 021, 022, 023, 024, 025, 031, 026, 029, 030, 027, 028.
 
- [ ] **TASK-020** Implement signup and login endpoints with password hashing (argon2id) and secure session cookies (HTTP-only, Secure, SameSite).
  - Done when: valid credentials work, invalid credentials are rejected, and passwords are never stored in plaintext.
- [ ] **TASK-021** Implement API-key creation and authentication using the `X-API-Key` header.
  - Done when: keys come from a secure random source, are stored as SHA-256 hashes with a prefix, are shown only once, are compared in constant time, are never logged, and authentication resolves the tenant from the key rather than from caller-supplied tenant IDs.
- [x] **TASK-022** Create migrations for `documents` and `chunks`.
  - Done when: the schema supports tenant ownership, vector embeddings (dimension matching the chosen embedding model), the full-text `tsv` column with a GIN index, document and chunk relationships, the embedding model name, and required indexes.
- [ ] **TASK-023** Implement `POST /v1/documents` with upload validation and background queueing.
  - Done when: PDF, TXT, and Markdown files up to the configured size (default 10 MB) are validated by type (content as well as extension), size, and safe filename handling; accepted uploads receive a trackable status and are queued rather than processed in the request; invalid files get structured errors (413, 422).
- [ ] **TASK-024** Implement the **arq** worker to parse documents, clean and chunk text, create embeddings, and store results.
  - Done when: a queued document is processed end to end; statuses move through `queued`, `processing`, and `ready` or `failed` with a safe error description; retries never create duplicate chunks; and the original file is removed or kept according to the storage setting. Use arq, not Celery or RQ.
- [ ] **TASK-025** Implement document endpoints: `GET /v1/documents`, `GET /v1/documents/{id}`, and `DELETE /v1/documents/{id}`.
  - Done when: users can list, inspect, and delete only their own tenant's documents; deleting a document deletes its chunks; other tenants' documents return 404.
- [ ] **TASK-031** Create the LLM service interface with an Ollama implementation and a fake implementation for tests.
  - Done when: the pipeline calls the LLM only through the interface (`generate()` plus configuration); provider, model, and base URL come from settings; and tests can run without a real model.
- [ ] **TASK-026** Implement `POST /v1/query` with tenant-filtered vector retrieval and cited answers.
  - Done when: the endpoint returns an answer and source references (document, chunk, page), the prompt places retrieved text in delimited context blocks and treats it as untrusted, and all retrieval queries are tenant-scoped inside the database query. Until rate limits and quotas exist (Phase 2), keep this endpoint limited to local development and testing.
- [ ] **TASK-029** Create the first 30 evaluation questions in `evals/datasets/`.
  - Done when: questions include answerable and unanswerable cases, expected answers and source evidence are documented, and the dataset can be reused repeatably.
- [ ] **TASK-030** Implement the baseline evaluation runner (`evals/run_eval.py`) and make `make eval` work.
  - Done when: `make eval` runs the dataset against the current configuration and saves a report in `evals/reports/` with at least Recall@K and abstention accuracy, plus the configuration used.
- [ ] **TASK-027** Implement the evidence threshold and "not found in your documents" guardrail.
  - Done when: weak evidence causes abstention without calling the LLM, the abstention is a normal successful response clearly marked as not found, and the threshold is chosen using `make eval` results rather than arbitrarily. The threshold must be recalibrated when the reranker is added in TASK-066.
- [ ] **TASK-028** Complete isolation tests for documents, chunks, and queries.
  - Done when: cross-tenant access is denied without revealing another tenant's resource, and foreign-tenant resources return 404.
## Phase 2: Tenancy, keys, and limits (weeks 4 to 5)
 
- [ ] **TASK-040** Add API-key scopes (`query`, `documents`, `admin`), expiry, revoke, rotate, last-used tracking, and `GET /v1/keys`, `POST /v1/keys`, `DELETE /v1/keys/{id}`.
  - Done when: revoked and expired keys stop working, scopes are enforced, keys can be listed without exposing secrets, and plaintext keys are never logged or stored.
- [ ] **TASK-041** Enforce the configured maximum number of active keys per tenant (default 5).
  - Done when: key creation beyond the limit is rejected safely and tests cover the limit.
- [ ] **TASK-042** Implement Redis rate limiting per API key and per IP, including login and signup.
  - Done when: excess requests return HTTP 429 with `Retry-After`; rate limiting happens before expensive RAG work; and if Redis is unavailable, query requests fail closed with HTTP 503 rather than bypassing limits.
- [ ] **TASK-043** Record `usage_events` and enforce monthly tenant quotas.
  - Done when: usage is recorded consistently for queries and uploads, and requests over quota are rejected (429) before expensive RAG work.
- [ ] **TASK-044** Implement `GET /v1/usage`.
  - Done when: authenticated tenants can view only their own usage and quota information.
- [ ] **TASK-045** Test limits, quotas, and revoked or expired keys.
  - Done when: success and rejection cases are automated, including the Redis-unavailable 503 behavior and tenant isolation where applicable.
## Phase 3: Tracing and retrieval quality (weeks 6 to 8)
 
- [ ] **TASK-060** Create migrations for `traces`, `spans`, and `feedback`.
  - Done when: records are tenant-scoped and include the fields required for trace inspection and feedback linkage, with time-based indexes.
- [ ] **TASK-061** Implement the failure-safe tracer module (start trace, add span, finish trace).
  - Done when: trace creation and span recording work, and a tracing failure does not fail the main query.
- [ ] **TASK-062** Instrument retrieval, reranking, and generation.
  - Done when: spans record timing, status, retrieved chunk IDs and scores, and available token metadata, without storing full document contents or secrets.
- [ ] **TASK-063** Add the `X-Trace-Id` response header.
  - Done when: each query response includes its trace identifier and it matches the stored trace.
- [ ] **TASK-064** Implement `GET /v1/traces` with filters and pagination, and `GET /v1/traces/{id}`.
  - Done when: results are tenant-scoped and trace details show pipeline steps, timings, and safe error information.
- [ ] **TASK-065** Implement `POST /v1/feedback`.
  - Done when: feedback is validated and linked to a trace belonging to the authenticated tenant.
- [ ] **TASK-066** Implement hybrid retrieval (PostgreSQL full-text keyword search plus vector search), Reciprocal Rank Fusion, and a local cross-encoder reranker.
  - Done when: each retrieval change is evaluated before and after with `make eval`; the report includes Recall@K, retrieval relevance, abstention accuracy, and answer correctness where applicable; and the guardrail threshold is recalibrated.
- [ ] **TASK-067** Test trace isolation and failure-safe tracing.
  - Done when: tenants cannot access other tenants' traces or feedback, and tracing failures do not break queries.
- [ ] **TASK-068** Implement trace retention and safe trace content.
  - Done when: scheduled cleanup deletes traces and spans after the configured period (default 30 days), stored trace data uses chunk IDs and short previews rather than full documents, and cleanup is tested.
- [ ] **TASK-069** Define and record evaluation acceptance criteria.
  - Done when: the evaluation report records the dataset and configuration, and the project has documented thresholds or baseline comparisons for deciding whether a retrieval change improves quality.
## Phase 4: Dashboard (weeks 9 to 11)
 
- [ ] **TASK-080** Scaffold the Next.js app with TypeScript, Tailwind, and the agreed design tokens.
  - Done when: the frontend runs locally and uses the API rather than duplicating backend business logic.
- [ ] **TASK-081** Implement login and signup pages.
  - Done when: successful, failed, and rate-limited states are handled and session behavior is secure.
- [ ] **TASK-082** Implement the API keys page.
  - Done when: users can create, list, revoke, and inspect key metadata; a new secret is shown only once, in a modal with a copy button.
- [ ] **TASK-083** Implement the documents page.
  - Done when: users can upload supported documents, delete documents, and see processing status and safe failure messages.
- [ ] **TASK-084** Implement the usage page with charts and quota information.
  - Done when: displayed data comes from the authenticated tenant's usage endpoint.
- [ ] **TASK-085** Implement the trace list with filters for failures.
  - Done when: users can find their own query traces and filter them usefully.
- [ ] **TASK-086** Implement trace details with a span timeline or waterfall.
  - Done when: retrieval, reranking, and generation steps, timings, and retrieved chunks with scores are inspectable.
- [ ] **TASK-087** Add an end-to-end Playwright test for signup, key creation, upload, query, and trace inspection.
  - Done when: the main user journey passes in a repeatable local test environment (using the fake LLM or a small local model).
- [ ] **TASK-088** Implement a feedback view in the dashboard.
  - Done when: feedback can be inspected in the context of its tenant-scoped trace.
- [ ] **TASK-089** Implement the overview and settings pages.
  - Done when: the overview and settings views listed in the architecture exist, use the API, and show only the authenticated tenant's data.
For every dashboard view, include loading, empty, and error states.
 
## Phase 5: Production hardening (weeks 12 to 14; deployment is optional)
 
- [ ] **TASK-100** Add Dockerfiles and production Compose or platform configuration.
  - Done when: the documented environment can be built reproducibly without relying on undocumented local setup,.
- [ ] **TASK-101** Attempt a preview or demo deployment only if a genuinely free option meets the project's constraints.
  - Done when: deployment instructions and required environment variables are documented, or a short note records why no free host was suitable. Do not require paid infrastructure, a paid API, or a credit card; a complete local run remains the fallback. Document free-host limits (sleeping servers, little RAM, no persistent disk) in the README.
- [ ] **TASK-102** Run a load test with Locust or k6 and publish results.
  - Done when: the scenario, concurrency, environment, and latency and error results are recorded. Use the fake LLM for the load test so it does not overload the local model, and do not claim a performance target unless one has been defined and measured.
- [ ] **TASK-103** Verify file limits, file-type checks, and prompt-injection defenses.
  - Done when: automated tests cover invalid or oversized files and documents containing instructions that attempt to override the system's behavior.
- [ ] **TASK-104** Produce an evaluation report for the default configuration.
  - Done when: the report includes the dataset, model and configuration, metrics, and known limitations.
- [ ] **TASK-105** Complete API documentation, the architecture write-up, and a "how it fails" post.
  - Done when: setup, usage, failure modes, and evaluation results are reproducible from the documentation.
- [ ] **TASK-106** Add monitoring appropriate to the chosen local or demo environment.
  - Done when: documented checks (health endpoint, logs, error visibility) help identify errors and availability issues without requiring paid services.
## Stretch goals (only after the MVP is complete)
 
- [ ] Python SDK (Hofund)
- [ ] Embeddable chat widget
- [ ] Failure clustering
- [ ] Customer-run evaluation
- [ ] Optional per-key IP allowlist
- [ ] ClickHouse trace storage if PostgreSQL becomes insufficient
- [ ] MCP server
## Definition of done for every task
 
Before marking a task complete:
 
1. Understand the requirement and any dependencies.
2. Implement only the intended task; avoid unrelated changes.
3. Run the relevant tests and review the result.
4. Run tenant-isolation tests for new tenant-scoped endpoints and query paths.
5. Run `make eval` before and after changes to chunking, embeddings, retrieval, reranking, thresholds, or prompts.
6. Review the diff for secrets, unrelated edits, and unsafe logging.
7. Commit the change and update `TASKS.md` and `docs/MEMORY.md` with the resulting state.