<!-- spindle:start -->
## Spindle memory

This workspace keeps a team memory in `spindle/` (Spindle skill in `.github/skills/spindle`).

- Before answering questions about past work, the frameworks, applications under test, flaky tests or reusable code, use the `spindle_*` MCP tools if available (`spindle_match` for "what applies to this scenario"), otherwise read `spindle/index.md` and only the threads you need.
- When asked to create or extend a test pack, use the `spindle-pack-builder` skill. Before writing any new helper, run `spindle_match` and reuse what exists.
- Offer to remember, once at the end of a task, whenever any of these happened, even if I didn't ask:
  - a page object, helper, fixture, API client or step definition was created or changed
  - a failing or flaky test was fixed, or an environment problem was worked around
  - something took several attempts to get working
  - a pack or a big part of one was finished
  - a convention was agreed or changed
- Show what you'd remember as one short list and write it only after I confirm.
- When a test fails, paste the error into `spindle_match` before debugging: it may be a known error with a recorded fix. Never apply anything listed under "Avoid".
- After applying a pattern or fix from memory, record it with `spindle_feedback` (used, helped or wrong).
- Never approve or retire patterns yourself; that's a person's decision (`spindle.py approve` / `retire`).
- Never store credentials, tokens, real customer data or client code in memory. Store file paths instead.
<!-- spindle:end -->
