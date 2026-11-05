# Teacher publication CI bundle check — 2026-11-05

User reported GitHub CI failure: Student bundles hold no answer key, Control failed: Teacher chunk has no explanation text. Reproduced the exact YAML shell step locally after a fresh successful frontend production build: exit1, same message.

Cause: publication removed obsolete teacherDemo static answers and sample Review. The CI positive control still required their explanation text inside a Teacher chunk, despite keys now being server-side. Correct only CI/docs: positive control matches the real backend practice_data.py fixture; leak scan includes every generated JS chunk, with no Teacher exclusion. No application/data/auth/LLM changes, no weakening of answer-leak protection.

Verification: frontend production build/typecheck PASS. Extracted and executed the exact corrected YAML shell step: clean build PASS; temporary injected explanation in index-ci-leak-control.js FAIL as intended; same injection in Teacher-ci-leak-control.js FAIL as intended; controls removed in finally, final clean build PASS. git diff --check PASS. No full application suite rerun because no runtime changes. Remote GitHub Actions rerun not performed; no push/PR/merge/deployment. Secrets/.env/developer DB untouched.

README/DeveloperGuide obsolete teacherDemo statements corrected; security/handoff/resource records updated. This is a CI maintenance correction, not a third application implementation round. Single inherited Codex session, no agents launched. Aggregate tracker attempted;0 attributed requests, actual tokens/cost unavailable rather than zero. Report workflow/experiments/results/teacher-publication-ci-fix.csv.
