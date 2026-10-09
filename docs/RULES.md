# Development Rules

These rules apply to every human and AI contribution. AI agents must read this file, PRD.md, ARCHITECTURE.md, SECURITY.md, and TASKS.md before changing code.

## General
- Python 3.11+ with type hints; TypeScript (strict) in the frontend.
- Reuse existing functions and components before creating new ones.
- Keep functions small and single-purpose.
- Do not modify unrelated files.
- Do not add a new dependency without a reason noted in DECISIONS.md.
- Do not leave dead code, debug prints, or commented-out blocks.

## Before coding
1. Read the relevant docs in `docs/`.
2. Inspect the existing implementation.
3. For changes touching more than two files, write a short plan first and wait for approval.

## Backend
- Endpoints in `api/v1/` stay thin; logic goes in `services/` and `rag/`.
- Validate all input with Pydantic schemas.
- Every query on tenant-owned data filters by `tenant_id` in SQL.
- `tenant_id` is never read from the request body or query string.
- Schema changes use Alembic migrations only.
- Return consistent error responses (code, message, trace_id when available).
- Never log API keys, passwords, or full prompts containing user documents.

## RAG pipeline
- Chunking, embedding, retrieval, rerank, threshold, and prompt changes require an evaluation run before and after (`make eval`), with both results reported.
- The similarity threshold lives in settings, not code.
- Do not call the LLM when retrieval is below the threshold.
- Treat document text as untrusted input.

## Tracing
- Every pipeline step has a span; new steps add spans in the same change.
- Tracing must never raise into the request path.

## Frontend
- Follow DESIGN.md.
- Include loading, empty, and error states for every data view.
- Keep API calls in `frontend/lib/`, not inside components.

## Testing
- Add tests for important behavior.
- Every new endpoint or query path gets an isolation test.
- Run lint, type checks, and tests after each change; fix failures before continuing.

## Git
- Small commits with descriptive messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- One branch per feature (`feature/auth`, `feature/ingestion`, `fix/rate-limit`).
- Never commit `.env` or any secret.

## The loop for every task
1. READ the relevant docs
2. UNDERSTAND the current code
3. PLAN
4. IMPLEMENT
5. TEST
6. REVIEW
7. FIX
8. COMMIT
9. UPDATE docs (TASKS.md, MEMORY.md, DECISIONS.md as needed)

## Reporting format
After finishing a task, report:
1. Files changed
2. What was implemented
3. Tests and checks run, with results
4. Evaluation numbers (if retrieval or prompts changed)
5. Remaining issues
