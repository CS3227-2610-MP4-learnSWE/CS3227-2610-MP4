# ADM-01 experiment: review pack (G4)

Costs are tracker list-price estimates (TRK-03, from session logs), not billed.

| Arm | Change from A | Cost USD | vs A | Requests | Q1 frozen suite (v2, 153) | Q2 blind review | Capped (2.536) | Rounds | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| A | none | 1.69 | baseline | 56 | 152/153 (AC6 no-store missing) | PASS, 4 non-blocking | no | 0 | baseline (not qualified: Q1) |
| H1 | context allowlist | 2.60 | +54% | 100 | 153/153 | PASS, 5 non-blocking | yes (marginal) | 1 | reject |
| H2 | verifier gets labelled items | 2.62 | +55% | 91 | 153/153 | NOT PASS, 1 blocking (AC9) | yes (marginal) | 1 | reject |
| H3 | haiku for developer/test-designer | 3.02 | +78% | n/a | 153/153 | PASS, 5 non-blocking | yes | 1 | reject |
| C | single session | - | - | - | not run | - | - | - | not run (dropped) |

Sources: `workflow/usage/runs/2026-11-05-ADM01-<arm>/report-v2.md`; blind key `grading/key.json` (x1=H3, x2=H2, x3=H1, x4=A).

## Triage and caveats
- Frozen suite v1 flagged `dict.update` in all arms (AC11 regex false positive, case-insensitive `\bUPDATE\b`). Fixed in suite v2 (`exp/adm01-frozen` d8da50d) with USER approval, all arms re-graded.
- Grading needs `TEA01_TEST_DATABASE_URL` with scheme `postgresql+psycopg://`.
- Arms ran without a provided database (confound): A did not run its ADM-01 tests; H1, H2, H3 started their own Postgres. H arms therefore had better in-run test feedback and spent more.
- Each H arm edited `test_tea03_publications.py` (expected Alembic head); H2 also loosened one assertion. Not blocking, needs human acknowledgement.
- Q2 verifiers did not run the suite; their cost is excluded. One sample per arm; revision rounds are not a quality measure.
- Arm A was reviewed blind although it failed Q1 (informational, USER approved).
- H2's blocking defect is not covered by any frozen test (a generation request failing before the try block leaves `requested` without an outcome).

## Decision rule result
No H variant was cheaper than A; none is adopted. Not run: C (secondary question has no verdict).
