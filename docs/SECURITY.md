# Security Requirements

Security is built in from the start, not added before deployment.
These requirements apply throughout development, testing, and deployment.

## Authentication

- Dashboard authentication uses email and password.
- Hash passwords with Argon2id; bcrypt is an acceptable alternative
  only if explicitly approved and documented.
- Use HTTP-only, Secure, SameSite session cookies.
- Protect signup and login endpoints with rate limiting.
- API authentication uses the `X-API-Key` header.
- Require HTTPS for API-key authentication outside local development.
- Never accept tenant identity directly from the request body,
  query string, or other caller-controlled input.

## API Keys

- Generate keys using a cryptographically secure random source
  with at least 32 bytes of randomness.
- Show the complete key only once, immediately after creation.
- Store only the SHA-256 hash and a short, non-secret key prefix.
- Compare key hashes using a constant-time comparison.
- Support scopes, expiry, revocation, and rotation.
- Track `last_used_at` without recording the full key.
- Never log, expose in error messages, or return a key again
  after its initial creation response.
- Enforce the configured maximum number of active keys per tenant.
- Never commit API keys or other secrets to Git.

## Authorization and Tenant Isolation

- Every tenant-owned table must have a `tenant_id NOT NULL`
  column, as defined by the architecture.
- Every query involving tenant-owned data must enforce tenant
  isolation in SQL.
- Derive `tenant_id` exclusively from the authenticated API key
  or dashboard session.
- Never trust a tenant ID supplied by the caller.
- Return HTTP 404 for resources belonging to another tenant.
- Apply tenant isolation to documents, chunks, traces, spans,
  feedback, usage events, API keys, and all other tenant-owned data.
- Every new tenant-scoped endpoint and query path must have
  an isolation test.
- Run tenant-isolation tests in CI.
- Verify that background jobs preserve tenant ownership and
  cannot process or modify another tenant's data.

## Input Validation and Resource Limits

- Validate request bodies, query parameters, and path parameters
  using appropriate Pydantic schemas.
- Enforce question-length, request-size, and other configured
  input limits.
- Reject malformed input with structured error responses.
- Apply rate limits and monthly quotas before expensive RAG work.
- If Redis is unavailable for protected query requests, fail closed
  with HTTP 503 rather than bypassing rate limits.
- Never allow an unavailable rate-limiting service to silently
  disable security controls.

## File Upload Security

Validate every uploaded file using the following requirements:

- Allow only supported file types: PDF, TXT, and Markdown.
- Check file content as well as the filename extension.
- Enforce the configured file-size limit (10 MB by default).
- Sanitize filenames and never use an uploaded filename directly
  as a filesystem path.
- Store uploaded files outside the web root.
- Do not execute uploaded files or treat them as trusted code.
- Process documents in background workers rather than inside
  the upload request.
- Return structured errors for invalid or oversized files.
- Prevent path traversal and unsafe file access.
- Apply resource limits to document processing, including
  processing time and the number of concurrent jobs.
- Handle worker retries idempotently to avoid duplicate chunks
  or unintended repeated processing.

### Deletion and Background Jobs

- Deleting a document must remove its associated chunks and
  embeddings, along with any other document-derived data covered
  by the deletion policy.
- Ensure queued or in-progress jobs cannot recreate chunks for
  a document that has already been deleted.
- Handle deletion and ingestion races safely.
- Test that deletion removes the expected data and that retries
  cannot restore deleted content.
- Follow the configured policy for retaining or removing the
  original uploaded file.

## Prompt Injection and Untrusted Content

- Treat all uploaded and retrieved document text as untrusted input.
- Place retrieved text inside clearly delimited context blocks.
- Instruct the model to answer from the supplied evidence and
  ignore instructions embedded in retrieved documents.
- Do not treat retrieved content as system instructions.
- The query-path LLM must not have tools, filesystem write access,
  or other capabilities that could execute document instructions.
- If retrieved evidence is too weak, abstain without calling the LLM.
- Maintain adversarial test documents covering prompt injection,
  instruction overrides, misleading content, and unanswerable
  questions.
- Run these tests when changing prompts, retrieval, chunking,
  reranking, or other relevant RAG components.
