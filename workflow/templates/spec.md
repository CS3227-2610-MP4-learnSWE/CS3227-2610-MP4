# Spec: <FEATURE-ID> <name>

Status: Draft | Approved (by <name>, <date>)

## Goal
One or two sentences, from the user story.

## Behaviour
What the user can do and sees.

## Acceptance criteria
- [ ] AC1 (testable)

## UI states and copy
For any feature with a screen. The test-designer cannot see the code, so every state a user can see is written here, not left to the developer. Write "not applicable" for a row that does not apply.

| Screen or action | Control (button, tab, link, field) and its exact label | Loading | Success | Empty | Each failure that can happen (wrong input, 401, 403, 404, 409, 422, 429, network, timeout) and the exact message | After a failed action (what stays, what is retried) |
|---|---|---|---|---|---|---|

Also state: what a user sees on refresh, on Back and Forward, after logout or an expired session, and with the backend down; the longest time any screen waits before showing an error; and that no failure hides behind a generic message ("could not reach the server" is only for a real network failure).

Also state, for every screen that calls the API: how many requests it sends on load and on each retry (one, unless the spec says otherwise; development builds run effects twice, so the developer must not send duplicates); what a user in the wrong role sees (a redirect to their own area or a message, and whether any request is sent); and for every link and button that changes the URL, whether it adds a history entry or replaces the current one.

## Out of scope

## Security and AI safeguards
Access rules, untrusted inputs, answer-release rules, limits. Also state: what must hold when two requests for the same record arrive at the same time, and how identifiers and other inputs are normalised (for example trimming whitespace) before comparison.

## Open questions
