# Alembic migration isolation correction — 2026-11-03

User approved fixing Ponytail review finding1. Root cause: online Alembic engine inherited database REPEATABLE READ; earlier version-table query fixed a snapshot before material table locking, allowing a newly committed legacy upload to be missed by the conversion guard.

Single-session small corrective change with independent strongest read-only recheck. Added real PostgreSQL-default repeatable-read pre-lock concurrent-writer test; confirmed RED on old source, committed6d8951e before application fix. Explicit READ COMMITTED in alembic/env.py is the only application change; no new migration/schema/API behaviour. Updated plan, developer guide and shared contract to explain the invariant. Original review record retained with resolution.

Focused regression GREEN unchanged; full505backend passed31.29s in isolated schemas. Independent reviewer5migration tests passed5.35s and reports PASS/no remaining findings. Existing prior160browser/types/lint/format/build remain applicable; frontend unchanged and not rerun. No user database/private files/.env/live provider/deployment/push changes. Migration CLI will use the corrected isolation on its next invocation; no new revision to apply to an already-upgraded database.

Tracker not run; inherited Codex parent +gpt-6-astra high reviewer, token/cost totals unavailable. Initial test-writing command used incorrect relative path and sandbox test attempt could not reach local sockets; corrected path/escalated test invocation succeeded. Zero verifier correction rounds after this source fix.
