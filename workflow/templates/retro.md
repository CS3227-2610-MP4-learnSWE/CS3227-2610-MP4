# Retro: <FEATURE-ID> <name>

One retro per feature, filled when the feature closes (after the verifier's final pass). Link it from the feature's row in `workflow/STATUS.md`. Short answers; use "none" or "n/a" with a reason rather than leaving a field empty.

Feature: | Branch: | PR: | Closed on:

## Revision rounds
Rounds used (cap 2): . Why each round was needed:

## Defects found
| Defect | Found by (agent) | Blocking? | Fixed in round |
|---|---|---|---|

## Resource use
Tracker run: yes | no. Total tokens: . Cost (USD): . Retries: . Resource-log row: (link)

## RED before GREEN
For each acceptance criterion or defect: the commit of the failing test and the commit of the fix. Say "no RED shown" where a test never failed first.

| Criterion or defect | Test commit (RED) | Fix commit (GREEN) |
|---|---|---|

## Steps done outside the pipeline
Anything done by hand or in a single session instead of by the roles in `coordination.md` (for example a manual fix, a skipped verifier pass, a test edited by the orchestrator), and why:

## What to change next time
One to three items, each pointing at a file in `workflow/`:
