# Plan: TEA-03 publishing preparation

Approved preparation only, based on clean master db82a18 (PR17). No database, backend API or student implementation changes.

1. Audit current teacher docs against implemented uploads, generation, editing, deletion and auth. Record discrepancies and PR17 merge state.
2. Replace TEA-04 assembly stories with batch publication requirements; preserve story IDs for traceability. Cross-reference the explicit publication workflow in US-TEA-03-04. Label future requirements and historical scope clearly.
3. Before UI changes, add browser regressions: no teacher assembly navigation/builder; old teacher practice URL redirects and refreshes; studio shows exact batch publication notice and no working Publish action; student Practice navigation remains available.
4. Remove the unused PracticeSets component and selection-only imports; remove its teacher sidebar entry, retain legacy-route redirect. Add the exact notice from spec.md to the existing MCQ studio.
5. Document compatibility: student practice currently uses fixed intro-se-1/server fixtures, string choice IDs and in-memory attempts. Publishing will require a server mapping and student discovery/version integration; do not alter those contracts during preparation.
6. Run frontend types/lint/format/build and full mocked browser suite, including student/practice/companion regressions. Confirm no backend/student runtime diff. Independent read-only review, then local commit; no push/PR/merge.

This is the repository's small docs/preview-cleanup single-session exception, not the publishing feature implementation. The latter requires a complete approved contract and Variant B before source changes. Current user request authorizes these preparation changes without another approval question.
