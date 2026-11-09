# ADM-01 privacy amendment — approval proposal

Status: APPROVED, 2026-11-10. The user selected option 1 after the plain-language explanation, including the stated detection limits and loss of factual-accuracy grading without context. This amendment overrides conflicting privacy/eligibility/API/UI clauses in the original spec/plan and authorises implementation. Root records the handoff and usage.

## Decision recommended for approval

Approve the bounded English local privacy gate below: local NER plus deterministic credential/identifier detection, source exclusions, sanitised-only storage and a final dispatch check. This preserves meaningful relevance, clarity and safety grading while factual accuracy stays unassessable without safe context. Approval must explicitly accept the gate's stated residual risk and amend AC23 accordingly. Until approval and implementation, use strict no-free-text mode as the fallback while keeping analytics counts/timings available. Do not close US-ADM-01-03 as complete while strict mode prevents semantic grading.

This is stronger protection than the previous email/long-token regex: names, short labelled credentials, identifiers and unsafe source categories are checked locally before analytics storage and again immediately before dispatch. It is not an exhaustive privacy guarantee. An arbitrary secret can be an ordinary word, a name can be unrecognised, and prose can encode a solution without a marker. No classifier can reliably certify their absence from arbitrary text. Neither a clean scanner result nor teacher publication proves it.

The strict alternative is categorical: no request/response/context free text is retained for analytics or transmitted for grading. Fixed structural summaries cannot support the approved relevance/factual-accuracy rubric, so do not manufacture grades from them. No new dependency/model is needed in strict mode.

## Acceptance criteria retained from US-ADM-01-03

- **Privacy and safeguards:** Evaluate only responses and the minimum context authorised for this purpose; exclude credentials, unnecessary personal data, and protected answer keys or solutions. Do not display private conversation content in the analytics report, and treat evaluated content as untrusted input.
- **Evidence and uncertainty:** Each grade includes a brief reason grounded in the response and available authorised context, without quoting private conversation content. If a dimension cannot be assessed from that material, it is marked unassessable rather than assigned a grade.

Shared server-side authorisation, SoC-only AI, bounded input/output, no uncontrolled retries, answer-release and safe rendering criteria remain in force. AC23's categorical names/credentials exclusion cannot be claimed for arbitrary prose under the optional gate; approving the gate requires explicitly changing that claim to the testable detected categories below. Existing broad story privacy requirements remain a product acceptance decision, not a spec-writer assumption.

## Proposed gate contract (only after explicit residual-risk approval)

1. Use local CPU named-entity recognition plus deterministic detection; never send text to an AI service to sanitise it. Only the shared SoC grading client may receive eligible sanitised text. No external privacy service, telemetry or runtime model download.
2. Exclude all account names, emails and identifiers from payload construction. Locally remove exact authenticated-account identity variants, including case/Unicode-normalised forms; do not load all users' identities as context. Also detect unrelated personal names using local NER.
3. Detect PERSON entities; emails, phone numbers, national-ID-like strings, app user IDs, private-key blocks, bearer/basic credentials, JWTs, connection strings containing credentials, common API-key prefixes, assignments labelled password/passwd/pwd/secret/token/api_key, and the existing 32-character token-like pattern. Replace detected spans with a fixed `[REDACTED]` marker. Short labelled secrets are removed regardless of entropy or length. Unknown unlabelled secrets remain a stated residual risk.
4. Scan the entire candidate before truncation. Input caps remain 2,000/6,000/3,000 characters for request/response/context; over-cap input is ineligible rather than scanned only partially. Reject malformed Unicode, unsupported language (English only), unsupported structured content and processing failures. No confident-English or no-entity result constitutes proof of safety.
5. Eligible source classes only: pre-submission hints-only companion response; teacher study-note output. Never include companion `explain`/solution responses, including after successful submission. MCQ batches are ineligible in this amendment, including stems/choices: solution text can be embedded there. Never include teacher upload/source prose or student pasted question/source context; it can contain key/solutions in ordinary prose. Teacher requests are regenerated from fixed application templates and enum settings, not upload titles, filenames, course names or teacher free text. Student request and eligible response still pass the gate. Context is always empty. Server forces factual accuracy unassessable with the existing no-context reason. In eligible request/response text, reject the whole item if normalised text contains a solution-bearing marker: `answer key`, `correct answer`, `correct option`, `solution:`, `worked solution`, `answer is`, or `explanation of the correct`. These bounded rules supplement categorical source exclusion; they cannot recognise arbitrary paraphrased solutions, which remains an explicit residual risk. Do not try to redact just the marker and retain its following answer.
6. NER is required for every nonempty eligible free-text field. Startup readiness checks load an immutable local model and run a fixed name-recognition health fixture. Missing model, wrong digest/version, unsupported language, scanner exception, timeout or health failure blocks all free-text grading; never fall back to regex. A clean scan is not labelled guaranteed safe.
7. Scan synchronously before the analytics write under a 500ms per-item deadline, without affecting host-route success. Failure saves metrics only and a privacy-blocked grading item with NULL text. Never log raw scanner exceptions, matching spans, request/response text or model outputs. Scan a sanitised copy again immediately before dispatch, under a 500ms deadline; newly detected spans are redacted and all fields rescan successfully before the single SoC call. No scanner network requests.
8. Sanitised storage only; retain the existing seven-day maximum and immediate deletion after grading. A version/digest marker is required. Legacy rows without the current policy marker are never eligible. Purge their three text columns and existing grade reasons before enabling the new worker; reset them to privacy-blocked without attempting to salvage raw text. Do not erase source learning/content records. Backup retention cannot be retroactively purged by an application migration: document remaining backup retention and ensure restored data is swept before workers run.
9. Grade reasons also pass the local gate before storage/display. Reject output containing any detected span (do not store partially redacted grades), any existing 30-character private-text overlap, invalid schema or markup. Retain existing fixed four-dimension schema. No unsafe output reaches analytics APIs.

