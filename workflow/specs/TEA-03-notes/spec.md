# Spec: TEA-03-notes — Edit draft notes

Status: Approved by the user's explicit implementation request, 2026-11-02. This contract records the approved plan and concrete implementation defaults without expanding its scope.

## Goal

Teachers can correct an existing unpublished note draft and explicitly save it. Implements US-TEA-03-02 and completes the editable-notes portion of US-TEA-02-01. Original acceptance criteria: “Saved edits persist when I reopen the draft” and “Edits to an unpublished draft do not change the published version.” No published version exists yet; edits must remain private and must not introduce publication.

## Acceptance criteria

- [ ] AC1: A teacher managing the draft's course can open an editor populated with its title/content, save valid changes and reopen them after browser/backend restart. Source files, other drafts, original creator/time and source/course references remain unchanged.
- [ ] AC2: Existing and newly generated drafts expose immutable source_title and version/updated_at/updated_by. Existing rows backfill version1, source_title=original title, updated_at=created_at and updated_by=created_by. New generations initialise identically. Metadata appears in list/get/create/patch; lists retain creation-time/ID descending ordering.
- [ ] AC3: PATCH requires exactly title/content/version. Trim title; normalise content CRLF/CR to LF then trim Unicode whitespace. Title must contain1–200 and content1–2,000 Unicode code points. Version is a strict positive integer (not bool/string/float). Invalid/unknown/missing fields return422 without mutation.
- [ ] AC4: The server resolves the development gate, identity, teacher role and current membership before body validation. Missing/unknown identities401, disabled gate/nonteacher403, foreign/missing draft404; invalid UUID422 after identity checks. A teacher with revoked access cannot save. No private paths, SQL/provider details or credentials appear in errors.
- [ ] AC5: Locking/version comparison makes two simultaneous valid saves using one version yield exactly one200 and one409 draft_conflict. Successful save increments version and records server-resolved editor/time. Stale versions and failed database commits change nothing. An uncertain/lost response is never automatically retried; an explicit retry may409 if the first save committed.
- [ ] AC6: Edit notes opens labelled Note title/Note content controls. Save changes is enabled only for valid semantic changes; Cancel returns to saved display. Show Unicode content count, field errors, original creator and latest editor/time. Source attribution uses source_title rather than editable title. Plain-text output stays escaped.
- [ ] AC7: Unsaved local input is protected on Cancel, course/draft selection, route/search change and browser back/forward with Keep editing/Discard changes confirmation. In-flight saves disable controls/duplicate requests and block in-app departure until settled. Refresh/tab close installs the native unload warning subject to browser behaviour; inputs are not persisted on reload.
- [ ] AC8: Save failures preserve local inputs, version and saved records, offer explicit retry and show a recoverable error.409 preserves edits and offers Load latest saved version after discard confirmation, with no force-overwrite. A failed latest-version fetch preserves local edits. Delayed old reads/saves cannot replace a different selected draft/course/editor.
- [ ] AC9: Migration works on populated TEA-02 and fresh databases and supports downgrade/re-upgrade. Existing health/student/material/generation behaviour remains compatible. No editing LLM invocation, publication, MCQs, autosave, revision-history UI or production authentication is introduced. Shared llm_client.py remains unchanged.
- [ ] AC10: Guides/shared contract reflect the actual behaviour; handoff records PR11/040dc07 TEA-02 merge and user-reported successful real generation. Independent tests, verifier review and mobile/desktop light/dark checks follow Variant B, isolated schemas/files and no live provider calls.

## Security and AI safeguards

Server access checks are authoritative; the spoofable demo header remains development-only. Body fields cannot select course/source/editor. Updates are transactional, and user/membership/draft checks must be locked/rechecked so revocation linearises with saves. Optimistic version conflicts never silently overwrite another writer. Render source titles, note content and metadata as escaped text. Editing never calls a model; existing generation uses the unchanged shared client and safeguards.

## Open questions

None.2,000-character manual content limit and notes-only scope were explicitly selected by the user. Production authentication, publishing/immutable published snapshots, MCQs, autosave and revision history remain future increments.
