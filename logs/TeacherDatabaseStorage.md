# Teacher PostgreSQL file storage — 2026-11-02

## Approved request

User approved moving original uploads to PostgreSQL BYTEA on branch fix/teacher-postgres-file-storage. Keep10MiB/file and enforce100MiB total raw file bytes. Start fresh instead of importing uploads. Never modify the existing developer database/files/.env. No live LLM, deployment, push, PR or master merge. All existing teacher features/access checks remain.

## Initial state and workflow

Clean updated master6d65273 confirmed (PR13 merged MCQs and Ponytail review fixes). Feature branch created from that commit. Spec writer producing workflow/specs/TEA-01-db-storage exact schema/API/migration/quota/test contract before application edits. Variant B independent test-designer worktree shares recorded contract start with developer; parent owns logs/security/resources/handoff.

Baseline483 backend tests passed against isolated PostgreSQL schema and temporary files. Existing learnswe-tea01-test container running on55432; no developer data used. The file-dependent test cases will be adapted to preserve their security/validation/rollback intent. Exact usage/cost totals unavailable.

Verification in progress.

Approved specification committeda088945d4a62f1785daf93ff189bd73341a3dd72 before application changes. Developer and independent designer started from this SHA; designer isolated in sibling work/db-storage-tests. Advisory transaction-lock key32272610 and explicitREADCOMMITTED are binding. Historical spec banners clarify only storage requirements are replaced; prior feature behaviour remains binding. Source/productdocs owned by developer; test adaptations/newtest coverage owned by independent designer; parent owns workflow/session evidence.

## Source and independent tests

Developer source/productdocs committedf80b08670bff54484789b49f08647c36b69ca668 before independent test visibility. Current source has atomic BYTEA records, READCOMMITTED/advisoryquota, byte downloads/extraction, safe missing-content503 and migration refusal. Developer verification:327 nonteacher backend tests passed; existing fullbackend stopped after334passes/3expectedlegacy storage_key fixtures. New isolated ASGI smoke passed upload201, byte-identical download, fake note/MCQ generation201 and foreign course404 with noFILE_STORAGE_DIR. Existing155browser and types/lint/format/build passed. No actual.env/data/provider changes.

Independent tests6dff0a32f5a00e9993bc8ce0a7871868734a1edd committed before source visibility:6existingbackend fixture/suite adaptations,15newstorage backend cases and4quota/layout browser cases. Collection498backend/159browser and fronttypes passed before integration. Designer authorised to merge source and run full checks; final evidence pending.

## Integrated verification

Independent source integrationed5cf36 followed by finaltestcommitabfd930b50b011f90be7d62bb54ef3a87d96632d. Full498backend/159browser/types/lint/format/build passed. Postintegration edits were test formatting only and strengthening the quota freshness test to observe an actual ungranted pg_locks advisory waiter; focused strengthened case passed. No app defects or weakened assertions reported. Parent fast-forward mergedabfd930 and requested strongest read-only verifier. Parent inspected four quota-error dialog screenshots at390/1440 in light/dark: readable, input retained, limit/error visible, no overflow. Shared llm_client.py remains unchanged; final verifier verdict pending.

## Correction round1

Strongest verifier independently passed498backend/159browser/types/lint/format/build/diff, then reproduced an upgrade guard/write race with real Alembic operations and an isolated-schema barrier after empty EXISTS. A separate legacy writer committed; migration completed with1material/0binary rows, storage_key column removed, new revision stamped. This violates AC7. No other blocker found. Corrective contract now explicitly requires ACCESS EXCLUSIVE material table lock before the first guard, held through Alembic transaction in both upgrade/downgrade. Independent designer writing RED regression before developer migration-only fix; source unchanged until RED.
