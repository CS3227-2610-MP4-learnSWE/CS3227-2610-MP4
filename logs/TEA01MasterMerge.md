# Merge master into TEA-01 — 2026-11-01

User requested merging their updated local master into the current feature branch. Working tree was clean on feat/tea01-materials. Merged master 778c696, resolving nine shared-file conflicts by retaining both teacher and student companion functionality. Combined backend dependencies and regenerated uv.lock; retained isolated PostgreSQL fixtures and fake LLM fixture, both environment-example groups, and both workflow histories. Guides now describe persistent teacher materials and the live student companion together.

Verification: 343 backend tests passed with a unique temporary schema on the dedicated teacher test database; 102 mocked browser tests passed. Frontend typecheck, lint, production build and diff whitespace checks passed. No live LLM call or deployment. No push or PR requested. Local .env files unchanged.
