# CI real-backend cleanup fix summary: 31 October 2026

## Direction and completed work
After PR 8 was merged, the CI run on `master` failed in the Real backend end-to-end job: its test passed, but the `setup-uv` cleanup (`uv cache prune --ci`) timed out waiting 300 s for the uv cache lock. The same failure had appeared once on the PR's first run, then did not recur on the next PR run or on two earlier `master` runs, so it is intermittent. On `fix/ci-real-backend-cleanup` (from the latest `master`) I added an `if: always()` "Stop backend" step at the end of that job, which kills the background `uvicorn` before the cleanup runs.

## Verification and limits
The workflow YAML parses and the step is last in the job. The fix is untested on GitHub; because the failure is intermittent, several green runs would be needed before calling it fixed. The cause (the background `uv run` process holding the cache lock) is a likely explanation, not confirmed. Nothing is committed or pushed at the time of writing.

## Resources and summary verification
Single session, no agents; no token or cost total measured. This summary was checked against the job results, the log text the user pasted and the diff. Human review pending.
