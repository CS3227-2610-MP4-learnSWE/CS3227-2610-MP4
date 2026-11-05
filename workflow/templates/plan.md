# Plan: <FEATURE-ID> <name>

## Data model

## API endpoints
Method, path, roles allowed, request/response, errors.

## Components and modules
New and reused (shared modules named explicitly).

## UI contract
For each screen: the accessible role and name of every control and message the tests will use (for example button "Create account"), the timeouts, and the copy from the spec's "UI states and copy" table. The test-designer uses only these names. Also fix, per screen, as labelled entries (one list item per label, written `Label: text`; `Label: not applicable: reason` when one does not apply):
- Requests per load and per retry: the number of requests on load and on each retry.
- Wrong role: the behaviour (redirect or message, and whether a request is sent).
- Link history: push or replace: for each link, push or replace in the browser history.
- No generic failure message: that every failure uses its exact message from the spec.

## AI usage
Prompt inputs, context allowed, output validation, limits, failure handling.

## Test plan
Acceptance criterion to test mapping; security tests.

## Decisions
