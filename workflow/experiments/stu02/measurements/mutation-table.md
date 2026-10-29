| Planted bug | A | A2 | B | baseline | grader |
|---|---|---|---|---|---|
| Set response includes each question's explanation | caught | caught | caught | caught | caught |
| Any student can use any attempt | caught | caught | caught | caught | caught |
| Another student's attempt gives 403 (reveals it exists) instead of 404 | caught | caught | caught | caught | caught |
| Missing X-Student-Id is accepted as 'anonymous' | caught | caught | caught | caught | caught |
| Saving replaces all answers instead of merging | caught | caught | caught | caught | **missed** |
| Unknown question ids are accepted | caught | caught | caught | caught | caught |
| Choices that do not belong to the question are accepted | caught | caught | caught | caught | caught |
| A rejected save still stores its valid answers | caught | caught | caught | caught | caught |
| Answers can be changed after submission | caught | caught | caught | caught | caught |
| An attempt can be submitted twice | caught | caught | caught | caught | caught |
| Submitting with questions unanswered is accepted | caught | caught | caught | caught | caught |
| The missing list is not in set order | caught | caught | caught | caught | caught |
| A score sent by the client is trusted | caught | caught | caught | caught | caught |
| Results are shown before submission | caught | caught | caught | caught | caught |
| Score counts one extra correct answer | caught | caught | caught | caught | caught |
| Results report every answer as correct | caught | caught | caught | caught | caught |
| The 'incomplete' error message reveals the correct answers | **missed** | caught | caught | caught | **missed** |
| The not_submitted error body includes the saved answers' correctness | **missed** | caught | caught | caught | caught |
| Set response includes key_version | caught | caught | caught | caught | caught |
| Another student's attempt gives a different 404 body than an unknown one | caught | caught | caught | caught | caught |
| Attempt ids are sequential numbers (guessable) | caught | caught | caught | caught | caught |
| Attempt ids are 4 characters | caught | caught | caught | caught | caught |
| A whitespace-only X-Student-Id is accepted | **missed** | caught | **missed** | caught | **missed** |
| Ownership ignores letter case | **missed** | caught | caught | caught | **missed** |
| Saving {} is rejected instead of being a no-op | **missed** | caught | caught | caught | **missed** |
| The missing list includes answered questions | caught | caught | caught | caught | caught |
| Body errors are checked before ownership | **missed** | caught | caught | caught | **missed** |
| Submit scores the submitted body's answers, not the saved ones | caught | caught | caught | caught | **missed** |
| Save and submit are not atomic (race) | **missed** | caught | caught | caught | **missed** |
| **Caught** | **22/29** | **29/29** | **28/29** | **29/29** | **21/29** |

Tests excluded because they fail on the neutral reference (spec-silent details): A: 0; A2: 4; B: 1; baseline: 1; grader: 0
