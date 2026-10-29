| Id | Area | Scenario | A | A2 | B | B-fixed | baseline |
|---|---|---|---|---|---|---|---|
| E01 | identity | Start attempt with no X-Student-Id | pass | pass | pass | pass | pass |
| E02 | identity | Start attempt with whitespace-only id | pass | pass | pass | pass | pass |
| E03 | identity | Id with spaces at start, then same id without spaces | pass | **fail** | **fail** | pass | **fail** |
| E04 | identity | Same letters, different case, is a different student | pass | pass | pass | pass | pass |
| E05 | identity | 10,000-character student id | pass | pass | pass | pass | pass |
| E07 | identity | Two X-Student-Id headers: owner's id plus another | pass | pass | pass | pass | pass |
| E08 | lookup | Set id in a different case | pass | pass | pass | pass | pass |
| E09 | lookup | Start attempt on an unknown set | pass | pass | pass | pass | pass |
| E10 | lookup | 5,000-character attempt id | pass | pass | pass | pass | pass |
| E11 | lookup | Attempt id with quotes and percent signs | pass | pass | pass | pass | pass |
| E12 | input | Empty answers object | pass | pass | pass | pass | pass |
| E13 | input | Extra top-level field next to answers | pass | pass | pass | pass | pass |
| E14 | input | Answer value is a number; nothing saved | pass | pass | pass | pass | pass |
| E15 | input | Answer value is null; nothing saved | pass | pass | pass | pass | pass |
| E16 | input | Answer value is a list; nothing saved | pass | pass | pass | pass | pass |
| E17 | input | Question id in upper case (Q1) | pass | pass | pass | pass | pass |
| E18 | input | Choice id in upper case (A) | pass | pass | pass | pass | pass |
| E19 | input | 1,000 unknown question ids in one save | pass | pass | pass | pass | pass |
| E20 | input | Malformed JSON body | pass | pass | pass | pass | pass |
| E21 | input | No body at all | pass | pass | pass | pass | pass |
| E22 | input | Deeply nested JSON (5,000 levels) | pass | pass | pass | pass | **fail** |
| E23 | input | Form-encoded body instead of JSON | pass | pass | pass | pass | pass |
| E24 | order | Another student's attempt with a malformed body | **fail** | pass | **fail** | **fail** | pass |
| E25 | order | Unknown attempt with a malformed body | **fail** | pass | **fail** | **fail** | pass |
| E26 | order | Submitted attempt with a malformed body | **fail** | pass | **fail** | **fail** | pass |
| E27 | submission | Submit with answers in the body (must be ignored) | pass | pass | pass | pass | pass |
| E28 | submission | Save after submit is refused and changes nothing | pass | pass | pass | pass | pass |
| E29 | concurrency | 10 simultaneous submits: exactly one succeeds | pass | pass | pass | pass | pass |
| E30 | concurrency | Save racing a submit cannot change a submitted attempt | pass | pass | **fail** | pass | **fail** |
| E31 | privacy | Another student reading a submitted attempt's results | pass | pass | pass | pass | pass |
| E32 | methods | DELETE on an attempt | pass | pass | pass | pass | pass |
| E33 | privacy | No answer or explanation in any response before submission | pass | pass | pass | pass | pass |
| E34 | robustness | No server error (5xx) in any response | pass | pass | pass | pass | **fail** |
| E35 | consistency | Every error body has the documented {code, message} shape | **fail** | pass | **fail** | **fail** | **fail** |
| | | **Passed** | **30/34** | **33/34** | **28/34** | **30/34** | **29/34** |
