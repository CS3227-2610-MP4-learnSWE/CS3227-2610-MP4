# Independent API usability review (blind)

A read-only sonnet subagent reviewed both backends from a frontend developer's point of view. It was given neutral copies labelled version 1 and version 2 and was not told which run made which. Unblinded afterwards: **version 1 = Run B, version 2 = Run A**. It ran the same scenarios in-process against both and compared real responses.

| Dimension | Run B (V1) | Run A (V2) | Why |
|---|---|---|---|
| Error message clarity | 4 | 3 | Same codes; B's messages slightly more helpful ("X-Student-Id header is required." vs "Student identity is required.") |
| Response shape consistency | 5 | 5 | Same field names everywhere; errors always `{"detail":{"code","message"}}` |
| Contract match | 5 | 5 | Every status, code and field matched the plan, including check order |
| Submit/results predictability | 5 | 5 | Same outcomes |
| OpenAPI docs | 2 | 3 | Both bare; A types `status` as an enum/const |
| Awkwardness | 3 | 4 | B does not trim the student header, so " carol " and "carol" are different students |

Reviewer's preference: Run A, narrowly (typed status, trimmed header); behaviour and contract are otherwise identical.

Problems in both: 401/403/404/409 responses and their error codes are not documented in OpenAPI (only 200/201 and the generic 422); the `X-Student-Id` header shows as optional with no description; business 422s are objects while body-shape 422s are FastAPI lists, so a page must handle two shapes. Neither message names the offending question or choice id.

Not covered by this review: concurrency (the save/submit race Run A fixed and Run B left open).
