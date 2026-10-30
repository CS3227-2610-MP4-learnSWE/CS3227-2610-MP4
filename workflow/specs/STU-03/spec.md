# Spec: STU-03 AI study companion (first slice: hint, explain, help)

Status: Approved by the user on 2026-10-30 ("ready to build"), with all decisions confirmed (see "Decisions made" and "Further decisions a to j"). Nothing here has been built or tested yet. Slice of STU-03 covering parts of US-STU-03-01..05; the parts left out are listed under "Out of scope".

## Goal
A student can ask the study companion for guidance from any student page. Before a practice set is successfully submitted the companion gives hints and guiding questions only; after the student's own successful submission it explains that attempt in full; elsewhere it gives short app help and general software-engineering explanations. The server alone decides which of the three behaviours applies, and does not rely on the prompt to keep answers back.

## Behaviour

### One endpoint, three server-selected modes
The widget sends one message to one endpoint (`POST /api/companion/messages`, contract in `plan.md`). The request never names a mode. The server picks it from the page context the client reports and from state it looks up itself.

| Mode | When the server chooses it | What the model is given | What the model may do |
|---|---|---|---|
| Hint | The page is a practice set and the student has no attempt on it, or has an attempt that is not successfully submitted. Also forced when the message matches a practice question (see below). | The fixed rules, the set's question text and code only (no answer choices), the student's message and recent chat. No answer key, no explanation, no key version, no saved answers. | A short concept note plus one guiding question. Never state or confirm the correct choice, say that a specific choice is right or wrong, or give a full solution or equivalent solution code (see "What counts as a leak"). |
| Explain | The page is a practice set, and the context names an attempt that this student owns and that the server has recorded as submitted, and the student has no newer unsubmitted attempt on the same set. | The fixed rules, that attempt's questions with the student's choice, the correct choice, the teacher-approved explanation and the key version, the student's message and recent chat. | Explain the student's mistakes and the correct reasoning for that attempt. |
| Help | Any other page, when the message does not match a practice question. | The fixed rules, a fixed trusted app-help text written by us (from `docs/UserGuide.md`), the student's message and recent chat. No practice content at all. | Say how to use the app and explain general software-engineering concepts. Say plainly that this is general help, not course material; never invent a source or a lesson; decline off-topic requests. |

### Pasted practice questions
A student may paste a practice question into a non-practice page. The server compares the message with the practice questions (matching rule: decision 2). A match forces Hint mode for that request, with the matched question's text and code (no choices) as the only practice content, whatever page the request came from. In Explain mode a match with a question outside the named attempt's set also forces Hint mode.

### What counts as a leak
A hint that helps will narrow the problem a little, so "no information" is not the standard. The standard is that the companion never gives the final answer.
- Blocked (hard rule): stating the correct choice by letter or text; confirming a choice the student names; saying that a specific choice is right, correct, wrong or incorrect; giving a full solution or equivalent solution code. A request such as "which two are definitely wrong?" is met with a guiding question, not a ruling on options.
- Allowed: explaining the underlying concept, asking what the student has tried, and pointing at what to compare or consider, even if that makes some choices look more or less likely.

Three layers support this, none of them enough alone: (1) hint context holds the question stem only, so the model has no choices to rank; (2) the fixed rules ask for a short concept note plus one guiding question, as a prompt instruction (the server does not enforce the shape); (3) the deterministic server leak check (AC9). Residual risk is stated under "Security and AI safeguards".

### Reply handling
- Replies are shown as plain text only, never as HTML or markdown.
- Before a Hint-mode (and Help-mode) reply is returned, the server checks it for leaked answers (decisions 1 and 3 fix how strict that is and what happens on a block).
- If the model service fails or a limit is reached, the reply is an error; the widget keeps the typed question so the student can retry.

### Widget (frontend)
The existing floating widget (`StudyCompanion.tsx`) keeps its current behaviour: bottom-right icon, minimise keeps history and draft, Escape minimises and returns focus to the icon, the clear control empties history and draft, reload clears everything, accessible labels, light, dark and mobile layouts. New: sending calls the endpoint instead of showing the fixed preview reply; a visible "thinking" state; send is disabled while a request is in flight; failures show a plain-words message and keep the draft. The widget sends the page type and, only when the student is looking at a submitted practice result, that attempt's id. The "No AI connected" and "Preview" wording is replaced by wording that is true once this ships.

## Acceptance criteria
Criteria copied or narrowed from the user stories carry their story reference. All backend and widget criteria are tested with a fake LLM; none calls the real service.

### Mode selection and answer release (server)
- [ ] AC1: The request has no mode field. A `mode` (or similar) field sent by the client is ignored; the mode is a pure function of page context and server-side attempt state. (US-STU-03-02, -03)
- [ ] AC2: Practice page, no attempt id: Hint mode. Practice page with an attempt id of this student's `in_progress` attempt: Hint mode. In both, the messages sent to the model contain no answer choices, correct choice, explanation, key version or saved answer (only question text and code), and the tests assert this by searching everything the fake LLM received. (US-STU-03-02, -05)
- [ ] AC3: Explain mode only when the attempt is this student's own, the server records it as `submitted`, and the student has no newer `in_progress` attempt on the same set. The context uses that attempt's questions, the student's choices and the key of its key version. (US-STU-03-03)
- [ ] AC4: A previous submission never unlocks a new unsubmitted attempt: with a submitted attempt A and a later in-progress attempt B on the same set, a request naming A or B gets Hint mode and no key in context. (US-STU-03-03)
- [ ] AC5: Another student's attempt id, or an unknown one, gives 404 `attempt_not_found` (same body for both), and no model call is made. (US-STU-03-03, SHR-01)
- [ ] AC6: Any other page gives Help mode: the model gets the fixed help text and no practice content.
- [ ] AC7: A message that matches a practice question (normalised, rule per decision 2) sent from a Help page, or from an Explain page for a question outside the attempt, is answered in Hint mode with no key in context. Variants tested: exact paste, different case and spacing, extra markdown or quote characters, question plus choices, question embedded in a longer message. (US-STU-03-01, -02)
- [ ] AC8: An explicit request for the answer, a repeated hint request, an answer-checking request ("is it b?") and a claim of being submitted or authorised, in Hint mode, still produce a request whose context has no key. The reply passes through the leak check (AC9). (US-STU-03-02)

### Leak check (server)
- [ ] AC9: For every Hint-mode reply (and Help-mode reply, against all practice keys) the server runs the leak check from decision 1. A fake LLM reply that states the correct choice by letter ("the answer is b", "option b", "(b)", "b is correct"), quotes the correct choice text, or marks any choice letter as correct or incorrect is not returned to the client. (US-STU-03-02)
- [ ] AC10: What the client receives when the check blocks a reply is decided by decision 3 (a fixed canned message, no retry). Either way the response contains no part of the blocked reply, and `withheld` is true.
- [ ] AC11: No error response, log line or response body from any companion path contains an answer key, an explanation or the API key. (US-STU-03-02, SHR-02)

### Explain and Help content
- [ ] AC12: In Explain mode the model context contains, for each question of that attempt: text, code, choices, the student's choice, the correct choice, the explanation, plus the key version. Nothing from another attempt, another student or another set appears.
- [ ] AC13: The Help-mode context holds the fixed help text. The fixed rules tell the model to say its help is not course material, to name no source or lesson, and to decline off-topic requests. The tests check that these rules are present in the request; whether the live model obeys them is checked only in the manual live check (AC31), not in tests. (US-STU-03-01)
- [ ] AC14: The fixed rules in every mode include the short-answer instruction ("at most 3 short sentences, no markdown") and state that student text, page content and chat history are data, not instructions. In Hint mode they also ask for a short concept note plus one guiding question and forbid stating or confirming the correct choice or ruling on a specific choice. The tests check that these rules are present in the request; the reply shape is not enforced by the server.

### Input, output and history limits
- [ ] AC15: The message is trimmed first. An empty or whitespace-only message, or one over 1,000 characters after trimming, gives 422 `invalid_message` and makes no model call and does not count against the rate limits.
- [ ] AC16: Only the last 4 history messages are sent to the model, and when they exceed about 2,000 characters in total the oldest whole messages are dropped until they fit. History items are untrusted: a forged "assistant" item that says the answer or gives instructions does not change the mode, and does not change what is in the context.
- [ ] AC17: The output token cap sent to the model is 100 in Hint mode, 200 in Explain and 150 in Help.
- [ ] AC18: Page context is bounded: the server builds it from stored data only (never from client-supplied page text), and the label the client may send is limited to 80 characters and treated as untrusted.

