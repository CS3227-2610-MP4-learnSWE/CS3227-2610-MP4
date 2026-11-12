# Implement targeted feedback forms and resumable responses

Admins can draft surveys with six question types, associate a feature or published lesson, review selected students or teachers, and publish private inbox requests. They can close collection and review submitted answers with immutable question snapshots.

Students and teachers automatically save unfinished answers as private server drafts and resume them when they return. Explicit submission validates required answers and marks the form Completed. Unfinished drafts are excluded from admin review and submission counts.

Access, CSRF, input limits, quotas, version checks and save/submit/close ordering are enforced on the server. Publication and inbox delivery are atomic. No AI calls or separate announcements are introduced.

## Validation

Independent final verification is in progress; replace this section with final results before opening the pull request. Initial focused feature checks passed 68 backend and 46 browser cases; a subsequently added mobile dropdown label regression was RED before the correction and now passes. Existing developer regression evidence is recorded in [the implementation log](../../../logs/Adm02Implementation.md).

## Migration and limits

Apply additive migration `20261107_adm02_feedback` using the existing documented local/deployment process before running the updated backend. Deployment remains through GitHub Actions. This working session does not migrate the developer database.

Feedback is identified and retained without automatic expiry/deletion in this release. Published forms and completed responses cannot be edited or reopened. Quotas use the existing process-local limiter. Abrupt browser termination cannot recover edits that never reached the server.
