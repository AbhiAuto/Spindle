<!-- spider:start -->
## Spider memory

This workspace keeps a team memory in `spider/` (Spider skill in `.github/skills/spider`).

- Before answering questions about past work, the frameworks, applications under test, flaky tests or reusable code, use the `spider_*` MCP tools if available (`spider_match` for "what applies to this scenario"), otherwise read `spider/index.md` and only the threads you need.
- When asked to create or extend a test pack, use the `spider-pack-builder` skill. Before writing any new helper, run `spider_match` and reuse what exists.
- Offer to remember, once at the end of a task, whenever any of these happened, even if I didn't ask:
  - a page object, helper, fixture, API client or step definition was created or changed
  - a failing or flaky test was fixed, or an environment problem was worked around
  - something took several attempts to get working
  - a pack or a big part of one was finished
  - a convention was agreed or changed
- Show what you'd remember as one short list and write it only after I confirm.
- Never store credentials, tokens, real customer data or client code in memory. Store file paths instead.
<!-- spider:end -->
