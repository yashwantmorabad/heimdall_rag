---
name: frontend-development
description: Use when building or changing the Heimdall Watchtower dashboard in frontend/, including Next.js pages, components, Tailwind styling, API client code, loading, empty, and error states, the API key modal, and Playwright tests. Use for any UI work on login, keys, documents, usage, traces, feedback, overview, or settings pages.
---

# Frontend (Watchtower dashboard)

## Stack and structure
Next.js, TypeScript (strict), Tailwind CSS.
```
frontend/app/   dashboard/  documents/  traces/  usage/  settings/
frontend/components/   reusable UI
frontend/lib/          API client helpers
```

## Rules
- The frontend talks to the FastAPI backend through its API. **Do not duplicate backend business logic.**
- Keep API calls in `lib/`, not inside components.
- All data shown is the authenticated tenant's, from the API. Never pass tenant IDs from the browser.
- Dashboard authentication uses the session cookie. API keys are not used by the dashboard.
- Every view that loads data has **loading, empty, and error** states.
- A new API key is shown **once**, in a modal with a copy button and a clear warning.
- Destructive actions (revoke key, delete document) require confirmation.

## Design
Follow `docs/DESIGN.md`. Starting direction: dark, observability-style interface.
```
Background: #0F172A    Primary: #6366F1
Font: Inter            Code font: JetBrains Mono
```
- Use monospace for IDs, keys, and trace data.
- Do not use color alone to show status; add an icon or label.
- Responsive at 375px, 768px, and 1440px. Wide tables scroll inside their own container.
- Accessible forms with labels, visible focus, and keyboard navigation for tables and modals.

## Key screens
Login and signup, overview, API keys, documents (upload and status), usage (charts and quota), trace list (failure filters), trace detail (span waterfall, retrieved chunks, scores), feedback, settings.

## Testing
Playwright end to end: sign up, create a key, upload a document, ask a question, open the trace.

## Do not
- Do not store API keys or secrets in local storage or in the repository.
- Do not call the LLM or database directly from the frontend.
- Do not skip loading, empty, or error states.
