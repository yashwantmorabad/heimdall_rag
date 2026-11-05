# Project Memory
 
> Records the actual current state of Heimdall. Update this file after every task. Permanent architecture decisions belong in `DECISIONS.md`.
 
## Current Status

**Terminal RAG plan: Stage 1 (Ingestion) COMPLETE. Stage 2 (`ask`) COMPLETE.**

Stage 1 is a five-step assembly line in `backend/app/rag/ingestion/`:

`FILE -> parse -> clean -> chunk -> embed -> store (PostgreSQL)`

| Step | File | What it does |
|---|---|---|
| Parse | `parsers.py` | Reads PDF (PyMuPDF), TXT, Markdown and returns pages with page numbers |
| Clean | `cleaner.py` | Strips control characters, collapses whitespace, trims ends |
| Chunk | `chunker.py` | Structure-aware: headings (Markdown), pages (PDF), sliding window (TXT) |
| Embed | `embedder.py` | `nomic-embed-text` (768 dimensions); adds the embedding and the model name to each chunk |
| Store | `pipeline.py` (TXN 2) | Deletes old chunks, inserts new ones in one transaction, scoped by `tenant_id` |
| Orchestrate | `pipeline.py` | Runs the steps in order with 3 transactions: create doc → replace chunks → update status |

Command: `python -m app.cli ingest <file> --tenant-id <id>`

Stage 2 (`ask`) is a four-step pipeline:

`QUESTION -> embed (search_query:) -> vector search (tenant_id filter) -> prompt + LLM -> answer + citations`

| Step | File | What it does |
|---|---|---|
| Embed | `embedder.py` | `embed_queries()` with `search_query:` prefix via Ollama `nomic-embed-text` |
| Search | `vector_search.py` | Cosine distance `<=>` with `WHERE tenant_id = ...` in SQL |
| Prompt | `prompt.py` | Numbered `[Source N]` blocks, 4-chunk cap, citation extraction |
| LLM | `llm.py` | `OllamaLLM` (qwen3:4b, 120s timeout, think=false) or `FakeLLM` for tests |

Command: `python -m app.cli ask "<question>" --tenant-id <id>`

Tests: 50 unit tests and 7 integration tests passing (re-run `python -m pytest -q` from `backend` to confirm).

Environment is set up: Docker (PostgreSQL + pgvector, Redis, ports bound to localhost only), Alembic migrations 0001 to 1c7b70d692aa applied (unique constraint on documents.tenant_id + filename), Ollama running `qwen3:4b` (about 3.2 GB, 100% GPU, thinking off, context 4096), embedding and reranker models cached on `E:\ai\hf-cache`. Sample documents are in `samples/` and 26 sample questions (21 answerable, 5 not) are in `evals/datasets/sample_questions.jsonl`.

Working mode: opencode is used as a read-only tutor. It shows code in the chat and I type it myself. One stage at a time.
 
## Completed

- Setup: Docker, Ollama with `qwen3:4b`, embedding and reranker models, Alembic, migrations 0001 to 0003 (tenants, users, api_keys, documents, chunks)
- Stage 1 ingestion pipeline (parse, clean, chunk, embed, store) and the CLI `ingest` command, with unit and integration tests
- Sample documents and a 26-question sample set
- Stage 2 Piece 1: LLM service interface (OllamaLLM + FakeLLM) in backend/app/rag/generation/llm.py
- Stage 2 Piece 2: Tenant-scoped vector retrieval in backend/app/rag/retrieval/vector_search.py
- Stage 2 Piece 3: Prompt builder (build_prompt, generate_answer) in backend/app/rag/generation/prompt.py with numbered source blocks, citation extraction, 4-chunk token budget
- Stage 2 Piece 4: CLI `ask` command in backend/app/cli.py with two subcommands (ingest, ask), per-step timings
- Stage 2 Piece 5: Tests — tenant isolation (tests/isolation), prompt builder unit tests (tests/unit/rag/test_prompt.py), full ask flow integration (tests/integration/test_ask_flow.py)
- Stage 2 Piece 6: Manual try-out — 6 questions from sample_questions.jsonl (4 answered, 2 correctly abstained)
## Current Task

Stage 2 COMPLETE. Next: Stage 3 (Evaluation Runner).

The API upload flow (TASKS 020, 021, 023, 024, 025) is deliberately postponed and will start in a fresh session after the terminal RAG stages.
 
## Known Issues and Blockers

- Structured logging (part of TASK-007) is not implemented yet.
- CI (TASK-011) is not confirmed: check that `.github/workflows` exists and has run on GitHub.
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

1. Stage 3: evaluation on the 26 sample questions (TASKS 029, 030) — implement `evals/run_eval.py` and `make eval`.
2. Stage 4: "not found" guardrail (027) — evidence threshold calibrated from eval results.
3. Stage 5: hybrid retrieval (keyword search + vector search + RRF + reranker) (066).
4. Later, in a fresh session: API keys (020, 021), upload endpoint and arq worker (023, 024), document endpoints (025).
## Memory Update Rules
 
- Update the current status, current task, completed work, known issues, and next step after every task.
- Record only work that has actually been completed and verified.
- Remove resolved issues and pending items rather than leaving stale information.
- Check architecture-related statements against `ARCHITECTURE.md` and permanent decisions against `DECISIONS.md`.
- Do not duplicate the full task list or permanent architecture decisions here.
- Update the last-updated date whenever this file changes.
**Last updated:** 2026-11-05