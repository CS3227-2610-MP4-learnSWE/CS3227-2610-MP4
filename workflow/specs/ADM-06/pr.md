# Add admin AI usage monitoring

Admins can inspect actual SoC service-call attempts, retries and failure categories by feature and bounded UTC dates at /admin/ai-usage. Durable metadata records only observed token counters, with explicit unavailable values for incomplete coverage, missing measurements and interrupted recording. Private prompts, replies and user identifiers are excluded.

The existing shared transport is instrumented without changing quotas or retry policy. Includes additive migration, explicit coordinated coverage activation, accessible report UI and updated operator/user guides. Apply migration, restart every worker, then activate STU-03/TEA-02 collection as documented; no historical backfill, first partialUTC day unavailable. ADM-03 remains disabled pending implementation.

Validation: strongest read-only verifierPASS;1169 backendPASS;513 browsercases covered across512PASS full run plus corrected timeout1PASS (one fixture failure in collected fullrun). Independent focused80backend/41browserPASS; typecheck/lint/build/format/spec/diffPASS. Mocked provider only; live measurement availability unverified. Reporting limiter retains documented process-local semantics.

Human review/merge into master required. No deployment included.
