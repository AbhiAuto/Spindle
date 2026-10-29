---
description: 'Spindle: reuse team memory whenever tests or test helpers are written or changed'
applyTo: '**/*.spec.ts,**/*.spec.js,**/*.test.ts,**/*.test.js,**/*.cy.ts,**/*.cy.js,**/test_*.py,**/*_test.py,**/*Test.java,**/*Tests.cs,**/*.feature,**/*.robot,**/tests/**,**/e2e/**,**/pages/**,**/fixtures/**,**/helpers/**,**/utils/**,**/support/**,**/steps/**'
---
This repo has a Spindle team memory in `spindle/`. Use it every time you write or change a test, page object, fixture or helper, whether or not a slash command was used.

Before writing code:

1. Describe the scenario in plain words and run `spindle_match` (or `python3 .github/skills/spindle/scripts/spindle.py match spindle "<scenario>"`; `python` on Windows). Read what it returns: patterns, gotchas, and existing functions, page objects and fixtures from the capability catalogue.
2. Use what exists. Extend an existing page object, fixture or helper rather than writing a new one. Only write a new helper when nothing in the catalogue fits, and say so.
3. Follow the conventions on the framework thread (locators, waits, assertions, tags, naming, folder layout), and apply known gotcha fixes instead of rediscovering them.
4. Tell the engineer which existing code you reused, in one short line.
5. Never apply a line listed under "Avoid": it records a shortcut that hid a problem.

When a test fails, paste the error into `spindle_match` first; it may be a known error with a recorded fix. After applying a pattern or fix from memory, record it with `spindle_feedback` (used, helped or wrong).

After the task, offer once to remember anything new: helpers or page objects you created or changed, fixes for failing or flaky tests, workarounds, and techniques that took several attempts. Add doc comments to new functions so harvest can catalogue them.

Never put credentials, tokens or real customer data in tests or memory.
