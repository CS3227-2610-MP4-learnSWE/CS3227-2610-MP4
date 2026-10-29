# STU-02 independent edge-case battery

Designed from `spec.md` and `plan.md` only. Files:

- `edge_cases.py`: the battery. `python edge_cases.py <app_dir> [--slow MODULE:ATTR]` prints a JSON list of results. `--list` prints scenario metadata only.
- `reference/main.py`: my own implementation of the contract. `MUTANT=<name>` switches on one planted bug (`MUTANTS` dict).
- `selfcheck.py` (runs everything, writes `selfcheck_results.json`) and `make_readme.py` (regenerates this file).

Totals: **115 scenarios** (75 `contract`, 40 `robustness`; CONC-08 is `contract` with `--slow`, `robustness` without), **62 planted bugs**.

Run it with the backend venv python, for example: `python edge_cases.py reference --slow main:do_save`.

## How the expectations were decided

- `contract`: the spec or plan states the outcome (status, error code, field, check order, 'nothing is saved from a rejected request', 'body ignored', 'not guessable ids').
- `robustness`: the spec is silent. Expectation is safe and sensible: no 5xx, a 4xx rejection, nothing wrongly saved, no leak. Where several outcomes are sensible, the scenario accepts each of them (listed in its Expected column).
- Success bodies after submission are checked for required fields and values, not for the absence of extra fields. Pre-submission bodies and the set body are checked strictly for leak fields.

### Ambiguities and how I resolved them

- Whitespace-only `X-Student-Id`: 'any non-empty string' could mean accepted. ID-03 accepts either 401/400 or an ordinary id that only that exact value can use.
- Padded / differently-cased ids (' alice', 'Alice'): the plan calls the header 'any non-empty string', so ids are compared exactly. I treat a server that strips or lower-cases as a defect (robustness: ID-05, ID-06).
- Duplicate `X-Student-Id` headers, non-ASCII bytes, 100k-char ids: spec silent. Only 'no 5xx, no cross-student access' is required.
- Malformed bodies: the plan allows FastAPI's default 422 body, so only status (400-499) is required for them, not the error shape. But the plan's check order still applies, so a malformed body from a non-owner must give 404 (ORD-04), from the owner on a submitted attempt 409 (LOCK-03), and with no header 401 (ORD-02). Implementations that let FastAPI validate the body before the handler will fail these on purpose.
- Wrong-typed choice values (null, number, list) and wrong body shapes: the plan only says 422 for `unknown_question` / `invalid_choice` and 'may use the default body' for malformed. I accept 400 or 422, require nothing saved.
- A request with both an unknown question and an invalid choice: the plan does not give a priority. SAVE-08 accepts either code.
- `PUT` with `{"answers": {}}`: merging nothing is arguably 200, rejecting is arguably 422. SAVE-11 accepts both and requires the saved answers unchanged.
- Extra client fields on `PUT` (status, score): ignoring is the natural reading of 'client score ignored'; a 4xx is also accepted. Becoming submitted is not.
- Duplicate JSON keys: accepted (last wins) or rejected, but response must match stored state.
- Start-attempt body: the plan documents none. Any body is ignored or rejected 4xx; it must never set state or the id.
- The 'not yours' 404 must be indistinguishable from 'unknown' 404 (AC9). I compare status and full body (code and message), in every attempt state, for every endpoint (XS-05).
- 'Opaque, not guessable' ids (plan): checked as strings, at least 8 chars, unique, URL-safe, not a plain counter, not containing the student id, not resolved by prefix or case (START-04/05, XS-09). Randomness quality beyond that is not measurable.
- Health endpoints (AC11): the plan gives no path, so the battery does not test them.
- Pre-submission leak of the *correct choice id* inside a message cannot be found by string search (every id is a letter). LEAK-02, LEAK-05 and LEAK-06 use differential tests instead: the message or response shape must not change with the question or with whether the saved answer is right.
- Concurrency (b): with `--slow` the named function is wrapped (also in any other module that imported the same object) to sleep 0.3 s first; the save starts, 0.1 s later the submit starts. Consistency rule: the reported score must equal the score of the final stored answers; a save that returned 200 must be visible in the final state; a save that returned 409 must not be. Without `--slow`, 40 simultaneous pairs are run. This can only catch races that an in-process event loop can interleave (an implementation with real locks and no awaits between check and write cannot be broken, correctly).