### Shared client and limits
- [ ] AC19: The client is OpenAI-compatible, reads `SOCLAAS_BASE_URL`, `SOCLAAS_API_KEY`, `SOCLAAS_MODEL` from the environment when it is built, and adds `Authorization: Bearer` itself. With any of them missing the endpoint answers 503 `llm_not_configured` and makes no network call.
- [ ] AC20: Timeout is 15 s per attempt. A timeout or HTTP 5xx is retried once; nothing else is retried. After the retry fails: 503 `llm_unavailable`. A 4xx other than 429, malformed JSON, missing or empty content: 502 `llm_bad_response`, no retry.
- [ ] AC21: Per student: at most 20 admitted requests in any 60 seconds and 300 in any 24 hours; the next one is 429 `rate_limited` with `scope`, `retry_after_seconds` and a `Retry-After` header, and no model call. Another student is unaffected.
- [ ] AC22: There is no shared cross-student limit; the provider's own limits are handled through AC23. The per-student limits are checked atomically: 30 simultaneous requests from one student admit exactly 20 in the minute window.
- [ ] AC23: An upstream 429 gives our 429 `llm_busy` with a plain message and `retry_after_seconds` (from the provider's `Retry-After` when present, otherwise 30). It is not retried.
- [ ] AC24: The API key is never logged, returned, put in an exception message or included in any error body (tested by making the fake transport fail with the key in the request and searching all outputs and captured logs).

### Auth
- [ ] AC25: Missing or blank `X-Student-Id`: 401 `missing_student`, before anything else. The id is trimmed as in STU-02.
- [ ] AC26: Unknown `set_id`: 404 `set_not_found`. A context that is inconsistent (practice page without a set id, attempt belonging to a different set than `set_id`): 422 `invalid_context`.

### Frontend widget
- [ ] AC27: Sending shows the student's message, a visible pending state and then the reply, rendered as plain text. A reply containing `<img src=x onerror=...>` or markdown stays literal text. Send is disabled while a request is pending.
- [ ] AC28: On any failure (network, timeout, 401/404/422/429/502/503) the widget shows a plain-words message chosen from fixed page text (not the raw server body), keeps the typed question in the draft, and a second send retries. A 429 message says how long to wait when `retry_after_seconds` is given. (US-STU-03-01)
- [ ] AC29: The widget reports the page type and, on a practice page whose results are shown, the current attempt id; after "Start another attempt" it reports no attempt id. It never sends a mode, a score or an answer key. Existing widget behaviour (minimise keeps history and draft, Escape restores focus to the icon, clear, reload clears, labels, light/dark/mobile) still passes its existing tests. (US-STU-03-04)
- [ ] AC30: The 10 s request timeout of the existing API client is not applied to the companion call: the companion call allows 40 s (15 s timeout, one retry, plus margin).

### Process
- [ ] AC31: CI and all automated tests make no live LLM call and need no key. One manual live check (a few Hint, Explain and Help calls and one pasted-question call) is run only by the user, with approval and a key from the local ignored `.env`; its outcome is recorded in `workflow/security/test-log.md` and `logs/`, not in the tests.
- [ ] AC32: `src/backend/.env.example` lists the three variable names with no values. `.env` stays ignored.
- [ ] AC33: `docs/UserGuide.md` and `docs/DeveloperGuide.md` describe only what works after this slice, including the limits (20 per minute, 300 per day) and the stated residual leak risk; they no longer say "No AI connected" for the companion. The fixed help text matches the user guide.
- [ ] AC34: `uv run pytest -q`, `npm run typecheck`, `npm run lint`, `npm run format:check` and `npm test` pass and CI is green.
- [ ] AC35: After the build passes verification, a planned iterative live-testing phase (user-run, with approval each time, key from the local ignored `.env`) uses realistic student questions and the experiment's attack prompts to look for answer leaks, over-refusal and thin explanations. Findings go to `workflow/security/test-log.md` and `logs/`; fixes or setting changes are separate approved changes. No test or CI step makes live calls.

## Out of scope
- Retrieval from teacher-published lessons with source links (needs STU-01). The grounding and source-reference criteria of US-STU-03-01 and US-STU-03-05 are therefore not met in this slice; the companion says its help is general, not course material.
- Page context from lesson content (only practice sets and the fixed help text are context).
- Chat history that survives reload, cross-device or per-account persistence (US-STU-03-04 history scoping beyond the browser session).
- Streaming replies.
- Real login or role checks (the `X-Student-Id` header stays a placeholder until SHR-01).
- Any LLM other than the SoC LLM.
- A shared cross-student rate limit, and any coordination with the Teacher and Admin owners. The client (`llm_client.py`) is still written as a generic, single-purpose module with no student-specific names, so others can reuse it if they choose; nothing in this slice depends on them doing so.
- Teaching preferences (OPT-02), usage analytics and AI usage monitoring (ADM-01, ADM-06).
- Code execution.

## Security and AI safeguards
Threat-model rows covered: prompt injection, answer leakage, cross-user access, unsafe rendered output, quota exhaustion (`workflow/security/threat-model.md`).

- Server enforcement, not prompts. The mode and the context are built on the server from the attempt store and the practice data. In Hint and Help mode the key and explanations are never read into the model context (`practice_logic.py` remains the only reader of the key for results; the companion reads the key only to build Explain context and to run the leak check).
- Ownership. The attempt named in the context is looked up with the student's id; another student's or an unknown attempt gives the same 404. Check order: header (401), set and attempt existence and ownership (404), context consistency and input validation (422), rate limits (429), model call (502/503).
- Answer release. Explain needs a server-verified `submitted` status of the student's own attempt. A new unsubmitted attempt is never unlocked by an older submission (AC4).
- Prompt injection. Student text, history and any page label are data. They are kept apart from the fixed rules (rules in the system message; untrusted text in clearly delimited user content). The experiments found that fake system lines in a message were sometimes obeyed, so nothing the student writes can change the mode or the context; only the server can.
- Residual risk, stated plainly. The experiments (`workflow/experiments/stu03-caps/RESULTS.md`, small samples) showed prompts alone leaked or narrowed the answer in about a third to a half of attack prompts in Hint mode, a pasted question in Help mode was answered in full, and an exact-text check caught only half of the problem replies. The server-side checks in this spec reduce that and do not remove it. A reply that hints strongly by paraphrase or by describing the right concept can pass a letter-and-text check, and the model can still rule out an option in words that avoid letters and quoted text. Narrowing at the concept level is allowed by design (see "What counts as a leak"). The spec does not claim hints cannot narrow an answer; it claims the server never puts the key or the answer choices in context before submission and blocks replies that state or rule on a choice by letter or text. No further defence (such as a second judging call) is added in this slice (decision 1).
- Output. Replies are rendered as text nodes; HTML and markdown are not interpreted. Reply length is bounded by the output cap and a character ceiling.
- Concurrency. (a) The rate limiters are atomic (a lock around check-and-record), so parallel requests cannot exceed the limits. (b) The mode is decided once per request from the state at that moment. If a submit arrives while a Hint request is running, that request stays a Hint-level reply (the safe direction); the next request sees `submitted`. An attempt never goes from `submitted` back to `in_progress`, so a request cannot become less restricted mid-flight.
- Normalisation. Student id: trimmed, as in STU-02. Message: trimmed before length checks. For question matching and the leak check, text is compared after Unicode NFKC normalisation, case folding, collapsing whitespace and removing markdown and quote punctuation. Identifiers (set id, attempt id) are exact opaque strings and are not normalised.
- Secrets. The key comes from the environment only, never appears in code, logs, error bodies, responses or tests. Dev and prod use separate keys supplied by deployment settings (not decided here).
- Logging. A companion request may log mode, outcome code, latency and token usage if the provider returns it; it does not log the message, history, reply or any key (item h).
- Limits are in memory per process (one backend instance). A restart resets them, and several instances would each have their own counts.

### What the numbers are based on
Measured in the live experiments (`RESULTS.md`, 347 calls, 3 questions per mode, easy question set, one model alias `default`): the short-answer instruction and output caps (hint 100, explain 200, help 150, which add margin over the smallest passing caps 60, 150, 100; explain 200 itself was not tested, 150 and 250 passed 9 of 9), latency (p50 about 1.0 s, p95 about 2.3 s, max 3.8 s in phases 1 to 5) behind the 15 s timeout, cost per call (about 0.00015 to 0.00019 USD with 4 history messages), and the leak and injection behaviour above.

Our choices, not measured: input length of 1,000 characters (a usability judgement), per-student limits of 20 per minute and 300 per day (the experiments ran about 60 calls per minute for several minutes without a 429, but the provider's policy limits are unknown), 4 history messages (kept for usefulness in a continuing conversation; no benefit was measured because the test questions were independent), the 2,000-character history ceiling, one retry on timeout or 5xx, the 12,000-character total request ceiling, and the pasted-question matching threshold. No provider rate limit was seen in the experiments, so the real provider limits are unknown.

## Decisions made
Decided by the user in discussion (the plan is written for these):
1. Leak defence: layers 1 + 2 + 3 (stem-only hint context, a fixed reply shape as a prompt instruction, a deterministic server letter/text check). No second LLM judge call for now; it can be measured and added later. Hard rule and allowed behaviour as under "What counts as a leak". "Narrowed it down" is not counted as a leak; stating or confirming is.
2. Pasted-question detection (rule 1b): compare after normalisation (NFKC, case-fold, collapse whitespace, strip markdown, quotes and punctuation) against the questions of every practice set, not only the student's open attempts, because the practice page creates its attempt only on first submit (STU-02-frontend). A match is: the normalised question text (and code, if any) is contained in the message; or at least two normalised choice texts are; or at least 80% of the question text's words appear. The 80% threshold is our choice and unmeasured; paraphrases below it are answered in Help mode, where the Help-mode leak check against all keys is the second line of defence.
3. When the leak check blocks a reply: return a fixed canned message (200 with `withheld: true`), no retry. A retry doubles cost and is another sample that can leak.
4. Limits: per student only, 20 per minute and 300 per day (sliding windows, in memory). No shared cross-student limit; the provider enforces its own, and a provider 429 gives `llm_busy`. At about 0.00015 USD per call, 300 calls is about 0.045 USD per student per day (arithmetic from the measured call cost, not measured use).
5. Scope of the client: student-specific scope, but written as a generic single-purpose module (`llm_client.py`, no student-specific names). No coordination with the Teacher and Admin owners is part of this slice; telling them it exists is optional.

## Further decisions a to j
Confirmed by the user in discussion.
- a. Limit accounting: a request counts once admitted (after 401/404/422 checks), including ones that later fail or are blocked; an internal retry is part of the same call.
- b. Hint context: all questions of the set (question text and code only, no choices), since the page does not say which question the student is looking at; the student says which one they mean in their message. A focus-question field can be added later. Bounded by the 12,000-character request ceiling.
- c. A student can call the API with an old submitted attempt id on purpose. The key was already released to them by the results endpoint, so this adds no new exposure; the "no newer in-progress attempt" rule in AC3 handles the retry case. Needs a store method to list a student's attempts (plan).
- d. History is held and sent by the browser, so it is forgeable. Accepted: it is untrusted and cannot change mode or context. Server-side history waits for SHR-01 and persistence.
- e. A reply cut off by the output cap (`finish_reason` `length`) is returned as is; trimming to the last full sentence is not specified. The experiments passed at the chosen caps, so this should be rare.
- f. Sliding 60 s and 24 h windows in memory, not calendar days.
- g. Over-refusal (legitimate requests declined) and the quality of short Explain replies ("accurate but thin") were not measured. After the feature works, iterative live testing (AC35) looks for leaks, over-refusal and thin replies, and may adjust the unmeasured settings (limits, match threshold, history, wording).
- h. Logging: metadata only (mode, outcome code, latency, token usage if returned); no message or reply text. Usage counts for ADM-06 are a later feature.
- i. The fixed help text is written by us from `docs/UserGuide.md` and claims only what works; the developer writes it and the verifier checks it.
- j. The pasted-question rule also forces Hint mode on a Help page for a student who has already submitted that set; full explanations come from the practice results page.
