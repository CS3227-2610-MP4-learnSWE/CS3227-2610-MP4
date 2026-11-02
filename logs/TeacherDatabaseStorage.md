# Teacher PostgreSQL file storage — 2026-11-02

## Approved request

User approved moving original uploads to PostgreSQL BYTEA on branch fix/teacher-postgres-file-storage. Keep10MiB/file and enforce100MiB total raw file bytes. Start fresh instead of importing uploads. Never modify the existing developer database/files/.env. No live LLM, deployment, push, PR or master merge. All existing teacher features/access checks remain.

## Initial state and workflow

Clean updated master6d65273 confirmed (PR13 merged MCQs and Ponytail review fixes). Feature branch created from that commit. Spec writer producing workflow/specs/TEA-01-db-storage exact schema/API/migration/quota/test contract before application edits. Variant B independent test-designer worktree shares recorded contract start with developer; parent owns logs/security/resources/handoff.

Baseline483 backend tests passed against isolated PostgreSQL schema and temporary files. Existing learnswe-tea01-test container running on55432; no developer data used. The file-dependent test cases will be adapted to preserve their security/validation/rollback intent. Exact usage/cost totals unavailable.

Verification in progress.
