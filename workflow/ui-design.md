# Shared UI design principles

Project design baseline, approved by the user after the ADM-04 redesign on 2026-11-07. Apply to new screens and scoped redesigns for all roles. This guide records reusable decisions; the feature spec still fixes exact copy, behavior and acceptance criteria. A task does not authorise a site-wide restyle automatically.

## Hierarchy and layout

- One clear page title and short purpose statement. Use section headings for distinct tasks; do not make labels, body text and headings look alike.
- Group related controls in padded panels. Separate the primary editor from selection/filter tools: for example, Message details and Recipients are separate panels, with search at the top of the recipient panel, outside the message form.
- Use a balanced desktop grid with a flexible main area and a bounded secondary panel (ADM-04 uses 360px). Stack on small screens, retaining a sensible reading and keyboard order. Keep actions beside the content they affect.
- Use an 8px spacing rhythm: about 24–28px panel padding and section gaps, 16–20px on mobile, 12–16px within related groups. These are defaults, not rigid dimensions that override content needs.
- Keep long IDs secondary to human names. Wrap long titles, identifiers and user text; never let them force horizontal page overflow. Constrain long recipient lists to their own scroll area rather than expanding the whole page indefinitely.

## Inputs and actions

- Editable fields must visibly look editable: outlined boundaries, a contrasting input surface, persistent visible labels, and a clear focus treatment. Placeholders supplement labels; they never replace them.
- Distinguish field labels from section headings. Supporting text explains requirements, format and limits before a failed submission. Preserve typed values after recoverable failures and focus the first invalid field.
- Use one visually dominant primary action for the current step. Secondary actions are quieter. Separate the action bar with spacing/dividers; disable duplicate submissions while pending.
- Show selection scope honestly. A filtered search total is a matching-result count, not the full selected audience. Keep selected IDs across search/pagination; show exact recipients and content at final review.
- Confirmation/review is visually read-only: separate the audience summary, content preview and final actions. Success has a clear heading and restrained success accent; do not make it look like an editable form.

## Surfaces, colour and typography

- Reuse existing theme tokens: `--bg`, `--paper`, `--ink`, `--muted`, `--line`, `--blue`, `--blue-soft`, `--green` and `--green-soft`. Avoid unrelated colours for each screen.
- Use neutral page/panel surfaces and restrained blue for primary actions, focus, selection and unread emphasis. Reserve green for successful outcomes and red for errors; always include text/icon meaning as well as colour.
- Preserve visual separation in both themes: darker input surfaces inside dark panels, visible outlines/dividers, readable secondary text, and selected/unread tonal backgrounds. Never remove outlines to achieve a minimalist appearance.
- Starting scale: page title 28–36px, section heading 18–20px, content 14–16px, labels/supporting metadata 12–14px. Smaller secondary identifiers must remain legible. Adjust to the existing shell and content rather than shrinking everything to fit.
- Prefer subtle 10–14px corner radii and light borders over heavy shadows. Reuse component styles; scope feature-specific styling so unrelated screens do not change accidentally.

## Inbox, lists and notifications

- Separate list metadata from its title and content. Message cards show category/read state, subject, plain-text body, human-readable local date/time and a distinct read action. Use semantic `time` with the original ISO datetime; raw database timestamps are not display copy.
- Request rows have generous clickable targets, visible hover/focus and clear lifecycle chips. Preserve accessible link names when adding metadata or badges.
- Show unread state with both words and a visual accent, not colour alone. Notification badges sit beside their navigation destination, disappear at zero, cap long visual counts (such as 99+), and expose the exact count to assistive technology. Support mobile navigation too.
- Define what the badge counts. ADM-04 counts owned unread survey requests plus messages. Use metadata-only endpoints for navigation; do not fetch private message bodies merely to obtain a count.
- Specify initial load, refresh/focus cadence, hidden-tab behavior, read updates, failure recovery and session cleanup. For the current Inbox: one shell load, visible 60-second refresh, focus/visibility refresh with five-second spacing, local updates after reads, and coalesced in-flight refreshes.
- Never invent zero when data are unavailable. Preserve a last-known count or represent an initially unknown count as unavailable/hidden. Prevent older responses from overwriting newer local updates; discard previous-account state immediately.

## Accessibility and implementation pitfalls

- Specify exact accessible roles/names, keyboard paths and visible focus. Meet WCAG AA contrast targets: 4.5:1 for normal text, 3:1 for large text and essential control boundaries. Do not rely only on screenshot appearance to assess contrast.
- Check 320–390px mobile and desktop, light and dark themes, long content, loading/empty/error/success states and reduced motion. Controls must remain reachable without horizontal page scrolling.
- MUI outlined inputs use a nested `fieldset` and `legend`. Broad rules such as `.panel fieldset { border: 0 }` can erase input outlines. Scope resets to actual question/audience groups or exclude `.MuiOutlinedInput-notchedOutline`; inspect the computed border and focus state.
- Reuse the shared API/auth/session layer and existing controls. Preserve server authorization, input limits, private-data boundaries and safe plain-text rendering while changing presentation.
- Mock newly added background requests in unrelated browser fixtures so test-only sessions cannot leak into a developer API. Keep original auth and failure assertions intact.

## What every screen spec/plan must record

1. The page/section hierarchy, panel grouping, field appearance and primary/secondary actions.
2. Exact labels, supporting/error/status copy, accessible roles/names and meaningful selection/count semantics.
3. Light/dark surfaces and theme tokens, responsive stacking/wrapping, long-content behavior and focus/keyboard expectations.
4. Any badge or background refresh: endpoint/schema, ownership, requests per load/retry/refresh, hidden-tab behavior, stale-response handling, failure state and logout/account-switch cleanup.
5. Regression coverage and visual evidence for representative desktop/mobile/light/dark and failure states. Existing security and functional tests remain in force.

## Reuse references

- Implemented examples: `src/frontend/src/pages/AdminMessaging.tsx`, `components/MessagesInbox.tsx`, `pages/FeedbackInbox.tsx`, `hooks/useInboxUnread.ts`, and scoped messaging styles in `styles.css`.
- Acceptance/visual examples: `workflow/specs/ADM-08/retained-criteria.md` and `src/frontend/tests/adm04-redesign.spec.ts`. Ignored screenshots are temporary evidence, not permanent design assets.
- External background: [Google Material text-field guidance](https://m2.material.io/design/components/text-fields.html), [Google Material Web text fields](https://github.com/material-components/material-web/blob/main/docs/components/text-field.md), and [MUI text fields](https://mui.com/material-ui/react-text-field/). Use this project's accepted pattern rather than copying every upstream default.
