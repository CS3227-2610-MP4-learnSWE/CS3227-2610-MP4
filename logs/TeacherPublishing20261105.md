# Teacher publishing implementation — 2026-11-05

## Approved scope and start

User explicitly requested implementation of the full updated plan on feat/tea03-publish-content, starting from clean1784729 after PR18/STU-01 and PR19/CHK-01 merge. Publish both notes and complete three-question batches once per draft; immutable snapshots, no assembly/republish/unpublish/published deletion. Reuse existing PublishedLesson/publish_lesson and student lesson APIs/UI. Add safe MCQ read APIs only; existing practice attempts/grading/companion remain separate.

Variant B: spec-writer completes exact contract and PR19 checker gate before application work. Developer and independent designer will start from the same approved specification SHA in separate worktrees; tests committed before implementation visibility. Strongest verifier, maximum two correction rounds, local commits only and human publishing/merge gate.

Parent baseline evidence from1784729 merge verification:855backend/352browser, frontend types/lint/format/build, speccheck and289checker unit tests passed. This implementation turn has not rerun that unchanged baseline. Existing isolated learnswe-tea01-test PostgreSQL16 container is available atloopback55432; no developer data or .env is read or changed. No live LLM/deployment/remote Git operation.

Resource tracker will be attempted at handoff; exact model/tokens/cost unavailable until measured. Inherited Codex spec/developer/designer roles; strongest read-only verifier later. No correction rounds yet.

Approved complete contract committed084534a. Parent independently ran speccheck --all:3checked,0failed,12existingwaivers, no newwaiver. Developer mainfolder and independent test-designer work/publishing-tests launched from that sameSHA. Pending publication navigation explicitly uses ownership guards rather than another router blocker. Request budgets and safe legacy responses are fixed in the contract.