## Function and data contract

New module `feature_analytics/privacy.py`:

```python
@dataclass(frozen=True)
class PrivacyResult:
    state: Literal['eligible', 'blocked']
    code: Literal['privacy_disabled', 'privacy_source_excluded',
                  'privacy_input_unsupported', 'privacy_scanner_unavailable'] | None
    content: GradingContent | None
    policy_version: str | None

def prepare_grading_content(*, source: Literal['student_hint', 'teacher_notes',
    'student_explanation', 'teacher_mcq', 'legacy'], content: GradingContent,
    identity_values: tuple[str, ...]) -> PrivacyResult: ...

def privacy_ready() -> bool: ...
def validate_grader_privacy(*, reasons: tuple[str, ...]) -> bool: ...
```

`GradingContent` remains the approved three-string value. Do not infer eligibility from prose; the authenticated host route supplies source category from its already-resolved operation. The privacy module owns the scanner and timeout; no test or hook loads a remote model. Scanner seam: `scan_person_spans(text: str) -> tuple[tuple[int,int], ...]` returns offsets or raises; tests substitute it and verify failing states, with a separate real-model fixture suite.

Add `privacy_policy_version text NULL` to grading items; permit item status `privacy_blocked`; permit failure codes above. Blocked items carry NULL text, contribute a new `privacy_blocked_count` integer to `/quality`'s grades object, and are excluded from waiting/failed/assessed counts and grading selection. Metrics still use original source outcomes. Add `privacy_mode: 'strict'|'local_dlp'` to that object. Existing runs, periods, pagination and endpoint paths remain unchanged.

Strict mode: all successful grading candidates become `privacy_blocked`/`privacy_disabled`; no free text is stored and the grading endpoint returns HTTP 409 `{"detail":{"code":"privacy_grading_disabled","message":"AI grading is disabled because free-text privacy protection has not been approved."}}`. Apply after authentication and existing input validation, before active-run/quota checks; create no run and consume no quota.

Local gate unavailable at grading start: HTTP 503 `privacy_scanner_unavailable`, message `AI grading is unavailable because the local privacy scanner is not ready. Try again later.` No run or quota charge. Scanner failure mid-run: stop with run `failed`/`privacy_scanner_unavailable`; purge current item's text and mark privacy_blocked; preserve earlier grades and untouched pending items. Recheck readiness per item. Policy version mismatch is blocked/purged, not rescanned from legacy text.

## Model/dependency provisioning decision

Optional gate implementation uses spaCy CPU English NER (`en_core_web_sm`) from a reviewed, pinned local wheel, with transitive Python dependencies locked in `uv.lock`; a developer preflight must establish a compatible exact spaCy/model pair for the existing Python version and record wheel hashes/licence, memory and 500ms fixture timings before reporting implementation ready. This proposal deliberately does not invent unverified package versions. CI installs the same pinned artifacts; deployment provisions the model at build time via GitHub Actions, never first request. Set a fixed model directory/digest and prohibit runtime fetching. Missing artifacts leave strict mode effective. Provisioning preflight below fixes the versions; timing and offline health must pass before implementation is ready.

## UI contract delta

All unchanged screen/navigation/loading/auth/network/history behaviour stays exactly as approved in spec.md/plan.md. No extra GETs or background polling are added.

| State | Exact copy / behaviour |
|---|---|
| Strict mode | `status`: `AI grading is disabled until free-text privacy protection is approved. Counts and timings remain available.` Disable button `Grade ungraded responses`; no confirmation or POST. |
| Blocked items | Plain text: `{count} responses excluded by privacy protection.` No content preview or override control. |
| Start 409 privacy_grading_disabled | `alert`: `AI grading is disabled because free-text privacy protection has not been approved.` Keep period/results; disable start after refreshing quality once. |
| Start 503 or mid-run scanner unavailable | `alert`: `AI grading is unavailable because the local privacy scanner is not ready. Try again later.` Preserve results/period; existing start button may be retried manually (one POST). |
| No eligible items in local mode | Existing zero-item completion; blocked count remains visible. |

