# Test Plan

Defines what "working" means. Run the full suite with `make test`.

## 1. Tenant isolation (`backend/tests/isolation/`)
Create two tenants (A and B) with their own keys and documents. Confirm tenant B cannot:
- [ ] List, read, or delete A's documents (404)
- [ ] Retrieve A's chunks through `/v1/query`, even with a question matching A's content
- [ ] Read A's traces, spans, usage, or feedback
- [ ] Use A's API key after it is revoked
- [ ] Pass `tenant_id` in a body or query string to access A's data
These tests run on every push and block merging.

## 2. Authentication and keys
- [ ] Signup and login work; wrong password fails
- [ ] Logged-out users cannot access dashboard APIs
- [ ] API key is shown once; only its hash is stored
- [ ] Missing, invalid, expired, and revoked keys return 401
- [ ] Scope enforcement (a `query`-only key cannot upload)
- [ ] Active key limit per tenant is enforced
- [ ] `last_used_at` updates on use

## 3. Rate limits and quotas
- [ ] Exceeding the per-key limit returns 429 with Retry-After
- [ ] Exceeding the per-IP limit returns 429
- [ ] Exceeding the monthly quota is rejected
- [ ] Usage counts match the number of requests sent

## 4. Ingestion
- [ ] Valid PDF reaches `ready`; chunks exist with the correct `tenant_id`
- [ ] Wrong file type and oversized file are rejected
- [ ] Corrupt file reaches `failed` with an error message
- [ ] Retrying a job does not create duplicate chunks

## 5. Query and guardrail
- [ ] Question answerable from a document returns an answer with correct citations
- [ ] Question not in the documents returns "not found" and makes no LLM call
- [ ] Empty tenant (no documents) returns "not found"
- [ ] Very long or empty questions are validated
- [ ] A document containing "ignore previous instructions" does not change behavior

## 6. Tracing
- [ ] Every query creates one trace with retrieve, rerank, and generate spans
- [ ] Spans record duration, status, tokens, cost, chunk IDs, and scores
- [ ] `X-Trace-Id` header matches the stored trace
- [ ] A tracing failure does not fail the query
- [ ] Feedback links to the correct trace

## 7. Dashboard
- [ ] Pages render loading, empty, and error states
- [ ] Mobile (375px), tablet (768px), and desktop (1440px) layouts work
- [ ] Keyboard navigation works for forms, tables, and modals

## 8. End-to-end (Playwright)
Sign up, create a key, upload a PDF, wait for `ready`, ask a question, open the trace, give feedback, revoke the key.

## 9. Evaluation (`make eval`)
- [ ] Dataset of at least 50 hand-checked question and answer pairs
- [ ] Metrics: recall@k, faithfulness, latency
- [ ] Results saved in `evals/reports/` with the configuration used

## 10. Load test
- [ ] Locust or k6 run against the preview deployment
- [ ] p50 and p95 latency and error rate recorded for the default configuration

## Before every production deploy
- [ ] Lint, type checks, and tests pass
- [ ] Production build passes
- [ ] No secrets in Git
- [ ] Isolation tests pass against a fresh database
