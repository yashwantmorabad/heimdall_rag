# Design System (Developer Dashboard)

> DESIGN = HOW IT SHOULD LOOK AND FEEL.

## Style
Calm, precise, and technical, like a monitoring tool. Information-dense but never cluttered. Heimdall is the guardian who sees everything, so clarity and trust matter more than decoration.

## Typography
- UI text: Inter
- Code, keys, IDs, and trace data: JetBrains Mono (fallback: ui-monospace)

## Colors
| Token | Light | Dark |
|---|---|---|
| Primary | #4F46E5 | #818CF8 |
| Background | #F8FAFC | #0B1120 |
| Surface (cards) | #FFFFFF | #111827 |
| Text | #0F172A | #E5E7EB |
| Muted text | #64748B | #94A3B8 |
| Border | #E2E8F0 | #1F2937 |
| Success | #16A34A | #4ADE80 |
| Warning | #D97706 | #FBBF24 |
| Error | #DC2626 | #F87171 |

Rules:
- Never use color alone to show status; pair it with an icon or label.
- Span colors in the trace waterfall: retrieve = indigo, rerank = teal, generate = amber, other = slate.

## Components
- **Buttons:** Primary, Secondary, Destructive (red, always confirms), Ghost
- **Cards:** border radius 12px, 1px border, subtle shadow
- **Tables:** sticky header, row hover, sortable columns, pagination
- **Badges:** status badges for `queued`, `processing`, `ready`, `failed`
- **Copy field:** monospace value with a copy button (used for IDs)
- **Secret reveal:** an API key is shown once in a modal with a copy button and a clear warning

## Key screens
1. **Login and signup**
2. **API keys:** list with prefix, scopes, last used, expiry; create and revoke
3. **Documents:** upload area, list with status badges and error messages
4. **Usage:** charts for queries, tokens, and cost; quota progress bar
5. **Trace list:** filters for status, date, latency, and thumbs-down; failure view
6. **Trace detail:** question, answer, citations, and a waterfall of spans with durations, tokens, and cost; retrieved chunks with scores; feedback buttons

## UX requirements
- Mobile responsive at 375px, 768px, and 1440px
- Light and dark mode
- Loading states (skeletons), empty states (with a call to action), and error states (with a retry)
- Accessible forms with labels and visible focus
- Keyboard navigation for tables and modals
- Wide tables scroll inside their own container, never the whole page
- Destructive actions require confirmation
- Dates shown in the user's local time with absolute time on hover
