# Ponytail full PostgreSQL storage review — 2026-11-03

Reviewed fix/teacher-postgres-file-storage at63b02bf against masterda389a5, including connected storage/generation/access helpers, merged transport/proxy configuration, tests and current guides. Read-only application review; no implementation changes. Parent reviewed frontend/config and strongest independent verifier reviewed backend/migrations. Assumed documented single-process local development workload and small uploads.

## Must fix: inherited migration transaction isolation

Alembic env.py:18 creates its engine without explicit isolation. If PostgreSQL defaults to REPEATABLE READ, earlier Alembic version-table queries establish a snapshot before LOCK TABLE material. A concurrent legacy upload committed after snapshot creation but before lock acquisition is invisible to EXISTS. Isolated real Alembic probe reproduced successful upgrade with1material/0material_file rows, no storage_key column, new head stamped. Original file mapping is lost despite the refusal guarantee.

Smallest fix: create_engine(..., isolation_level="READ COMMITTED") in the Alembic environment, matching teacher_session, plus a concurrent pre-lock regression with a repeatable-read connection default. Probe with normal READ COMMITTED refused safely; temporary runtime override of the proposed fix also refused under repeatable-read default, preserving row/key/prior revision. No repository patch applied. Verdict: fix this before acceptance. No additional concrete correctness/security/conciseness finding established; avoid speculative refactoring.

## Fresh evidence

- Independent backend504passed45.76s, including quota/concurrency/atomicity/access/generation/migration coverage.
- Parent frontend160browserpassed1.6m, including actual Vite config compatibility regression; types/lint/format/build passed.
- Code traces: access before binary reads; metadata excludes bytes; actual-byte quota under advisory lock/READ COMMITTED; both inserts/commit rollback; bounded extraction; no inference transaction; post-model access checks; safe rendering/error contracts; shared-helper merge; no stale runtime storage callers.
- Migration probe schemas removed; no developer database/upload data/private.env accessed, no live LLM or hosted deployment. Diff whitespace checks passed. Only required review/handoff records written.

Resource tracking not run; inherited Codex parent +gpt-6-astra high read-only verifier; tokens/cost unavailable. No app fixes, commit, push or PR. Review exposed a case missing from the passing default-isolation suite.

## Resolution

User authorised the fix. Regression committed6d8951e before source change; original code reproduced RED (migration succeeded despite concurrent row). One-line Alembic engine READ COMMITTED fix then passed unchanged regression and full505backend tests. Independent strongest reviewer passed5migration cases covering snapshot/lock races, populated refusal and empty cycles, and confirmed no remaining findings. Guides/shared contract/plan updated. No new schema revision or developer database changes; no frontend rerun for migration-only fix.