## Scenarios

| ID | Category | Kind | Scenario | Expected |
|---|---|---|---|---|
| ID-01 | identity | contract | POST start attempt with no X-Student-Id header | 401 missing_student |
| ID-02 | identity | contract | POST start attempt with an empty X-Student-Id header | 401 missing_student |
| ID-03 | identity | robustness | Whitespace-only X-Student-Id ('   ', tab) | No 5xx; either rejected 401/400, or accepted as an ordinary id that only that same value can use |
| ID-04 | identity | contract | Header name case: create with 'x-student-id', read with 'X-STUDENT-ID' | HTTP header names are case-insensitive: both work as the same student |
| ID-05 | identity | robustness | Padded ids: ' id', 'id ', '\tid' are not the same student as 'id' | 404 (or 401); never 200 |
| ID-06 | identity | robustness | Student ids differing only by case ('Alice' vs 'alice') | Different students: 404 for the other-cased id |
| ID-07 | identity | robustness | Very long student id (100,000 chars) | No 5xx; if accepted, the same id can use its attempt |
| ID-08 | identity | robustness | Two X-Student-Id headers with different values | No 5xx; 201/400/401; if accepted, a third student cannot read the attempt |
| ID-09 | identity | robustness | Non-ASCII (UTF-8 bytes) in the student header | No 5xx; if accepted, same bytes can read it and a different student cannot |
| ID-10 | identity | contract | Existing attempt, no header, on GET attempt / PUT answers / submit / results | 401 missing_student on each; same for an empty header |
| ID-11 | identity | contract | GET set without header and with a header | 200 both, identical bodies |
| ID-12 | identity | robustness | Student ids that look like injection / wildcards ('*', "' OR '1'='1", '%', '..', 'admin', 'null') | Treated as ordinary ids: 201 and only that id can read its attempt (admin/teacher get no special rights) |
| ID-13 | identity | contract | Unknown attempt id, no header, on all four attempt endpoints | 401 missing_student (header is checked before existence) |
| ID-14 | identity | contract | Start attempt on an unknown set with no header | 401 missing_student (header first) |
| ID-15 | identity | contract | Student id that is a numeric string / looks like a boolean ('0', 'false') | Any non-empty string is a valid id: 201 |
| SET-01 | set | contract | GET the set; compare to the fixture exactly (title, order, text, code, choices) | 200; id, title, questions q1..q3 in order; code null for q1,q2; choices a,b,c with fixture text |
| SET-02 | set | contract | GET the set and inspect every key | Exactly {id,title,questions}; question {id,text,code,choices}; choice {id,text}; no key/explanation/key_version |
| SET-03 | set | contract | GET unknown set ids: 'nope', 'INTRO-SE-1', 'intro-se-2', 'intro-se-1x', ' intro-se-1', long, unicode | 404 set_not_found for each (case-sensitive, exact match) |
| SET-04 | set | robustness | GET set after other students started, saved and submitted attempts | Set response unchanged (no per-attempt state bleeds into the set) |
| SET-05 | set | robustness | GET set with an empty-ish POST/odd path: trailing slash and double slash | No 5xx; any 2xx body has no key/explanation |
| START-01 | start | contract | POST start attempt on intro-se-1 | 201 {attempt_id,set_id,status:in_progress,answers:{}} |
| START-02 | start | contract | Start on an unknown set with a valid header | 404 set_not_found |
| START-03 | start | contract | AC10: two attempts by one student; save/submit one | Independent: other stays empty and in_progress; a third start is fresh |
| START-04 | start | contract | Attempt ids: 40 creations are strings >= 8 chars, unique, not sequential integers | All unique, len >= 8, not consecutive numbers |
| START-05 | start | robustness | Attempt id shape: URL-safe, no student id inside, ids of different students differ | Opaque: charset [A-Za-z0-9_.~-], does not contain the student id, no shared long prefix |
| START-06 | start | robustness | Start with a body that tries to set state ({status:submitted, answers, attempt_id, score}) or garbage | No 5xx; if 201 the attempt is in_progress, empty, with a server-chosen id |
| START-07 | start | contract | GET a fresh attempt | 200 {attempt_id,set_id,status:in_progress,answers:{}}, same id |
| SAVE-01 | save | contract | Save one answer | 200 {attempt_id,status:in_progress,answers:{q1:a}}; GET agrees |
| SAVE-02 | save | contract | Revise the same answer 12 times (a,b,c,...) | Always 200; last value wins |
| SAVE-03 | save | contract | Save q1, then q2, then revise q1 (merge semantics) | Responses contain all saved answers |
| SAVE-04 | save | contract | Save all three answers in one request | 200 with all three |
| SAVE-05 | save | contract | Unknown question ids: q4, Q1, 'q1 ', ' q1', '', q0, __proto__, q1\u0000, fullwidth ｑ１, '1' | 422 unknown_question each; nothing saved |
| SAVE-06 | save | contract | Invalid choice ids for q2: d, A, 'a ', '', ab, q1, 1, null, fullwidth ａ, ' a', 'a\n' | 422 invalid_choice each; nothing saved |
| SAVE-07 | save | contract | Mixed request: valid q1 plus invalid q2 choice / unknown q9, with earlier saved answers present | 422; the valid entry of the same request is NOT saved; earlier answers untouched |
| SAVE-08 | save | robustness | One request with both an unknown question and an invalid choice | 422 with code unknown_question or invalid_choice; nothing saved |
| SAVE-09 | save | robustness | Wrong value types for a choice: 1, null, true, false, ['a'], {'a':1}, 1.5, [], {} | 400/422 (never 200, never 5xx); nothing saved |
| SAVE-10 | save | robustness | Wrong body shapes: {}, answers null/list/string/number, top-level list/null/string/number, wrong key name, nested objects | 400/422; nothing saved |
| SAVE-11 | save | robustness | Empty answers object {'answers': {}} on an attempt with a saved answer | 200 (merge of nothing) or 422; saved answers unchanged either way |
| SAVE-12 | save | robustness | Non-JSON / malformed bodies: text, truncated JSON, empty, invalid UTF-8, single quotes, trailing comma, trailing garbage, NULs | 4xx (400-499, never 5xx); nothing saved |
| SAVE-13 | save | robustness | Huge payloads: 20,000 unknown keys; a 3 MB choice string; q1 valid plus 5,000 unknown keys | 4xx or 413 (never 5xx / hang); nothing saved |
| SAVE-14 | save | robustness | Deeply nested JSON (100,000 levels) as the body and as a choice value | 4xx, no 5xx / crash; nothing saved |
| SAVE-15 | save | robustness | PUT with extra client fields: status:'submitted', score, attempt_id, key_version alongside valid answers | Extras ignored (200, in_progress, only the answers saved) or the request rejected 4xx with nothing saved; never submitted |
| SAVE-16 | save | robustness | Duplicate JSON keys in one body: {"answers":{"q1":"a","q1":"b"}} | No 5xx; 200 with one of the values (consistent with GET) or 4xx with nothing saved |
| SAVE-17 | save | robustness | PUT with answers in the query string (?q1=a&answers=...) and an empty body | Query string is not an input: nothing saved |
| SAVE-18 | save | contract | PUT valid answers to an unknown attempt id | 404 attempt_not_found |
| SAVE-19 | save | contract | PUT keeps answers for questions not in the request and returns the full map each time | Response answers always equals GET answers |
| SAVE-20 | save | robustness | Large but valid-looking repeated saves (200 requests) do not break the attempt | All 200; final state correct; submit works |
| SUB-01 | submit | contract | Submit an attempt with nothing answered | 422 incomplete, missing == [q1,q2,q3]; shape {code,message,missing}; attempt stays in_progress |
| SUB-02 | submit | contract | Missing lists after each partial save (q3 only; q2 only; q1 only; q3+q2; q3 then q1) | missing is in set order: [q1,q2], [q1,q3], [q2,q3], [q1], [q2] |
| SUB-03 | submit | contract | Rejected submit leaves answers, status and results gate untouched; attempt still usable | Answers preserved, status in_progress, results 403 not_submitted, can save the rest and then submit |
| SUB-04 | submit | contract | Submit a complete all-correct attempt | 200 {attempt_id,status:submitted,score:{correct:3,total:3}} |
| SUB-05 | submit | contract | Scores for all-wrong, 2/3, 1/3 and 0/3 variants incl. each question wrong in turn | Server-computed correct/total (total always 3) |
| SUB-06 | submit | contract | AC5: client-supplied scores on submit (body {score}, {correct,total}, {score:3}, ?score=3) for an all-wrong attempt | Ignored: score is 0/3 |
| SUB-07 | submit | contract | Submit body ignored: none, 'not json', [], invalid UTF-8, 1 MB of x, answers in body, text/plain, multipart junk | Always processed as a plain submit: 200 with the true score; body answers not applied |
| SUB-08 | submit | contract | Submit twice (and three times) | 2nd+ gives 409 already_submitted; score and results unchanged |
| SUB-09 | submit | contract | Resubmit with a client score of 3/3 after a 0/3 submit | 409; results still 0/3 |
| SUB-10 | submit | contract | Submit an unknown attempt id | 404 attempt_not_found |
| SUB-11 | submit | contract | Wrong answers revised to right before submit; and right revised to wrong | Score uses the latest saved answers |
| SUB-12 | submit | contract | Submit response shape | keys attempt_id, status, score{correct,total} ints present |
| SUB-13 | submit | contract | Incomplete attempt submitted with a body claiming answers / a perfect score | Still 422 incomplete with the true missing list; nothing saved from the body |
| RES-01 | results | contract | Results of an unsubmitted attempt (empty, partial, complete-but-unsubmitted) | 403 not_submitted each, body without key/explanation |
| RES-02 | results | contract | Results of a perfect attempt, full comparison | key_version v1, 3/3, answers, per-question selected/correct_choice/correct/explanation in set order |
| RES-03 | results | contract | Results of all-wrong and mixed attempts | correct flags false/true per question; explanations and correct_choice still present |
| RES-04 | results | contract | Results fetched repeatedly; compared with submit response and GET attempt | Identical bodies; score equals submit score; GET attempt shows submitted with same answers |
| RES-05 | results | contract | Results of unknown attempt | 404 attempt_not_found |
| RES-06 | results | contract | Results use revised answers, and 'selected' equals the saved answer for every question | selected/answers reflect the final saved values |
| RES-07 | results | robustness | Results with query parameters (?include=x, ?debug=1) and trailing slash | Same body as plain results or a clean 4xx; no 5xx |
| LOCK-01 | lock | contract | Save after submit (same values, changed values, a wrong value) | 409 already_submitted; stored answers, results and score unchanged |
| LOCK-02 | lock | contract | Save after submit with an unknown question / invalid choice / empty answers | 409 (state check precedes validation) |
| LOCK-03 | lock | contract | Save after submit with a malformed body | 409 (state precedes input validation) |
| LOCK-04 | lock | contract | Status after submit via GET attempt, and PUT answers response never says in_progress again | submitted forever |
| ORD-01 | order | contract | No header + unknown attempt + garbage PUT body | 401 (header before everything) |
| ORD-02 | order | contract | No header + existing attempt + malformed / invalid PUT bodies | 401, nothing saved |
| ORD-03 | order | contract | Another student PUTs an invalid body (unknown question / invalid choice) to my attempt | 404 attempt_not_found, not 422 |
| ORD-04 | order | contract | Another student PUTs a malformed / wrong-shaped body to my attempt | 404 attempt_not_found, not 422 (ownership before input validation) |
| ORD-05 | order | contract | Another student PUTs to my SUBMITTED attempt | 404, not 409 |
| ORD-06 | order | contract | Another student asks for results of my UNSUBMITTED attempt | 404, not 403 |
| ORD-07 | order | contract | Another student submits my incomplete / complete attempt | 404, not 422 / 200; my attempt untouched |
| ORD-08 | order | contract | Owner PUTs an invalid body to own submitted attempt | 409, not 422 (state before validation) |
| ORD-09 | order | contract | Owner submits an incomplete attempt with a garbage body | 422 incomplete (body ignored) |
| ORD-10 | order | contract | Unknown attempt + invalid PUT body (with header) | 404, not 422 |
| ORD-11 | order | contract | Other student results/submit/PUT on someone's attempt that is in each state (empty, partial, complete, submitted) | Always 404 attempt_not_found |
| XS-01 | cross-student | contract | Another student GETs my attempt | 404 attempt_not_found, no answers/status in body |
| XS-02 | cross-student | contract | Another student saves to my attempt | 404; my answers unchanged |
| XS-03 | cross-student | contract | Another student submits my complete attempt | 404; I can still submit it, once |
| XS-04 | cross-student | contract | Another student asks for results of my submitted attempt | 404, body has no answers/explanations |
| XS-05 | cross-student | contract | Existence oracle: for every attempt endpoint compare not-owned vs nonexistent id (incl. same-length id), in each state | Identical status and body (code and message), so existence cannot be inferred |
| XS-06 | cross-student | contract | Two students, same set, each with attempts: no answers visible across, each sees only own | Own GET shows own answers only; foreign GET 404; new attempts empty |
| XS-07 | cross-student | robustness | Student ids that are prefixes / substrings of one another ('bob' vs 'bobby', 's1' vs 's10') | Exact match only: 404 both ways |
| XS-08 | cross-student | robustness | Enumeration probes: GET /api/attempts, /api/attempts/, /api/practice-sets/intro-se-1/attempts, /api/students/x/attempts, ?student=other | 404/405 (or redirect) and the body never contains other students' attempt ids |
| XS-09 | cross-student | robustness | Probing attempt ids: swapped case, 8-char prefix, trailing space/slash, id with %2e, uppercase | 404 for every variant (exact id match only) when requested by the owner |
| XS-10 | cross-student | robustness | Random unknown ids of many shapes (empty-ish, long, unicode, injection, path traversal, 100 random) for all endpoints | 404 attempt_not_found (documented shape) with a valid header; never 5xx; never 200 |
| LEAK-01 | leak | contract | Sweep ~60 pre-submission calls (start, GET set, GET attempt, valid/invalid PUTs, incomplete submits, early results, 401s, 404s, other-student calls) with a fully answered but unsubmitted attempt | No response contains an explanation, correct choice field/phrase, key_version or answer-key wording |
| LEAK-02 | leak | contract | invalid_choice / unknown_question messages compared across q1..q3 and several bad values | Message does not depend on which choice is correct (identical once the question id is normalised) |
| LEAK-03 | leak | robustness | Query-string probes (?debug=1, ?include_answers=true, ?show_key=1, ?admin=true, ?include=explanation, ?version=v1) on set, attempt, PUT, results | No leak; no extra fields compared to the plain response |
| LEAK-04 | leak | robustness | Privilege probes: X-Student-Id 'admin'/'teacher'/'root'/'*', extra headers X-Admin, X-Role, Authorization, X-Debug | No special rights: foreign attempt 404, results of unsubmitted 403/404, no leak |
| LEAK-05 | leak | contract | Differential: PUT/GET responses after saving the CORRECT vs a WRONG choice for q1 | Same structure (keys/types) either way: nothing reveals correctness (no score, flags, feedback) |
| LEAK-06 | leak | contract | Incomplete-submit error body in detail (every partial state) | Only code, message and missing (ids); message contains no explanation, no choice ids tied to the key |
| ERR-01 | errors | contract | Collect every documented 401/403/404/409 error and check the body | Exactly {detail:{code,message}}; right code; message a non-empty string; JSON content type |
| ERR-02 | errors | contract | Collect 422 errors: unknown_question, invalid_choice, incomplete | {detail:{code,message}} (+missing for incomplete); right codes and status 422 |
| ERR-03 | errors | robustness | Error messages for documented errors and malformed bodies: no stack traces, exception class names, file paths, or the caller's student id | Clean human-readable messages |
| ERR-04 | errors | robustness | Malformed-body 422s (default FastAPI body allowed): status/shape sanity | 400-499, JSON content type, JSON-parseable body |
| METH-01 | methods | robustness | Unsupported methods on every route (DELETE/PATCH/POST/PUT as applicable, with valid auth and body) | 404/405; the attempt and the set are unchanged and still readable afterwards |
| METH-02 | methods | robustness | HEAD and OPTIONS on all routes; HEAD by non-owner / no header | No 5xx; HEAD/OPTIONS never 200 for someone else's attempt; no leak |
| STATE-01 | state | contract | GET attempt after each action (start, save, failed submit, submit) | Read-your-writes; answers contain only saved question ids (no null placeholders) |
| STATE-02 | state | contract | Full lifecycle then replay every endpoint | Each endpoint answers per the state machine |
| STATE-03 | state | robustness | All successful responses use a JSON content type | application/json |
| CONC-01 | concurrency | contract | 25 simultaneous submits on one complete attempt (2/3 score) | Exactly one 200; all others 409 already_submitted; no 5xx; results consistent |
| CONC-02 | concurrency | robustness | Simultaneous submits by the owner and 10 other students on the same attempt | Owner exactly one 200 or 409 combos; every other student 404; nothing changes for them |
| CONC-03 | concurrency | robustness | 30 simultaneous saves of different questions on one attempt | All 200 and no lost update: all three answers stored |
| CONC-04 | concurrency | robustness | 60 simultaneous attempt creations (some by the same student) | All 201, all ids unique, all independent |
| CONC-05 | concurrency | robustness | 20 simultaneous submits on an INCOMPLETE attempt, then complete and submit it | All 422 incomplete; attempt not locked; later submit succeeds |
| CONC-06 | concurrency | robustness | 12 different attempts submitted simultaneously with different answers | Each gets its own true score; no cross-talk |
| CONC-07 | concurrency | robustness | 30 simultaneous saves to the same question with values a/b/c | No 5xx; the final stored value is one of the sent values and equals GET |
| CONC-08 | concurrency | contract | Save racing a submit. With --slow: the named function is delayed 0.3 s, save starts, 0.1 s later submit starts. Without --slow: 40 simultaneous save+submit pairs (kind reported as robustness) | Final stored state matches what submit reported: a save that succeeded before the submit counts in the score; one after gets 409 and leaves answers unchanged |

