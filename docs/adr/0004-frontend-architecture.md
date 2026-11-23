# ADR-0004: Incremental Frontend Modernization with Vite and TypeScript checkJs (Decision D4)

- **Status:** Accepted
- **Date:** 2026-11-23
- **Related Plan Items:** UX-01, UX-02, UX-20, UX-28

## Context
The Turkish web UI grew to ~6,000 lines of vanilla JS (`master/static/js/`) without bundling, linting, or XSS sanitization (Audit Finding F15). A full React/Next.js rewrite would stall sprint deliverables and risk breaking working Scrum workflows.

## Decision
Introduce a lightweight `frontend/package.json` toolchain using **Vite + TypeScript `checkJs` + ESLint + Playwright** while keeping the existing FastAPI static delivery intact. Extract modular components (`sanitizer.js`, `i18n.js`, `store.js`, `ux_shell.js`) incrementally with zero external CDN dependencies.

## Consequences
- Zero-downtime incremental refactor without throwing away the 5-tab Turkish UI.
- DOM sanitization and accessibility checks run locally and in CI.
