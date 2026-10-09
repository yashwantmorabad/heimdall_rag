---
name: redis-workers
description: Use when working on Heimdall background jobs or Redis, including arq workers, document processing jobs, job status, retries, rate limiting per API key and IP, monthly quotas, usage events, and behavior when Redis is unavailable. Use whenever adding a background job or a rate limit.
---

# Redis, arq workers, and limits

Tenant isolation rules: see `heimdall-development`.

## Workers (arq)
- Background jobs use **arq**, not Celery or RQ. arq is async like FastAPI, light, and runs on Windows development machines.
- Code lives in `backend/app/workers/`. Jobs call services and `rag/ingestion`; they contain no business logic of their own.
- Upload endpoints validate the file, create the document record (`queued`), enqueue the job, and return. The request never waits for processing.
- Job flow: `processing` -> parse, clean, chunk, embed, store -> `ready`, or `failed` with a short, safe error message.
- Jobs are **idempotent**: a retry must never create duplicate chunks.
- Scheduled cleanup (for example trace retention) also runs as a background job.
- Jobs receive IDs, not document contents, and always carry `tenant_id`.

## Rate limiting
- Limits apply **per API key and per IP address**, and login and signup endpoints are rate limited too.
- Rate limiting and quota checks run **before any expensive RAG work**.
- Exceeding a limit returns HTTP **429** with a `Retry-After` header.

## Quotas and usage
- A monthly query quota per tenant is checked before the pipeline runs.
- Every query and upload records a `usage_events` row (counts, tokens, bytes), so usage numbers match what was actually sent.

## Redis unavailable: fail closed
- If Redis is unavailable, query requests return **HTTP 503** instead of running without limits.
- Never silently skip rate limiting or quota checks.
- Test this: simulate the Redis failure and confirm a 503 and no LLM call.

## Testing
- Test limits (429), quota rejection, and the Redis-down case.
- Test job retries and failures, and that chunks are never duplicated.
- Use the fake LLM so tests stay free and fast.

## Do not
- Do not use Celery or RQ.
- Do not process documents inside the request.
- Do not run RAG work before the limit checks.
- Do not store secrets or full document text in the queue.
