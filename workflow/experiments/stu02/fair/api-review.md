# Blind API review of the fair runs (P = fair B, Q = fair baseline, R = fair A)

| Dimension | fair B | fair baseline | fair A |
|---|---|---|---|
| Error message and code clarity | 4 | 5 | 3 |
| Response and error shape consistency | 4 | 4 | 4 |
| Contract match incl. check order | 5 | 3 | 3 |
| Submit/results predictability | 5 | 5 | 5 |
| OpenAPI docs | 2 | 2 | 2 |
| Awkwardness for a frontend | 4 | 3 | 3 |

Ranking: 1 fair B (only one following the documented check order for bad bodies), 2 fair baseline (best messages, names the rejected question), 3 fair A (same ordering problem, vaguest 401 message).
Identical in all three: happy path, merging, ignored client score, 409s, 403, cross-student 404 byte-identical to unknown id, nothing saved from rejected requests, no leaks; header not trimmed in any; OpenAPI documents no error responses and shows the header as optional.