### Why each category matters

- **identity**: The header is the only identity; every access decision rests on reading it exactly and strictly.
- **set**: AC1: the set is the one public surface and must never carry the key.
- **start**: AC2/AC10: attempt creation, unguessable ids, independence.
- **save**: AC3: saving, merging, validation, atomic rejection and hostile bodies.
- **submit**: AC4/AC5: completeness check, ordering of 'missing', server-side scoring.
- **results**: AC7: what is released after submission and exactly when.
- **lock**: AC6: nothing changes after submission.
- **order**: Plan check order: 401, then 404, then 409/403, then 422. Wrong order leaks existence or state.
- **cross-student**: AC9: no access to, and no knowledge of, other students' attempts.
- **leak**: AC8: no key or explanation in any pre-submission response, including errors.
- **errors**: Plan: one error body shape for every documented error.
- **methods**: Unsupported methods must not mutate, expose or crash.
- **concurrency**: Exactly-once submit and consistent state under simultaneous requests.
- **state**: Read-your-writes and state-machine consistency.

## Planted bugs (reference/main.py, `MUTANT=<name>`)

| Bug | Description | Caught by |
|---|---|---|
| `no_ownership_check` | Any student can read, change, submit and fetch results of any attempt. | ID-05, ID-06, ID-09, ID-12, ORD-03, ORD-04 (+14) |
| `results_before_submit` | Results are returned for unsubmitted attempts (no 403). | START-03, SUB-03, RES-01, LEAK-01, LEAK-03, LEAK-04 (+2) |
| `leak_set_correct` | GET set marks the correct choice (choice.correct = true). | SET-02, SET-05, LEAK-01, LEAK-03, LEAK-04 |
| `leak_set_explanation` | GET set includes the explanation for each question. | SET-02, SET-05, LEAK-01, LEAK-03, LEAK-04 |
| `leak_put_key_version` | PUT answers response includes key_version. | SAVE-01, LEAK-01, LEAK-03, LEAK-05 |
| `leak_error_invalid_choice` | invalid_choice error message states the correct answer. | SAVE-06, SAVE-09, SAVE-10, LEAK-01, LEAK-02 |
| `leak_error_incomplete_explanation` | incomplete error message includes a hint copied from the explanation. | LEAK-01, LEAK-06 |
| `leak_attempt_get_score` | GET attempt (in progress) includes a running score (reveals correctness). | START-01, START-07, LEAK-05 |
| `leak_query_debug` | GET attempt?debug=1 returns the answer key (backdoor). | LEAK-03 |
| `admin_bypass` | Student id 'admin' bypasses ownership and the not_submitted gate. | LEAK-04 |
| `not_owned_403` | Another student's attempt gives 403 instead of 404 (reveals existence). | ID-05, ID-06, ID-09, ID-12, ORD-03, ORD-04 (+14) |
| `not_owned_distinct_message` | 404 for another student's attempt has a different message than for a missing one. | XS-05 |
| `echo_student_in_404` | 404 attempt_not_found message echoes the caller's student id. | ERR-03 |
| `sequential_ids` | Attempt ids are zero-padded sequential integers (8 digits). | START-04, START-05 |
| `short_ids` | Attempt ids are only 6 characters long. | START-01, START-04 |
| `id_embeds_student` | Attempt id embeds the student id. | ID-07, ID-12, START-05 |
| `id_prefix_match` | An attempt id is resolved by prefix, so its first 8 characters work. | XS-09 |
| `id_case_insensitive` | Attempt ids are matched case-insensitively. | XS-09 |
| `order_422_before_404` | Body validation (422) runs before ownership/existence (404). | LOCK-02, LOCK-03, ORD-03, ORD-04, ORD-05, ORD-08 (+1) |
| `order_422_before_409` | Body validation (422) runs before the submitted-state check (409). | LOCK-02, LOCK-03, ORD-08 |
| `order_404_before_401` | Unknown attempt id gives 404 even when the student header is missing. | ID-13, ORD-01 |
| `order_403_before_404` | Results for someone else's unsubmitted attempt give 403 not 404. | ORD-06, ORD-11, XS-05, LEAK-04 |
| `order_409_before_404` | Saving to someone else's submitted attempt gives 409 not 404. | ORD-05, ORD-11, XS-05 |
| `missing_reversed` | The 'missing' list is in reverse set order. | SUB-01, SUB-02, SUB-13 |
| `incomplete_no_missing` | The incomplete error has no 'missing' field. | SUB-01, SUB-02, SUB-13, LEAK-06, ERR-02 |
| `client_score_trusted` | A score sent in the submit body replaces the computed score. | SUB-06 |
| `submit_body_fills_answers` | Answers sent in the submit body are merged into the attempt before checking. | SUB-07, SUB-13 |
| `partial_save_on_reject` | Valid entries before an invalid one are kept when a request is rejected. | SAVE-07, SAVE-08, SAVE-13 |
| `submit_allows_incomplete` | Submit succeeds with unanswered questions (counted wrong). | SAVE-15, SUB-01, SUB-02, SUB-03, SUB-13, ORD-09 (+6) |
| `double_submit_ok` | A second submit returns 200 again instead of 409. | SUB-08, SUB-09, ERR-01, STATE-02, CONC-01, CONC-02 |
| `save_after_submit_ok` | Answers can still be changed after submission. | LOCK-01, LOCK-02, LOCK-03, ORD-08, ERR-01, STATE-02 (+1) |
| `failed_submit_locks` | A rejected (incomplete) submit still marks the attempt submitted. | SUB-01, SUB-03, LEAK-01, STATE-01, STATE-02, CONC-05 |
| `failed_submit_clears_answers` | A rejected (incomplete) submit wipes the saved answers. | SUB-03, SUB-13, STATE-01, CONC-05 |
| `non_atomic_submit` | Submit checks state, yields, then writes: concurrent submits can all succeed. | CONC-01, CONC-02 |
| `non_atomic_save` | Save checks state in the route, then writes later without re-checking. | CONC-08 |
| `lost_update_save` | Save merges onto a stale snapshot: concurrent saves lose updates. | CONC-03 |
| `replace_answers` | PUT replaces all saved answers instead of merging. | SAVE-03, SAVE-11, SAVE-20, SUB-02, SUB-03, SUB-11 (+5) |
| `student_lower` | Student ids are lower-cased, so 'Alice' is 'alice'. | ID-06 |
| `student_strip` | Student ids are stripped, so ' alice ' is 'alice'. | ID-05 |
| `empty_header_ok` | An empty X-Student-Id is accepted as a student. | ID-02, ID-10 |
| `set_requires_header` | Reading a set demands the student header (401 without). | ID-11, SET-01, SET-02, SET-03, ERR-01, METH-01 (+1) |
| `start_no_header` | Starting an attempt without a header works (anonymous student). | ID-01, ID-02, ID-03, ID-14, ERR-01 |
| `start_unknown_set_ok` | Starting an attempt on an unknown set returns 201. | START-02, ERR-01 |
| `start_reuses_attempt` | Starting again returns the student's existing in-progress attempt. | START-03, START-04, CONC-04 |
| `accept_unknown_choice` | Any string is accepted as a choice id. | SAVE-06, SAVE-07, SAVE-13, LEAK-01, LEAK-02, ERR-02 |
| `accept_unknown_question` | Unknown question ids are accepted and saved. | SAVE-05, SAVE-07, SAVE-13, ERR-02 |
| `null_answer_accepted` | A null answer value is silently accepted (200) and ignored. | SAVE-09 |
| `type_500` | Non-object bodies / wrong-typed 'answers' crash with a 500. | SAVE-10, ERR-04 |
| `status_trust_put` | A 'status' field in the PUT body can mark the attempt submitted. | SAVE-15 |
| `error_shape_flat_409` | 409 errors use {"detail": "text"} instead of the code/message object. | SUB-08, SUB-09, LOCK-01, LOCK-02, LOCK-03, ORD-08 (+3) |
| `error_shape_no_message_401` | 401 errors omit 'message'. | ERR-01 |
| `incomplete_status_400` | The incomplete error returns status 400 instead of 422. | SAVE-15, SUB-01, SUB-02, SUB-03, SUB-13, ORD-09 (+4) |
| `score_ignores_q1` | Scoring never counts q1 (off-by-one over the questions). | SUB-03, SUB-04, SUB-05, SUB-07, SUB-11, RES-02 (+4) |
| `results_reversed` | Results questions are in reverse set order. | RES-02, RES-03, RES-06 |
| `results_correct_always_true` | Results 'correct' flag is true whenever an answer exists. | RES-03, RES-06 |
| `results_explanation_swapped` | Results swap the explanations of q2 and q3. | RES-02, RES-03, RES-06 |
| `results_no_key_version` | Results omit key_version. | RES-02, RES-03, RES-06 |
| `delete_attempt_route` | DELETE /api/attempts/{id} exists and deletes the attempt. | METH-01 |
| `list_attempts_route` | GET /api/practice-sets/{id}/attempts lists every student's attempt ids. | XS-08, METH-01 |
| `start_status_200` | Starting an attempt returns 200 instead of 201. | ID-04, ID-05, ID-06, ID-10, ID-12, ID-15 (+88) |
| `set_case_insensitive` | Set ids are matched case-insensitively. | SET-03, START-02 |
| `traceback_in_error` | Malformed-body errors expose the exception class name. | ERR-03 |

## Self-check results

- Clean reference with `--slow main:do_save`: 115 scenarios, failures: none.
- Clean reference without `--slow`: 115 scenarios, failures: none.
- Planted bugs caught (at least one scenario fails, run with `--slow main:do_save`): **62 of 62**.
- Without `--slow`, `non_atomic_save` is still caught (CONC-08 repeated simultaneous pairs) and `non_atomic_submit` is caught by CONC-01/CONC-02.
- Note: several bugs (e.g. `start_status_200`) trip many scenarios because setup helpers assume 201; the 'Caught by' list is therefore noisy for such bugs.
