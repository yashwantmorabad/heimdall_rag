---
name: observability
description: Use when working on Heimdall tracing and observability, including traces, spans, the tracer module, instrumenting the RAG pipeline, X-Trace-Id, feedback, trace retention, structured logging, and the trace endpoints. Use whenever adding or changing a pipeline step, because every step needs a span.
---

# Observability

Tenant isolation rules: see `heimdall-development`.

## Model
Every query is a **trace**; each operation inside it is a **span**.
```
Trace: trace_id, tenant_id, status, total latency, spans[]
  retrieval -> reranking -> llm -> result
```

| Span | Records |
|---|---|
| Retrieval | candidate count, method, scores, chunk IDs, latency, status |
| Reranking | input count, final top-k, latency, status |
| LLM | model, token counts when available, latency, status |
| Result | success, abstention, or error; user feedback when available |

## Rules
- **Tracing must never break the main request.** Wrap trace writes so a failure is logged and the request continues.
- Every pipeline step has a span. **When you add a step, add its span in the same change.**
- Store chunk IDs and short previews, **not** full document text. Never store secrets.
- Return the trace ID in the `X-Trace-Id` response header, matching the stored trace.
- All trace, span, and feedback data is tenant-scoped, and other tenants' traces return 404.
- Retention: delete traces and spans after the configured period (default 30 days), with scheduled cleanup.
- Logs are structured and include `trace_id` and `tenant_id` where available.

## Endpoints
- `GET /v1/traces` with filters (for example failures) and pagination
- `GET /v1/traces/{id}` with steps, timings, and safe error information
- `POST /v1/feedback`, linked to a trace owned by the authenticated tenant

## Testing
- A trace with retrieval, reranking, and LLM spans is created per query.
- Simulated tracing failure does not fail the query.
- Trace isolation between tenants.
- Retention cleanup removes only expired data.

## Do not
- Do not let tracing raise into the request path.
- Do not store full documents or prompts in traces.
- Do not expose another tenant's trace data.
