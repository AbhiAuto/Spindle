---
description: 'Spindle: build memory from this automation repo'
agent: 'agent'
argument-hint: 'Optional: folder of the automation repo (defaults to the workspace)'
---
Use the spider skill to harvest this test automation repo into memory.

1. Run the harvest as a dry run on ${input:repo} (for example: .) (spider_harvest tool, or `python .github/skills/spider/scripts/harvest.py <repo> spider`). Show me what it found, including how many reusable functions, classes and fixtures went into the capability catalogue.
2. Open the config file, one page object, one helper and two representative specs. From the code, propose extra `convention` and `pattern` strands the scan can't see: locator strategy, assertion style, wait strategy, test naming, data setup and teardown, how auth is handled.
3. Ask me once to confirm, then write everything (harvest with write, plus your extra strands on the same framework thread with src:harvest-review).
4. Look at the helpers and fixtures that do something complex (auth, OTP, uploads, payments, data setup, waits). Propose a `pattern` thread for each, with `use_when` triggers: the words people would use when they need it, including synonyms.
5. If the repo tests one main application, offer to create its `app` thread and link it to the framework thread.
