# Project Memory

> Records the actual current state of Heimdall. Update this file after every task. Permanent architecture decisions belong in `DECISIONS.md`.

## Current Status

Planning and initial documentation are in progress. The starter repository contains project documentation, configuration, and project skills. No application features have been implemented yet.

Verify this status against the actual repository at the start of each new work session.

## Completed

- Project idea, name (`heimdall-rag`), and scope defined.
- PRD and architecture documentation written.
- Design, development rules, security requirements, test plan, and task list drafted.
- Project skill written for OpenCode and Antigravity.

**Verification required:** Confirm that every listed document exists and has been reviewed and finalized. Do not mark a document complete merely because an initial draft exists.

## Current Task

**TASK-001:** Create the GitHub repository and push the starter project.

**Pending confirmation:** Confirm that TASK-001 is still the correct next task after completing the planned documentation review. Do not begin implementation until the documentation review is complete.

## Known Issues and Blockers

- No issues have been confirmed yet.
- Recheck the repository, configuration, and documentation before reporting that there are no known issues.
- Record newly discovered issues and blockers here, and update them when resolved.

## Pending Documentation Updates

The following finalized architecture decisions must be confirmed in `DECISIONS.md`:

- Background jobs use **arq with Redis**, not Celery or RQ.
- Programmatic API authentication uses the **`X-API-Key`** header.
- If Redis is unavailable, query requests fail closed with **HTTP 503** rather than bypassing rate limits.

Until these decisions are recorded and verified in `DECISIONS.md`, keep them listed as pending documentation updates. Remove each item from this section once it has been recorded and checked.

## Open Questions

- Which local Ollama model will be used for development?
- Which free hosting option, if any, will be used for the public demo? Verify its current free-tier limits before choosing.
- Confirm the embedding configuration against `ARCHITECTURE.md`. The current architecture specifies `BAAI/bge-small-en-v1.5` with 384 dimensions; do not treat this as undecided unless the architecture itself changes.

## Next Step

1. Finish reviewing and finalizing the project documentation.
2. Verify that `DECISIONS.md` records all accepted architecture decisions consistently with `ARCHITECTURE.md` and `SECURITY.md`.
3. Confirm the actual current task in `TASKS.md`.
4. Complete Phase 0 tasks (TASK-001 through TASK-011) according to the task list.
5. Begin Phase 1 only when its prerequisites are satisfied.

## Memory Update Rules

- Update the current status, current task, completed work, known issues, and next step after every task.
- Record only work that has actually been completed and verified.
- Remove resolved issues and pending items rather than leaving stale information.
- Check architecture-related statements against `ARCHITECTURE.md` and permanent decisions against `DECISIONS.md`.
- Do not duplicate the full task list or permanent architecture decisions here.
- Update the last-updated date whenever this file changes.

**Last updated:** 2026-10-09