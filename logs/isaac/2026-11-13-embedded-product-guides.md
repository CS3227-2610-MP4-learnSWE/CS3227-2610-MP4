# Embedded product website guides

User clarified that guides must be hosted on GitHub Pages itself, with separate professional navigation tabs. Added static guide rendering from maintained Markdown, local screenshots and supporting setup/data-contract pages. Added consistent navigation, a sticky contents sidebar, responsive typography, scrollable tables, code styling and light/dark support. Fixed two stale source guide links. HTML input in Markdown is disabled; no private files are copied.

RED-before-GREEN evidence: new embedded-guide test failed on missing local guide navigation before implementation. All 14 site tests passed after implementation, including local assets and fragment validation. Chromium screenshots inspected at desktop 1440px, mobile 390px and dark mobile 320px; no page overflow. Direct master push authorised in prior turn. CI and Pages publication must complete before claiming the new pages live.
