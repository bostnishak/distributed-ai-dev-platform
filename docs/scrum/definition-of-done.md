# Definition of Done

**Status: draft.** The Scrum Team agrees on it or changes it at the next Sprint Planning. Work that does not meet the Definition of Done is not part of the Increment and is not shown at the Sprint Review.

A backlog item is **Done** when all of the following hold:

1. **Acceptance criteria** of the item are met and the Product Owner accepted it.
2. **Code is on `main`** through a pull request that:
   - has passing CI (lint + unit tests for `master` and `agent`, Docker builds);
   - was reviewed and approved by at least one teammate other than the author.
3. **Tests.** New logic has unit tests that run without a real model; behaviour involving a model was also tried with the real local model and the result is noted in the pull request.
4. **Runs in the real setup.** `docker compose up -d --build` starts the system and the feature works in the browser on desktop and mobile widths.
5. **Privacy and security.** No secrets in the repository, no data sent to external AI services, model output treated as untrusted.
6. **Documentation.** README, SRS, architecture or the member guides are updated when the item changes them. Code comments are in English and user-facing text in Turkish.
7. **Trello** card moved to *Bitti* with a link to the pull request.
