# TRK-02 workflow triggers and cross-platform commands

Date: 2026-11-05
Branch: `feat/token-tracker-invocation-report`

## Changes

- Made the orchestrator responsible for tracking from feature selection through run close. Each agent launch, including retries, gets a distinct manifest row; the orchestrator generates and links the report when the run completes or stops.
- Clarified that this is a required orchestrator lifecycle step. The repository has no provider hook that watches agent launches in the background, so this update does not claim OS-level event capture.
- Added macOS/Linux commands for running the token-tracker tests and `run-report`.
- Documented that separate machines' local usage logs need to be collected; the tracker does not merge reports across machines automatically.

## Verification

- Documentation and resource-log changes only; no code tests rerun.
- `git diff --check` passed.
- No provider logs or prompt/reply content were committed.

## Resource use

- Tracker run: no
- Model: GPT-6 Luna, light
- Tokens and cost: not available for this documentation follow-up
- Retries/revision rounds: 0
