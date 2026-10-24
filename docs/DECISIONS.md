# Architecture Decisions

This document records permanent architecture and technology decisions for Heimdall. Each decision includes its status and reasoning. Do not silently change an accepted decision; document significant changes in a new ADR (Architecture Decision Record).

**Status values:** `Proposed`, `Accepted`, `Deprecated`, `Superseded`

## ADR-001: FastAPI for the Backend

**Status:** Accepted

**Decision:** Use FastAPI to build the backend API.

**Reason:** Python fits the AI and ML ecosystem, and FastAPI provides request validation, asynchronous support, and automatic API documentation.

**Consequences:** Keep API endpoints thin. Put business logic in services and RAG logic in the appropriate RAG modules.

## ADR-002: PostgreSQL with pgvector Instead of a Separate Vector Database

**Status:** Accepted

**Decision:** Use PostgreSQL with the pgvector extension for relational data and vector storage.

**Reason:** A single database simplifies transactions, tenant filtering, and operations while the project is small.

**Consequences:** Benchmark retrieval performance as the dataset grows. Consider a separate vector database only if measurements demonstrate a clear need.

## ADR-003: PostgreSQL Full-Text Search for Keyword Retrieval

**Status:** Accepted

**Decision:** Use PostgreSQL full-text search with `tsvector` and a GIN index for keyword retrieval.

**Reason:** This avoids introducing a separate search engine and allows keyword and vector retrieval to work within the same database.

**Consequences:** Evaluate keyword retrieval as part of the RAG evaluation process. Consider a dedicated search engine or BM25 implementation only if evaluation demonstrates a meaningful improvement is needed.

## ADR-004: arq with Redis for Background Jobs

**Status:** Accepted

**Decision:** Use arq with Redis for asynchronous background jobs, including document processing and ingestion.

**Reason:** arq provides a lightweight asynchronous job queue that fits the Python and FastAPI stack and the project's local-first approach.

**Consequences:**
- Document ingestion must run in background workers rather than performing the entire process inside the API request.
- Jobs must be designed for safe retries and idempotent processing.
- Redis and arq must be configured and tested as part of the development environment.
- Do not introduce Celery or RQ without a documented architecture review and an approved decision.

## ADR-005: Separate Authentication for Dashboard Users and API Clients

**Status:** Accepted

**Decision:** Use two authentication mechanisms:

- **Dashboard users:** Authenticate with email and password, using Argon2id password hashing and an HTTP-only session cookie with appropriate security settings.
- **API clients:** Authenticate using securely generated API keys sent through the `X-API-Key` HTTP header. Store only a cryptographic hash of each API key, never its plaintext value.

**Reason:** Browser-based dashboard sessions and programmatic API access have different security and usability requirements.

**Consequences:**
- API keys must be shown only once when created.
- Support key scopes, expiration, revocation, rotation, and last-used tracking.
- Never log passwords, API keys, or other secrets.
- Derive the tenant identity from authenticated credentials, never from a request-supplied `tenant_id`.
- Use IP addresses for rate limiting and optional IP allowlists, never as the tenant's identity.
- Return consistent authentication errors without revealing sensitive details.

## ADR-006: Store Traces in PostgreSQL Initially

**Status:** Accepted

**Decision:** Store query traces, spans, and related observability metadata in PostgreSQL initially.

**Reason:** PostgreSQL is already part of the stack, making it the simplest option while trace volume is manageable.

**Consequences:**
- Apply tenant isolation and appropriate retention rules to trace data.
- Store chunk identifiers and short evidence previews rather than full document contents.
- Ensure tracing failures never break the main API request.
- Consider ClickHouse or another analytical store only if measured query performance or storage volume justifies the added complexity.

## ADR-007: Strict Evidence-Based Answering by Default

**Status:** Accepted

**Decision:** Answers must be grounded in the authenticated tenant's retrieved documents by default. If the retrieved evidence is insufficient, the API must abstain rather than generate an unsupported answer.

**Reason:** Heimdall is a document-grounded RAG service. Avoiding unsupported answers is more important than answering every question.

**Consequences:**
- Do not call the LLM when retrieval evidence falls below the configured acceptance threshold.
- Keep the threshold in application settings rather than hardcoding it throughout the codebase.
- Calibrate and validate the threshold using a representative evaluation dataset.
- Measure abstention accuracy, retrieval relevance, and answer correctness.
- A future hybrid mode that includes clearly labeled general knowledge requires a separate documented decision.

## ADR-008: Return 404 for Resources Owned by Other Tenants

**Status:** Accepted

**Decision:** Return `404 Not Found` when an authenticated tenant attempts to access a resource belonging to another tenant.

**Reason:** This avoids revealing whether another tenant's resource exists.

**Consequences:**
- Apply tenant filters to every query involving tenant-owned data.
- Test cross-tenant access for every new tenant-scoped endpoint and query path.
- Never rely only on frontend checks for tenant isolation.

## ADR-009: Store the Embedding Model Name with Each Chunk

**Status:** Accepted

**Decision:** Store the embedding model identifier with chunk embedding data.

**Reason:** Embeddings generated by different models may have incompatible dimensions or vector spaces. Recording the model helps prevent incompatible embeddings from being mixed during retrieval.

**Consequences:**
- Record the embedding model used to create each stored embedding.
- Ensure query embeddings are compatible with the indexed document embeddings.
- Use a controlled re-embedding or re-indexing process when changing models.
- Do not mix incompatible embedding models in the same retrieval index.

## ADR-010: Evaluate Retrieval Changes Before and After

**Status:** Accepted

**Decision:** Run RAG evaluations before and after changes that can affect retrieval or answer quality.

**Reason:** Retrieval quality and reliable evidence-grounded answers are central to Heimdall's purpose.

**Consequences:**
- Evaluate changes to chunking, embedding models, retrieval, hybrid-search weighting, reranking, similarity thresholds, and prompts.
- Record the evaluation dataset, relevant configuration, and before-and-after results.
- Track suitable metrics, including Recall@K, retrieval relevance, abstention accuracy, and answer correctness.
- Do not treat passing software tests as proof that RAG quality has improved or remained stable.

---
## ADR-011: Fail Closed on Redis Unavailability

**Status:** Accepted

**Decision:** When Redis is unavailable, query requests return HTTP 503 rather than bypassing rate limits and quotas.

**Reason:** Rate limiting and quota enforcement protect the local LLM from overload. Bypassing them when Redis is down would allow unlimited requests to reach the model, risking resource exhaustion. Failing closed is the safer default.

**Consequences:**
- All rate limit and quota checks must be enforced before expensive RAG work.
- If Redis is down, the query endpoint returns 503 with a clear error.
- This behavior must be tested explicitly (see TASK-042, TASK-045).
- The choice can be revisited in a future ADR if operational experience shows it is too strict.

## Changing an Accepted Decision

When a significant architecture decision needs to change:

1. Explain the problem with the existing decision.
2. Gather evidence, benchmarks, or evaluation results where applicable.
3. Propose the replacement decision and its trade-offs.
4. Obtain approval before implementing the architecture change.
5. Record the change in a new ADR and mark the previous decision as `Superseded` or `Deprecated` where appropriate.

Do not silently change accepted architecture decisions or introduce conflicting technology choices in code or documentation.