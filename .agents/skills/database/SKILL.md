---
name: database
description: Use when creating or changing PostgreSQL tables, Alembic migrations, indexes, pgvector columns, full-text search columns, or SQL queries in Heimdall. Covers the schema, tenant_id rules, vector and keyword search queries, deletion cascades, and retention. Also use when writing any query on tenant-owned data.
---

# Database

Tenant isolation rules: see `heimdall-development`.

## Rules
- PostgreSQL 16 with pgvector. Async SQLAlchemy with asyncpg.
- **Schema changes use Alembic migrations only.** Never edit the database by hand. The first migration enables the `vector` extension.
- Every tenant-owned table has `tenant_id NOT NULL` and an index on it.
- Migrations must apply cleanly to an empty database.
- Add time-based indexes for traces and usage events (supports queries and retention cleanup).

## Main tables
| Table | Key columns |
|---|---|
| `tenants` | id, name, created_at |
| `users` | id, tenant_id, email, password_hash |
| `api_keys` | id, tenant_id, name, key_prefix, key_hash, scopes, expires_at, revoked_at, last_used_at |
| `documents` | id, tenant_id, filename, status, error, created_at |
| `chunks` | id, tenant_id, document_id, content, chunk_index, embedding, embedding_model, tsv, created_at |
| `usage_events` | id, tenant_id, api_key_id, kind, tokens, bytes, created_at |
| `traces` | id, tenant_id, status, latency_ms, question_preview, created_at |
| `spans` | id, trace_id, tenant_id, name, duration_ms, status, attributes |
| `feedback` | id, trace_id, tenant_id, rating, comment |

Document statuses: `queued`, `processing`, `ready`, `failed`.

## Chunks and vectors
- The `embedding` column dimension **must match** the embedding model (384 for `BAAI/bge-small-en-v1.5`).
- Store `embedding_model` with every chunk. Never mix vectors from different models in one search.
- `tsv` is a `tsvector` column with a GIN index for keyword search.
- Deleting a document deletes its chunks (use a foreign key with cascade delete).

## Tenant-scoped queries
Filter inside the query, never afterwards:
```sql
-- vector search
SELECT id, content, embedding <=> :query_embedding AS distance
FROM chunks
WHERE tenant_id = :tenant_id
ORDER BY embedding <=> :query_embedding
LIMIT :k;

-- keyword search
SELECT id, content, ts_rank(tsv, plainto_tsquery('english', :q)) AS rank
FROM chunks
WHERE tenant_id = :tenant_id AND tsv @@ plainto_tsquery('english', :q)
ORDER BY rank DESC
LIMIT :k;
```
Approximate vector indexes can return fewer rows when combined with a filter, so measure retrieval quality with `make eval` before and after adding or changing a vector index.

## Retention
- Traces and spans are deleted after the configured period (default 30 days), by scheduled cleanup.
- Traces store chunk IDs and short previews, not full document text.

## Do not
- Do not filter by tenant after the database call.
- Do not store raw API keys or plaintext passwords.
- Do not change the embedding model or dimension without a re-index plan and an Alembic migration.
- Do not write raw SQL in endpoint files.
