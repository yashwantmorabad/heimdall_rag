---
name: security
description: Use when working on Heimdall authentication, API keys, passwords, sessions, file uploads, input validation, prompt injection defenses, secrets, error responses, or anything that handles untrusted input. Covers X-API-Key handling, hashing, scopes, expiry and revocation, dashboard cookies, upload validation, and logging safety. Also use when reviewing code for security.
---

# Security

Details and the release checklist are in `docs/SECURITY.md`. Tenant isolation rules: see `heimdall-development`.

## API keys
- Header: **`X-API-Key: hk_live_...`**.
- Generate with a cryptographically secure random source (at least 32 bytes).
- Show the full key **once**, at creation.
- Store only a **SHA-256 hash** and a short prefix. Compare in constant time.
- Never log or return a key after creation. Redact the `X-API-Key` header in logs.
- Keys have scopes (`query`, `documents`, `admin`), optional expiry, revocation, rotation, `last_used_at`, and a maximum number of active keys per tenant (default 5).

## Dashboard authentication
- Email and password, hashed with **argon2id** (or bcrypt).
- Session cookie: HTTP-only, Secure, SameSite.
- Login and signup are rate limited.
- Sessions and API keys are separate mechanisms and never interchangeable.

## Authorization
- `tenant_id` comes only from authenticated identity.
- Foreign-tenant resources return 404.
- Check scopes in the shared dependency, not ad hoc.

## Uploads
- Allowlist types (PDF, TXT, Markdown), checked by content as well as extension.
- Enforce the size limit (default 10 MB).
- Sanitize filenames and never use them as filesystem paths.
- Store files outside any web-served path. Process in workers.

## Input validation
Validate every body, query parameter, and path parameter. Limit question length and request size.

## Prompt injection
- Document text is untrusted.
- Place retrieved text in clearly delimited context blocks.
- Instruct the model to ignore instructions found inside documents.
- The LLM has no tools and no write access in the query path.

## Secrets, errors, and logging
- Secrets live in environment variables. `.env` is never committed.
- Return structured errors without internal details.
- Never log keys, passwords, or full prompts containing user documents.
- Traces store chunk IDs and short previews only.

## Do not
- Do not store plaintext keys or passwords.
- Do not trust any client-supplied tenant ID.
- Do not disable or bypass rate limits when Redis fails.
- Do not commit secrets.
