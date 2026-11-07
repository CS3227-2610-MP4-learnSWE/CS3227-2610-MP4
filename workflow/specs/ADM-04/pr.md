# ADM-04: reviewed private feedback follow-up

Admins can respond to an individual submitted feedback response or review and send an announcement to selected or all active students or teachers. Recipients receive private unread messages in a separate Messages section beneath existing survey requests.

Immutable server-side reviews, transaction-protected fan-out and persisted send receipts prevent duplicate delivery after retries or refresh. Recipient APIs enforce ownership and exclude raw feedback, audience identities and internal response links. Existing survey drafts and completion behavior remain intact.

Validation: strongest read-only verifier PASS at `7f1ff5e`: full 1,358 backend tests (116 ADM-04) and 615 browser tests (48 ADM-04), zero failures/errors/skips or browser retries/flaky cases. Typecheck/lint/build and scoped formatting/compile pass; all 130 tracked frontend formatting targets pass after LF normalization (Windows checkout uses CRLF). Independent tests were committed before implementation visibility; initial contract failures were fixed in one correction round. Independent designer full regression also passes: 1,358 backend tests in930.30s and615 browser tests in470.465s; zero failures/errors/skips/retries. Whitespace-only test cleanup `f4865f3` changes no assertions. See `logs/Adm04Implementation.md` and `workflow/specs/ADM-04/retro.md`.

Local runtime requires the additive `20261107_adm04_messaging` migration and a backend started with `uv run --env-file .env`. The implementation session leaves developer data/environment and existing user processes unchanged. No live AI or external messaging is used. Request quotas remain process-local; send uniqueness is enforced in PostgreSQL.

Nonblocking follow-up: while searching in All active users mode, the composer labels the filtered list total as selected. The immutable review shows the complete, correct role audience before confirmation; delivery/access remain correct.
