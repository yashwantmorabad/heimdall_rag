---
name: backend-development
description: Use when writing or changing FastAPI code in backend/app for Heimdall, including endpoints, request and response schemas, services, settings, authentication dependencies, error handling, and logging. Covers layering, /v1 API conventions, the X-API-Key header, status codes, the error format, and structured logs. Also use when adding or changing any public API endpoint.
---

# Backend development

Tenant isolation rules: see `heimdall-development`.

## Layering
```
api/v1/ (thin)  ->  services/ or rag/  ->  db/
```
- Endpoints receive the request, call a service, and return a schema. No business logic and no raw SQL in endpoint files.
- `api/deps.py` handles authentication and tenant resolution, shared by all endpoints.
- Services hold business rules (keys, usage, quotas). The RAG pipeline lives in `rag/`.
- Reuse existing functions before writing new ones. Keep functions small.

## API conventions
- All public endpoints are under `/v1/`. Breaking changes need a new version.
- Planned endpoints:
  - `POST/GET /v1/documents`, `GET/DELETE /v1/documents/{id}`
  - `POST /v1/query`
  - `GET/POST /v1/keys`, `DELETE /v1/keys/{id}`
  - `GET /v1/traces`, `GET /v1/traces/{id}`, `POST /v1/feedback`
  - `GET /v1/usage`
- Validate every body, query parameter, and path parameter with Pydantic schemas. Limit question length and request size.
- List endpoints support pagination and filters, and are tenant-scoped.
- Query responses include sources and the `X-Trace-Id` header.
- An abstention ("not found in your documents") is a normal successful response, clearly marked.

## Authentication
- Programs send **`X-API-Key: hk_live_...`**. Dashboard users use a session cookie. The two are never interchangeable.
- Resolve the tenant in `deps.py`. Check scopes (`query`, `documents`, `admin`), expiry, and revocation there.
- Routes that need a scope declare it; do not check scopes ad hoc inside services.

## Errors
Return structured errors: `code`, `message`, and `trace_id` when available. Never expose internal details or secrets.

| Status | Meaning |
|---|---|
| 400 | invalid request |
| 401 | authentication failure |
| 403 | forbidden (scope missing) |
| 404 | not found, including other tenants' resources |
| 409 | conflict |
| 413 | file too large |
| 422 | validation error |
| 429 | rate limit or quota exceeded (with `Retry-After`) |
| 500 | internal error |
| 503 | service unavailable (for example Redis down on query requests) |

## Settings and logging
- All settings come from environment variables through `core/config.py`, validated at startup. No hard-coded secrets.
- Logs are structured and include `trace_id` and `tenant_id` where available. Never log API keys, passwords, or full prompts containing user documents. Redact the `X-API-Key` header.

## Do not
- Do not read `tenant_id` from the client.
- Do not put business logic in endpoints.
- Do not return stack traces to clients.
- Do not add a dependency without a reason, especially a heavy one.
