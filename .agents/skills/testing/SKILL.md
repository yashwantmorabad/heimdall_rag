---
name: testing
description: Use when writing, running, or fixing tests in Heimdall, including pytest unit, integration, and tenant-isolation tests, fake LLM tests, rate limit and Redis-outage tests, upload and prompt-injection tests, Playwright end-to-end tests, and RAG evaluation runs. Use before marking any task complete.
---

# Testing

## Layout
```
backend/tests/
  unit/          small isolated tests
  integration/   tests with a real database and Redis
  isolation/     cross-tenant access tests
evals/           RAG quality evaluation (separate from software tests)
```
Commands: `make test`, `make test-isolation`, `make lint`, `make eval`.

## Tenant isolation (blocks merging)
Create two tenants with their own keys and data. Confirm tenant B cannot:
- list, read, or delete tenant A's documents (404)
- retrieve A's chunks through `/v1/query`
- read A's traces, spans, usage, or feedback
- use A's key after revocation
- pass a `tenant_id` in a body or query string to reach A's data

Every new tenant-scoped endpoint or query path gets an isolation test.

## Always use the fake LLM in tests
Tests and load tests use the fake implementation behind the LLM service interface, so they are fast, free, and repeatable. Never depend on a real model or paid API in automated tests.

## What to cover
- **Authentication:** missing, invalid, expired, and revoked keys; scope enforcement; active-key limit.
- **Limits:** 429 with `Retry-After` for rate limits and quotas.
- **Redis outage:** simulate it and confirm query requests return 503 and make no LLM call.
- **Uploads:** wrong type, oversized file, bad filename, corrupt file (document becomes `failed`), retry creates no duplicate chunks.
- **Query:** cited answer, "not found" with no LLM call, empty tenant.
- **Prompt injection:** a document containing instructions must be placed in delimited context. With a fake LLM this proves the prompt is built safely; how a real model behaves is measured in evaluation runs, not in CI.
- **Tracing:** every query creates a trace with spans; a tracing failure does not fail the query; `X-Trace-Id` matches the stored trace.
- **Migrations:** apply cleanly to an empty database.

## Evaluation (separate from software tests)
Run `make eval` before and after changes to chunking, embeddings, retrieval, reranking, thresholds, or prompts. Report Recall@K, retrieval relevance, abstention accuracy, and answer correctness.

## End to end (Phase 4)
Playwright: sign up, create a key, upload a document, ask a question, open the trace.

## Habits
- Run the relevant tests after each change and fix failures before continuing.
- Do not skip or weaken a test to make a change pass.
- Keep test data small and local.
