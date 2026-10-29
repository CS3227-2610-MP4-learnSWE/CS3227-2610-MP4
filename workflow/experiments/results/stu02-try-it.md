# Try Run A and Run B yourself

Both runs built the same backend API (no UI). Run each in its own terminal and use the interactive docs page in a browser.

## Start them (PowerShell, two terminals)

Terminal 1, Run A (5 agents), port 8001:

```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\.claude\worktrees\stu02-run-a-eba95d\src\backend"
uv sync --frozen
uv run uvicorn main:app --host 127.0.0.1 --port 8001
```

Terminal 2, Run B (3 agents), port 8002:

```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\.claude\worktrees\stu02-run-b-223ec1\src\backend"
uv sync --frozen
uv run uvicorn main:app --host 127.0.0.1 --port 8002
```

Open http://127.0.0.1:8001/docs (Run A) and http://127.0.0.1:8002/docs (Run B). On each endpoint, click **Try it out**, fill the fields, then **Execute**. Stop a server with Ctrl+C. The run folders are only on this machine; they disappear when the run worktrees are cleaned up.

## What to try (do the same steps on both)

Correct answers, so you can aim for a known score: q1 = a, q2 = b, q3 = c.

| # | Do this | Expect |
|---|---|---|
| 1 | `GET /api/practice-sets/{set_id}` with `intro-se-1` | 3 questions with choices; no correct answers or explanations anywhere |
| 2 | `POST /api/practice-sets/{set_id}/attempts`, set `X-Student-Id` to `alice` | 201 with an `attempt_id`; copy it |
| 3 | `PUT /api/attempts/{attempt_id}/answers` as alice, body `{"answers": {"q1": "b"}}`, then `{"answers": {"q2": "b"}}`, then `{"answers": {"q1": "a"}}` | Answers merge; q1 changes from b to a |
| 4 | `GET /api/attempts/{attempt_id}/results` as alice now | 403 `not_submitted`, nothing revealed |
| 5 | `POST /api/attempts/{attempt_id}/submit` as alice now (q3 still unanswered) | 422 `incomplete`, listing `q3` as missing |
| 6 | Save `{"answers": {"q3": "c"}}`, then submit again | 200 with score 3 of 3 |
| 7 | Read results again | Your answers, the correct choices and explanations |
| 8 | Save answers or submit again after that | 409 `already_submitted` |
| 9 | Any attempt endpoint with `X-Student-Id` set to `bob` | 404 `attempt_not_found`, the same as an unknown id |
| 10 | Any attempt endpoint with the header empty | 401 `missing_student` |
| 11 | Save `{"answers": {"q9": "a"}}`, then `{"answers": {"q1": "z"}}` on a new attempt | 422 `unknown_question`, then `invalid_choice`; nothing saved |

## What to compare between A and B
- Are the error messages clear enough to show a student?
- Do the docs page explain the `X-Student-Id` header and the error codes?
- Are the response shapes the same across endpoints, and easy to build a page on?
- Anything confusing, inconsistent or surprising?

Note: the save/submit race that Run A fixed and Run B left open only shows with two requests at exactly the same moment, so you will not see it by clicking.
