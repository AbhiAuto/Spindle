---
title: Test automation engineer
thread_types: [framework, app, pack, pattern, person]
strand_kinds: [convention, decision, pattern, gotcha, asset, coverage, data, env, defect, commitment, insight, status]
stale_after_days: 180
---

For engineers who build and maintain automation packs and want each new pack to build on what the team already did.

Thread types:

- `framework`: one per automation repo or framework (stack, layout, conventions, reusable assets).
- `app`: one per application under test (modules, environments, auth quirks, hard-to-automate areas, flaky areas).
- `pack`: one per test pack delivered (scope, coverage, what was reused, what found defects).
- `pattern`: one per reusable technique (OTP login, file upload, iframe handling, API data setup).
- `person`: app SMEs, developers and testers worth asking.

## Capture

- Conventions: folder layout, naming, locator strategy, assertion style, wait strategy, tagging (`convention`)
- Reusable assets with their repo path: page objects, API clients, helpers, fixtures, data builders (`asset`)
- Techniques that worked for a tricky scenario, with the file that shows it (`pattern`)
- Flaky tests and broken behaviour: symptom, root cause, fix (`gotcha`)
- Test data approach per app: source, setup, teardown, masking (`data`)
- Environments: URLs by name only, access rules, refresh cycles, known downtime (`env`)
- Pack scope and coverage: modules, test count, priority split, what was left out and why (`coverage`)
- Defects the automation found that matter (`defect`)
- Design decisions and the alternative rejected (`decision`)

## Never store

- Passwords, tokens, API keys, connection strings, test account credentials (store where they're kept, for example "vault path X")
- Real customer or production data, including in test data examples
- Client source code beyond file paths and short identifiers
- Environment URLs that are not already in the repo

## Shortcuts

- "What do we have for <app>?" : the app thread, its gotchas, data and env strands, and the packs linked to it.
- "How do we usually do <technique>?" : the pattern thread, plus `pattern` strands mentioning it across frameworks.
- "Have we seen this flake before?" : `gotcha` strands matching the error text or test name.
- "What can I reuse for <module>?" : `asset` strands on the framework thread plus assets from packs that covered the same module.
- "Start a new pack for <app>" : use the spider-pack-builder skill.
