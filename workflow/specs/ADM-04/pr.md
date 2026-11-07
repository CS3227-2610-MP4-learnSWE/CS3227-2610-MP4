# ADM-04: reviewed private feedback follow-up

Admins can review and send private replies to individual feedback submitters or announcements to selected/all-active students or teachers. Immutable previews and transactional receipts prevent duplicate delivery after retries; recipients get private persistent unread messages with read state.

The follow-up redesign separates recipient selection from outlined message inputs, groups inbox requests/messages into readable cards, uses local dates and consistent light/dark surfaces, and adds an owner-only combined unread navigation badge. The badge checks metadata while visible every minute/on focus and updates locally after reads; no body polling. All-active search counts no longer imply a smaller selected audience. The spec and guides match the new UI.

Validation: redesign full **622 browser tests PASS** (370.746s), **121 focused backend tests PASS** (56.55s); zero failures/errors/skips or browser retries/flaky cases. Types/lint/build/scoped formatting/spec/whitespace pass; desktop/mobile dark/light screenshots inspected. An auth-only mock needed an additive metadata fallback; existing assertions retained. Prior core feature strongest verifier passed full1358backend/615browser; this UI maintenance was a single developer session. See logs/Adm04UiRedesign.md and workflow/usage/runs/2026-11-07-ADM04-UI-01/report.md.

Initial core feature requires migration20261107_adm04_messaging; the redesign adds no migration. Start API with the intended .env. Developer DB/environment and user processes unchanged; no live AI/external delivery. Request quotas remain process-local, durable delivery uniqueness database-enforced. Remote CI and teammate review pending.