Requests per load and per retry: unchanged three GETs; strict mode adds none. Wrong role, Link history: push or replace, Refresh, Back and Forward, Expired session or logout, Backend down: unchanged approved contract. Longest wait before an error: existing 15-second HTTP timeout, plus 500ms local scanner bounds inside existing job bound. No generic failure message: use exact messages above. Accessible roles/names remain unchanged except the added `status`/`alert`; existing theme tokens, mobile stacking and safe plain text rendering apply.

## Ordered tasks and tests before code

1. spec-writer/orchestrator: obtain decision on strict containment and whether the explicit bounded gate/residual-risk AC23 amendment is acceptable. Do not claim full feature closure.
2. developer, read-only preflight: verify exact dependency/model compatibility, hashes/licence, offline installation and scan timing; return concrete provisioning addendum. No application feature code yet.
3. test-designer: after approval, independently write `test_adm01_privacy_*` and UI tests against this fixed contract; no real SoC calls. Cases: unrelated names (single/multiword), account aliases, short passwords, mixed-case labels, JWT/key/connection strings, embedded/injected solutions, post-submit explanation, MCQ stem/choices with answers, teacher source prose, Unicode/unsupported language, oversize-before-truncation, missing/wrong/failed model, timeouts, output reasons containing a new name/secret, legacy/policy mismatch, sanitised-only database/log/API inspection, rescan tampering, scanner failure mid-run, concurrent starts and no quota charge for blocked starts. Assert exact fake-client payload and zero calls for every excluded source/failure. Real offline model fixtures test representative English names and document misses; fixtures are evidence, never a guarantee.
4. developer: implement only approved mode, migration/sweep ordering, gate/hooks/job/query/UI deltas; preserve counts and host-route isolation. Update developer/user guides accurately.
5. verifier: re-run suites, inspect all candidate constructors and dispatch paths, verify restore/sweep ordering and no regex fallback; security report explicitly states scope and residual risk. Orchestrator closes usage/handoff.

## Open questions / approval prerequisites

- Single recommended approval: approve the bounded English local-DLP gate and its explicit AC23 scope amendment, with strict no-free-text mode effective until the scanner is provisioned and verified. This retains semantic grading with a new local dependency and acknowledged detection misses; declining keeps semantic grading incomplete.
- Is the bounded English local-DLP mode with possible missed arbitrary names/unlabelled secrets acceptable, explicitly revising categorical AC23? If categorical exclusion is non-negotiable, reject this mode and keep strict mode; stronger regex or NER alone cannot resolve it.
- Exact spaCy/model pins, hashes and compatible local installation must be supplied by preflight before independent implementation/test work. No unverified version is an approved contract.
- Backup retention/restoration policy must be recorded; deleting live analytics text does not erase historical backups.


## Approved provisioning and runtime rulings (2026-11-10)

- Exact dependencies: `spacy==3.8.18`; `en_core_web_sm==3.8.0` installed from the official wheel `https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl` with SHA256 `1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85`. Official wheel is 12,806,118 bytes, MIT licensed, metadata requires spaCy >=3.8.0,<3.9.0. PyPI confirms the chosen spaCy release has a Python3.13 Windows wheel; CI Python3.12 remains supported. Provision during frozen dependency install; never download at runtime. Developer verifies installation, real-model fixture timings and records observed resource limits.
- Default approved mode is `local_dlp`. Strict mode is an explicit server setting; missing/unhealthy scanner in local mode returns the specified 503 and never falls back to regex. No extra runtime approval switch is required.
- Bound scanner work with one owned worker and no unbounded queue: a busy, timed-out or failed worker blocks the candidate; callers wait at most500ms. A timed-out worker is marked unhealthy and cannot start more tasks until restart; never spawn repeated workers on timeout. Model warmup may run separately before readiness; cold/unready state blocks candidates rather than holding host requests. Offline fixed-name health fixture is required.
- English-only support is conservative: reject non-ASCII letters/unsupported script and unsupported structured/binary content; ordinary Unicode punctuation is normalised. This is a bounded supported-input rule, not proof of English or privacy.
- Solution markers (case/whitespace normalised phrases `correct answer`, `correct choice`, `answer key`, `solution`, `explanation:`) in any eligible candidate block the whole candidate before storage. These supplement source exclusions; they cannot identify arbitrary unmarked solution prose. This remaining detection limitation was part of option1's accepted bounded scope.
- Record privacy mode, policy version and blocked count; the detailed statuses and function signatures above are the test contract. Freeze the final policy identifier as `adm01-local-dlp-v1`. Legacy rows/grade reasons are purged by an additive migration before new workers serve requests; migration must be applied before service start and after any backup restoration. Existing backup retention is operator-owned/unavailable here; do not claim historical backups were erased.
