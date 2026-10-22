# Project Memory

> Records the actual current state of Heimdall. Update this file after every task. Permanent architecture decisions belong in `DECISIONS.md`.

## Current Status

**Phase 1 (Core RAG API) — Stage 1 Ingestion: COMPLETE.**

The terminal ingestion tool is fully implemented and tested:
- `backend/app/rag/ingestion/` — cleaner, parsers (PDF/TXT/MD), chunker, embedder, store, pipeline
- `backend/app/cli.py` — CLI command `python -m app.cli ingest <file> --tenant-id`
- 28 unit tests + 2 integration tests passing
- Idempotent, tenant-isolated, structure-aware chunking, BAAI/bge-small-en-v1.5 embeddings

Docker (PostgreSQL + pgvector, Redis) running. Migrations 0001-0003 applied.

## Completed

- Stage 1 ingestion pipeline: parse → clean → chunk → embed → store (7 modules)
- Terminal CLI ingestion tool with tenant_id parameter
- Unit tests (28) and integration tests (2) for all ingestion components

**Verification required:** Confirm that every listed document exists and has been reviewed and finalized. Do not mark a document complete merely because an initial draft exists.

## Current Task

**TASK-023:** Implement `POST /v1/documents` with upload validation and background queueing.

Stage 1 ingestion (terminal tool) is complete. Next: API endpoint for document upload and arq background worker.

## Known Issues and Blockers

- No issues have been confirmed yet.
- Recheck the repository, configuration, and documentation before reporting that there are no known issues.
- Record newly discovered issues and blockers here, and update them when resolved.

## Pending Documentation Updates

The following finalized architecture decisions must be confirmed in `DECISIONS.md`:

- Background jobs use **arq with Redis**, not Celery or RQ.
- Programmatic API authentication uses the **`X-API-Key`** header.
- If Redis is unavailable, query requests fail closed with **HTTP 503** rather than bypassing rate limits.

Until these decisions are recorded and verified in `DECISIONS.md`, keep them listed as pending documentation updates. Remove each item from this section once it has been recorded and checked.

## Open Questions

- Which local Ollama model will be used for development?
- Which free hosting option, if any, will be used for the public demo? Verify its current free-tier limits before choosing.
- Confirm the embedding configuration against `ARCHITECTURE.md`. The current architecture specifies `BAAI/bge-small-en-v1.5` with 384 dimensions; do not treat this as undecided unless the architecture itself changes.

## Next Step

1. Implement `POST /v1/documents` API endpoint (TASK-023) — file upload validation, document record creation, queue to arq.
2. Implement arq worker (TASK-024) — uses the existing ingestion pipeline.
3. Implement document CRUD endpoints (TASK-025).
4. Continue Phase 1 tasks in recommended order.

## Memory Update Rules

- Update the current status, current task, completed work, known issues, and next step after every task.
- Record only work that has actually been completed and verified.
- Remove resolved issues and pending items rather than leaving stale information.
- Check architecture-related statements against `ARCHITECTURE.md` and permanent decisions against `DECISIONS.md`.
- Do not duplicate the full task list or permanent architecture decisions here.
- Update the last-updated date whenever this file changes.

**Last updated:**  2026-10-22