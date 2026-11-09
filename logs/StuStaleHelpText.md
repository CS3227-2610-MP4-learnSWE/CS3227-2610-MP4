# Stale student help text (2026-11-09)

- Trigger: the TEA-05 owner noted that `companion_help.py` still said published-set practice is pending and that the teacher overview/inbox are demonstrations.
- Pulled master (TEA-06, then TEA-05 merged as PR 38), created `fix/stu-stale-help-and-hint-copy`.
- Audited the student side against `docs/UserGuide.md`: rewrote the stale lines in `companion_help.py`, corrected the Student bullet in `README.md`. No application logic or tests changed.
- Verified: file parses; STU-03 companion tests 30 passed, 92 skipped (no test database in this session). Full suites and CI not run.
- Later in the session (user decision): hid the "Demo · Sample data" pill for signed-in users (`Shell.tsx`, new test in `auth-guard.spec.ts`) and reworded the practice-set published message in `PublishDraft.tsx` and its test. 76 of 76 focused browser tests passed.
- Previously flagged, now done: to the user: `PublishDraft.tsx` pending message (teacher file, test-pinned), the scripted hint panel (honest, spec-pinned), the "Demo · Sample data" pill for signed-in students.
- Pushed to PR 39.
