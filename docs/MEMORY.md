# Project Memory
 
> Records the actual current state of Heimdall. Update this file after every task. Permanent architecture decisions belong in `DECISIONS.md`.
 
## Current Status

**Terminal RAG plan: Stage 1 (Ingestion) COMPLETE. Stage 2 (`ask`) is next.**

Stage 1 is a five-step assembly line in `backend/app/rag/ingestion/`:

`FILE -> parse -> clean -> chunk -> embed -> store (PostgreSQL)`

| Step | File | What it does |
|---|---|---|
| Parse | `parsers.py` | Reads PDF (PyMuPDF), TXT, Markdown and returns pages with page numbers |
| Clean | `cleaner.py` | Strips control characters, collapses whitespace, trims ends |
| Chunk | `chunker.py` | Structure-aware: headings (Markdown), pages (PDF), sliding window (TXT) |
| Embed | `embedder.py` | `BAAI/bge-small-en-v1.5` (384 dimensions); adds the embedding and the model name to each chunk |
| Store | `pipeline.py` (TXN 2) | Deletes old chunks, inserts new ones in one transaction, scoped by `tenant_id` |
| Orchestrate | `pipeline.py` | Runs the steps in order with 3 transactions: create doc → replace chunks → update status |

Command: `python -m app.cli ingest <file> --tenant-id <id>`

Tests: 38 unit tests and 3 integration tests passing (re-run `python -m pytest -q` from `backend` to confirm before relying on these numbers).

Environment is set up: Docker (PostgreSQL + pgvector, Redis, ports bound to localhost only), Alembic migrations 0001 to 1c7b70d692aa applied (unique constraint on documents.tenant_id + filename), Ollama running `qwen3:4b` (about 3.2 GB, 100% GPU, thinking off, context 4096), embedding and reranker models cached on `E:\ai\hf-cache`. Sample documents are in `samples/` and 26 sample questions (21 answerable, 5 not) are in `evals/datasets/sample_questions.jsonl`.

Working mode: opencode is used as a read-only tutor. It shows code in the chat and I type it myself. One stage at a time.
 
## Completed
 
- Setup: Docker, Ollama with `qwen3:4b`, embedding and reranker models, Alembic, migrations 0001 to 0003 (tenants, users, api_keys, documents, chunks)
- Stage 1 ingestion pipeline (parse, clean, chunk, embed, store) and the CLI `ingest` command, with unit and integration tests
- Sample documents and a 26-question sample set
## Current Task

TASK-031: LLM service interface (first piece of Stage 2, the terminal ask command).
 
Stage 2 goal: `python -m app.cli ask "<question>"` embeds the question, searches chunks for the dev tenant only (tenant filter inside the SQL query), asks `qwen3:4b`, and prints the answer with sources and per-step timings (TASK-038). The first real tenant-isolation test (TASK-010) is written in this stage.
 
The API upload flow (TASKS 020, 021, 023, 024, 025) is deliberately postponed and will start in a fresh session after the terminal RAG stages.
 
## Known Issues and Blockers

- Structured logging (part of TASK-007) is not implemented yet.
- CI (TASK-011) is not confirmed: check that `.github/workflows` exists and has run on GitHub.
- The real tenant-isolation test (TASK-010) is not written yet; it is part of Stage 2.
- Node.js is not installed or checked (needed in Phase 4).
- Windows Application Control blocks `.exe` launchers: always use `python -m ...` (pip, pytest, uvicorn, alembic, arq).
- `make` is not available on Windows; run the commands directly.
- Harmless: httpx deprecation warning in tests, Hugging Face symlink warning, LF/CRLF Git warnings.
- First Ollama response takes 25 to 35 seconds while the model loads.

Test-database guard is too loose (accepts names that don't end in _test). Fix later; not a blocker.
## Pending Documentation Updates
 
The following finalized architecture decisions must be confirmed in `DECISIONS.md`:
 
- Background jobs use **arq with Redis**, not Celery or RQ.
- Programmatic API authentication uses the **`X-API-Key`** header.
- If Redis is unavailable, query requests fail closed with **HTTP 503** rather than bypassing rate limits.
Also update `TASKS.md`: tick TASK-022 and the Stage 1 tasks, and keep TASK-010 and TASK-011 unticked until their real work is done.
 
Remove each item from this section once it has been recorded and checked.
 
## Open Questions
 
- Which free hosting option, if any, will be used for the public demo? Verify its current free-tier limits before choosing.
## Next Step
 
1. Stage 2 (terminal `ask`): LLM interface (031), retrieval, prompt and answer, the `ask` command (038), tests including the first real tenant-isolation test (010), then try about 6 sample questions.
2. Stage 3: evaluation on the 26 sample questions (TASKS 029, 030).
3. Stage 4: "not found" guardrail (027). Stages 5 and 6: keyword search with rank fusion, then the reranker (066).
4. Later, in a fresh session: API keys (020, 021), upload endpoint and arq worker (023, 024), document endpoints (025).
## Memory Update Rules
 
- Update the current status, current task, completed work, known issues, and next step after every task.
- Record only work that has actually been completed and verified.
- Remove resolved issues and pending items rather than leaving stale information.
- Check architecture-related statements against `ARCHITECTURE.md` and permanent decisions against `DECISIONS.md`.
- Do not duplicate the full task list or permanent architecture decisions here.
- Update the last-updated date whenever this file changes.
**Last updated:** 2026-10-24