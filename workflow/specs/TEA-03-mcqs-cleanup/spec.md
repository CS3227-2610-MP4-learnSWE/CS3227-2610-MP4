# Spec: TEA-03-mcqs-cleanup — Authenticated MCQ editing and unpublished deletion

Status: Approved through Dylan's explicit implementation request, 2026-11-04. Derived from the complete plan approved in chat; no additional permission gate before code.

## Goal and behaviour

A signed-in teacher managing a course can correct generated MCQs, permanently remove unwanted unpublished notes or entire MCQ batches, and remove unused uploaded originals. Migrate every teacher API off development identity onto PR16's shared cookie authentication. PR15 merged PostgreSQL original-file storage; PR16 merged shared authentication. Neither publication nor unpublishing exists in this increment.

## Acceptance criteria

- AC1: Every teacher endpoint requires the current authenticated teacher and current course membership. Spoofed demo headers have no effect, including when the legacy development gate is enabled. Unsafe methods require shared Origin/CSRF checks. An anonymous teacher data screen shows sign-in guidance without requesting teacher records.
- AC2: Existing upload/download/topic assignment, notes editing and notes/MCQ generation remain functional using session identity. No database transaction remains open during LLM work; session, role, membership and source are checked again before persistence.
- AC3: Any managing teacher can edit all three questions in an existing batch, including choices, correct answer and explanation. Strict limits/types and duplicate validation apply; no field outside the requested editable fields changes. Saved edits survive reopening/restart.
- AC4: Batch version/audit fields are backfilled without losing existing work. Atomic saves use locked optimistic concurrency: two saves from one version allow exactly one success. Stale saves/deletes return 409 without mutation.
- AC5: After explicit confirmation, a teacher may permanently delete an unpublished note or entire three-question batch. Never delete a single question. Failures preserve unrelated work; deletion and version checks are transactional.
- AC6: A source can be deleted only with no note or MCQ references. Its metadata and bytes disappear together; quota becomes reusable after commit. Concurrent generation, source deletion, uploads and topic reassignment cannot create orphans, partial changes or uncontrolled failures.
- AC7: MCQ editor supports labelled fields, counters, valid-change-only Save, Cancel, failure recovery, conflict recovery and duplicate prevention. All generated strings are escaped text. Existing note and new MCQ dirty editors protect navigation, Back/Forward and unload; pending save cannot depart in-app.
- AC8: Deletion confirmations name the item and permanence; batch confirmation includes all three questions. Success refreshes the list/clears deleted route selection. Errors retain work and explain recovery; obsolete responses cannot overwrite current selections. No mutation auto-retries.
- AC9: Additive migration, isolated tests, truthful docs, mobile/desktop both themes and existing suites pass. No student access or publication is introduced. No live LLM calls or developer data changes occur during verification.

## UI states and copy

The binding detailed control/message contract is in plan.md. Existing generation/notes controls retain their names and current content. New controls use these exact accessible names; dynamic braces are replaced with escaped item text.

| Action | Controls | Loading | Success | Empty | Failures | After failure |
|---|---|---|---|---|---|---|
| Anonymous teacher data screen | link “Sign in” to /login | “Loading your session…” while auth resolves | Authenticated screen | “Sign in to manage teacher materials and drafts.” | Auth bootstrap failure follows anonymous guidance | No teacher requests; sign in to retry |
| MCQ editing | button “Edit questions”; fields defined in plan; “Save changes”, “Cancel” | “Saving changes…” role=status | “Question changes saved.” role=status | No selected batch: existing empty viewer | Error table in plan | Editor values stay, explicit “Retry save”; conflict offers “Load latest saved version” |
| MCQ cancellation/navigation | dialog “Unsaved changes”; “Keep editing”, “Discard changes” | Pending-save dialog “Saving changes” | Requested action proceeds after discard | Clean editor cancels without dialog | Not applicable | Keep editing retains all fields |
| Note deletion | “Delete note draft”; dialog “Delete note draft?”; “Keep draft”, “Delete permanently” | “Deleting…” role=status | “Note draft deleted.” role=status | Existing list empty state | Error table in plan | Retain item and allow reopening confirmation |
| MCQ deletion | “Delete MCQ batch”; dialog “Delete MCQ batch?”; “Keep batch”, “Delete permanently” | “Deleting…” role=status | “MCQ batch deleted.” role=status | Existing list empty state | Error table in plan | Retain item and allow reopening confirmation |
| Source deletion | per-row button accessible name “Delete material {title}”; dialog “Delete material?”; “Keep material”, “Delete permanently” | “Deleting…” role=status | “Material deleted.” role=status | Existing material empty state | Error table in plan | Retain item; referenced source explains removing drafts first |

Refresh reloads saved state; unsaved edits are not persisted. Native unload warning applies while dirty/saving (browser controls display). Back/Forward, tab/course/draft changes use the same blocker; Keep editing never discards fields. Expired session displays sign-in guidance via the shared auth flow; do not silently resubmit after login. Backend/network failures use distinct messages. Ordinary request timeout 10 seconds, generation 45 seconds, no infinite loading. Logout/account changes clear active teacher selection/editor context; no previous account response may populate another account's screen. Avoid broad changes to shared logout; dirty route blockers cannot retain protected data after session expiry or successful logout; failed logout retains the current session/editor.

## Out of scope

Publishing, unpublishing, deleting published/student-referenced work, individual-question deletion, question reordering, practice sets, revision history, autosave, source replacement, account administration, new LLM prompts/providers and deployment. All existing draft rows are unpublished by definition; future publication/practice-set integration must add restrictive references/deletion guards before exposing them.

## Security and AI safeguards

Server controls permissions; UI role selection and identity headers are never authority. Reuse shared authentication and SoC client, preserve input/output/extraction limits. Mutation authorization precedes body/query validation; UUIDs canonicalised through existing parser and text through newline normalisation/Unicode strip. Row locks/version comparisons prevent lost updates; source/foreign-key locks prevent orphan generation. Safe envelopes never expose SQL, credentials, byte content or internal storage details. See plan for exact concurrency/error contract.

## Open questions

None. User chose any managing teacher and whole-batch MCQ deletion. Scope and implementation plan were explicitly approved.
