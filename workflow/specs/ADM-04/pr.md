# ADM-04: reviewed private feedback follow-up

Admins can respond to an individual submitted feedback response or review and send an announcement to selected or all active students or teachers. Recipients receive private unread messages in a separate Messages section beneath existing survey requests.

Immutable server-side reviews, transaction-protected fan-out and persisted send receipts prevent duplicate delivery after retries or refresh. Recipient APIs enforce ownership and exclude raw feedback, audience identities and internal response links. Existing survey drafts and completion behavior remain intact.

Validation: developer existing suites cover all 1,242 backend and 567 browser cases passing across full and focused recovery runs; types/lint/build/scoped formatting/compile pass. Independent ADM-04 integration and read-only verification are pending; update this paragraph with final results before opening PR.

Local runtime requires the additive `20261107_adm04_messaging` migration and a backend started with `uv run --env-file .env`. The implementation session leaves developer data/environment and existing user processes unchanged. No live AI or external messaging is used. Request quotas remain process-local; send uniqueness is enforced in PostgreSQL.