- Treat prompt-injection defenses as layered safeguards; do not
  assume that prompt wording alone guarantees protection.

## Secrets and Configuration

- Store secrets in environment variables or an approved local
  secrets mechanism.
- Never commit `.env` or other files containing real secrets.
- Keep `.env.example` free of real credentials and document the
  required configuration variables.
- Use different secrets for different environments.
- Rotate any secret that is exposed or suspected to be compromised.
- Avoid exposing secrets through logs, exceptions, API responses,
  screenshots, or generated reports.
- Review Git changes and staged files before every commit.

## Data and Privacy

- Store trace chunk IDs and short previews rather than full
  document contents.
- Never store API keys, passwords, or secrets in traces.
- Define retention periods for traces, spans, and usage events.
- Use the architecture's default trace-retention period of
  30 days unless an approved configuration specifies otherwise.
- Implement cleanup for expired trace and span data.
- Document the retention policy for usage events.
- Allow tenants to delete their documents and associated chunks
  and embeddings.
- Ensure deletion and retention operations are tenant-scoped.
- Avoid collecting or retaining data that is unnecessary for
  the service's functionality.

## Transport and HTTP Security

- Require HTTPS in preview and production environments.
- Restrict CORS to the approved dashboard origin.
- Configure appropriate security headers for the dashboard.
- Do not expose internal exception details, stack traces,
  database credentials, or other sensitive information to clients.
- Use secure session-cookie settings appropriate to each
  environment without weakening production settings.

## Logging, Tracing, and Monitoring

- Use structured logs that can include `trace_id` and `tenant_id`.
- Never log API keys, passwords, secrets, or full prompts
  containing user documents.
- Sanitize error messages and logs to prevent accidental
  disclosure of sensitive data.
- Ensure tracing failures never interrupt the main query path.
- Apply tenant isolation to stored traces, spans, and feedback.
- Configure appropriate health checks and error visibility.
- Use free or local-appropriate monitoring where possible;
  paid monitoring services must not be mandatory.
- Document how to identify and investigate failures.

## Dependencies and CI

- Review every new dependency and document the reason for adding it.
- Pin dependency versions once the project stabilizes.
- Run dependency vulnerability scans in CI where practical.
- Keep dependencies updated and address relevant security findings.
- Run automated tests for authentication, authorization,
  tenant isolation, file validation, rate limits, quotas,
  prompt injection, and error handling.
- Test the Redis-unavailable behavior to verify that protected
  query requests return HTTP 503 rather than bypassing limits.
- Ensure CI does not require paid infrastructure or paid API access.

## Security Testing Before Release

Before a release, verify the following:

- [ ] No secrets are committed or exposed in Git history.
- [ ] Authentication and authorization behave correctly.
- [ ] API keys are securely generated, hashed, and never logged.
- [ ] Expired and revoked API keys are rejected.
- [ ] API-key scopes are enforced.
- [ ] Tenant-isolation tests pass for all tenant-owned resources.
- [ ] Cross-tenant resource requests return HTTP 404.
- [ ] File type, size, filename, and content validation are tested.
- [ ] Document deletion removes associated chunks and embeddings.
- [ ] Background jobs cannot recreate deleted document data.
- [ ] Resource limits prevent uncontrolled ingestion or query work.
- [ ] Prompt-injection and unanswerable-question tests pass.
- [ ] Rate limits and monthly quotas are enforced before expensive work.
- [ ] Redis outages cannot silently bypass rate limits.
- [ ] CORS, HTTPS, and dashboard security headers are configured.
- [ ] Trace and usage-event retention policies are documented.
- [ ] Production environment variables and secrets are configured.
- [ ] Dependency security checks have been reviewed.
- [ ] Remaining security limitations are documented.

## Security Change Rules

- Follow `ARCHITECTURE.md` for the finalized system design.
- Record approved architectural changes in `DECISIONS.md`.
- Update security tests when introducing new endpoints,
  data flows, permissions, or background jobs.
- Review the security impact of changes before merging.
- Never weaken a security requirement merely to make a test pass.
- If a requirement cannot be implemented as specified, document
  the limitation and obtain approval before changing the design.