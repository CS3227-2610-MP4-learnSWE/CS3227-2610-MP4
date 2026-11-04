# Teacher MCQ editing and unpublished-work deletion

## 2026-11-04 — Approved implementation started

- User approved authenticated teacher APIs, versioned whole-batch MCQ editing and confirmed deletion of unpublished notes/MCQ batches plus unreferenced source materials. Any managing teacher may act; publication/unpublishing and student history changes are excluded.
- Clean master `da57eab` (PR16 authentication, after PR15 PostgreSQL storage) recorded before creating `feat/tea03-edit-mcqs-delete-drafts`.
- Variant B: spec-writer first; developer and independent test designer will use the same approved specification commit and separate folders, then a strongest read-only verifier. No redundant document approval requested: user supplied the complete approved plan.
- Test infrastructure: Docker application could not launch (missing executable). Initial sandboxed initdb failed on shared memory; approved elevated initdb/pg_ctl started an isolated temporary PostgreSQL cluster at loopback port55439, database learnswe_test. This is not the developer database. Existing development data, files and .env remain untouched.
- Baseline backend and mocked browser suites started before application changes. Results and subsequent commits recorded below when available.
- No live LLM, deployment, push, PR publication or merge into master authorised by this session.

- Approved contract/stories committed0038b47; independent developer/designer launched from that exact commit. Baseline backend692passed (101.81s), before application changes.
