# Admin story synchronization - 2026-11-06

User supplied expanded admin UserStories during ADM-05 implementation and requested resynchronization with the previously agreed decisions.

Preserved all supplied UserStories text outside ADM-05 exactly, verified by a script assertion. Restored ADM-05 fixed-role creation, status/session handling, permanent archival, course creation/assignments, account search and confirmation requirements as six stories. Added labelled criteria and explicit scope boundaries, including that TEA-05 learning-results reporting is separate implementation. Synced FeatureList summaries for ADM-01 through ADM-06 with expanded story definitions. Copied ADM-05 criteria verbatim into spec AC1-19 without renumbering; derived criteria and API/UI/test contracts unchanged. No other admin features were implemented.

Validation: ADM-05 speccheck passed (1 checked, 0 failed); git diff --check passed. No application code or tests changed; no runtime suite warranted for this documentation synchronization. Implementation agents continue independently.

Resource use: follow-up spec-writer, inherited model/effort; tokens/cost unavailable; no retries or correction rounds. Orchestrator owns invocation manifest/report.

## New-course integration clarification

The orchestrator found that teacher publication requires a same-course Topic, but new admin-created courses had none and existing teacher tooling exposes no topic creation. The agreed course-creation outcome therefore requires one default General topic, created atomically with the course. UserStories and spec AC16 now match verbatim; plan covers storage, unchanged API response, guide walkthrough and independent regression/rollback cases. This is course usability integration, not a new topic-management feature. Existing courses/topics remain unchanged; no content is published automatically. No source, tests or guides edited by spec-writer. ADM-05 speccheck and diff check passed.
