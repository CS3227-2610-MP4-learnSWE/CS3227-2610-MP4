# TEA-03 publishing — scope preparation

Status: Preparation approved by the user's explicit request, 2026-11-04. Publishing implementation is NOT approved or implemented by this preparation change; its API/data/UI contract must be completed before application publishing code.

## Goal

One saved, reviewed MCQ batch is one practice set containing exactly its three questions. Teachers do not select subsets, mix batches, add questions to a set or use a separate assembly screen. Generation remains private; publication is a separate explicit action. Notes publication remains part of US-TEA-03-04.

## Acceptance criteria

- [ ] AC1: Current feature list, stories, guides and shared contract describe the same three-question batch publication model and distinguish working generation/editing/deletion from future publication.
- [ ] AC2: Remove the teacher question-selection builder and its sidebar entry. Legacy `/teacher/practice` redirects with replacement to `/teacher/generate?tab=questions`; refresh works. Student navigation and routes stay unchanged.
- [ ] AC3: The questions studio states: `One batch of three questions will be published as one practice set. Publishing is not available yet.` No active publication control or new endpoint is introduced.
- [ ] AC4: Existing teacher drafts, APIs, database and student practice behaviour remain unchanged. Student whole-set submission and answer-release tests continue to pass.
- [ ] AC5: Historical records remain historical; superseded future assembly scope is explicitly replaced rather than treated as a current requirement.

## Behaviour

Preparation removes the unused teacher builder and redirects its URL to the protected questions studio. Publishing itself remains future work:


- Review and explicitly publish all three saved questions from one authorised course batch, with a practice-set title and a topic in that course. Preserve question order, four choices, exactly one correct choice and an explanation each. No question selection/mixing interface.
- Publish an immutable snapshot. Later draft edits cannot change published questions or the versions used by student attempts. Published references must block draft/batch deletion; source protection follows its existing references. No unpublish or published deletion.
- Published notes and sets require server-side student/course access; drafts remain teacher-only. Never return answer keys/explanations before successful whole-set submission.
- Map teacher indices to stable student choice IDs on the server; do not expose raw teacher detail responses to students. Preserve the existing student question/choice and attempt/results envelope, ownership and hint/explanation safeguards.

## UI states and copy

| Screen/action | Control | Loading | Success | Empty | Failure | Recovery |
|---|---|---|---|---|---|---|
| Legacy teacher URL | Replacement navigation | Existing session loading | Questions studio | Existing no-course/source state | Existing auth/source alerts | Existing Retry controls |
| Studio scope notice | Plain text; no Publish button | Not applicable | One batch of three questions will be published as one practice set. Publishing is not available yet. | Same notice | No new request | Existing studio controls unchanged |


Teacher navigation has no `Practice sets` assembly entry. The legacy URL redirects to the existing `Practice questions` tab of `AI content studio`, subject to existing auth loading/sign-in guidance and existing request timeouts/errors. The new notice is plain text (no button). Other studio controls, dirty-state blockers, generated batches, confirmation messages and mobile/themes remain unchanged. Back/Forward uses the redirected destination; student Practice links stay intact.

## Open questions

The future implementation must fix exact publication schema/endpoints, duplicate/republication policy, notes publication representation, student set discovery/course access and immutable attempt/version lookup in a separate approved implementation contract. Do not infer that a teacher-only publish endpoint alone makes content usable by students.


## Out of scope

No publishing endpoint, migration or student implementation change is introduced by preparation or merge resolution. Revise the publishing contract against STU-01 before application work.

## Security and AI safeguards

- Concurrent requests: preparation adds no writes; existing request ownership, edit/delete transactions and duplicate prevention remain unchanged.
- Normalisation: existing UUID/text normalization remains; the fixed legacy redirect accepts no user-provided parameters. No AI calls or answer exposure.

## Merge integration note (2026-11-05)

Reuse STU-01 published_lesson, completion/student study APIs and study_lessons.publish_lesson for future notes publication; do not add a competing note-publication store. Practice integration remains pending. Existing withdrawal/republishing storage does not add those teacher actions to the chosen scope. New migrations follow20261104_stu01_lessons.
