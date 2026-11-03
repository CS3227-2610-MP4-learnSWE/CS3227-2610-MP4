# SHR-01 authentication spec: 2026-11-03

## Request and scope

The user is building the student side and offered to build login. After discussion they chose a single login system for all three roles, with a shared auth core, so teacher and admin owners can adopt it later. This session produced the spec only; no code or tests were written.

## What happened

1. Pulled `master` (fast-forward `778c696` to `6d65273`, the teacher TEA-01 to TEA-03 work) and read `workflow/notes.md` and `docs/FeatureList.md`. A second pull later reported already up to date; no remote branch carried the teammate's Neon/file-storage change.
2. Helped the user run the app locally: Docker Postgres, backend `.env` (`FILE_STORAGE_DIR` and the missing `DATABASE_URL` that caused the first migration to fail on port 5432), `alembic upgrade head`, seed. The user confirmed these ran.
3. Discussed hosting: Render's free tier has no persistent disk, so teacher uploads in `FILE_STORAGE_DIR` would not survive restarts; Neon's free storage limit was unclear between its docs (0.5 GB vs 1 GB). Flagged that `CLAUDE.md` bans build-and-host tools and that Render needs checking against that rule. Nothing was decided.
4. User decisions: session cookie; seeded accounts plus public signup that creates students only; scope of auth core, login UI and student route migration; demo access kept; limiter move approved; teacher routes and specs unchanged.
5. Created `feat/shr01-auth-spec` and ran the spec-writer twice (draft, then a revision for demo access and closed questions). Edited two open-question entries in `spec.md` myself to record the user's answers.
6. User approved the spec and plan and asked for a commit.

## Verification

I checked that the three spec files exist. I did not read the full spec; the user reviewed it. The claim that the teacher Playwright specs pass without signing in is unverified (the spec-writer did not read them). No tests or builds were run.

## Open

Cookie settings depend on the Render/Neon topology. Teacher file storage on Render is unresolved and belongs to the teacher owner. Nothing is pushed and no PR exists.
