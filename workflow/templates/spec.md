# Spec: <FEATURE-ID> <name>

Status: Draft | Approved (by <name>, <date>)

## Goal
One or two sentences, from the user story.

## Behaviour
What the user can do and sees.

## Acceptance criteria
- [ ] AC1 (testable)

## UI states and copy
Read [the shared UI design guide](../ui-design.md) before specifying a screen (from a generated feature spec, use `../../ui-design.md`). Record the concrete hierarchy/panels, outlined field treatment, primary/secondary actions, responsive light/dark behavior, keyboard/focus and notification/count semantics. Use the guide's final checklist; exact feature behavior and copy must still be specified below.

For any feature with a screen. The test-designer cannot see the code, so every state a user can see is written here, not left to the developer. Write "not applicable" for a row that does not apply.

| Screen or action | Control (button, tab, link, field) and its exact label | Loading | Success | Empty | Each failure that can happen (wrong input, 401, 403, 404, 409, 422, 429, network, timeout) and the exact message | After a failed action (what stays, what is retried) |
|---|---|---|---|---|---|---|

Also state, as labelled entries (one list item per label, written `Label: text`; write `Label: not applicable: reason` when one does not apply):
- Requests per load and per retry: how many requests each screen that calls the API sends on load and on each retry (one, unless the spec says otherwise; development builds run effects twice, so the developer must not send duplicates).
- Wrong role: what a user in the wrong role sees (a redirect to their own area or a message, and whether any request is sent).
- Link history: push or replace: for every link and button that changes the URL, whether it adds a history entry or replaces the current one.
- Refresh: what a user sees after a browser refresh.
- Back and Forward: what a user sees after browser Back and Forward.
- Expired session or logout: what a user sees after logout or when the session has expired.
- Backend down: what a user sees when the backend cannot be reached, and how they recover.
- Longest wait before an error: the longest time any screen waits before showing an error.
- No generic failure message: that no failure hides behind a generic message ("could not reach the server" is only for a real network failure).

## Out of scope

## Security and AI safeguards
Access rules, untrusted inputs, answer-release rules, limits. Also state, as labelled entries (`Label: text`):
- Concurrent requests (same time): what must hold when two requests for the same record arrive at the same time.
- Normalisation: how identifiers and other inputs are normalised (for example trimming whitespace) before comparison.

## Open questions
