---
name: spider-pack-builder
description: Builds a new test automation pack (regression, smoke, API, E2E suite or set of test scripts) from what the team did before, using the Spider memory in spider/. Use when asked to create, scaffold or extend a test pack, test suite or automation scripts for an application or module, or on /new-pack.
---

# Spider pack builder

Builds a new automation pack that looks like the team wrote it: same framework, same conventions, reusing the page objects and helpers that already exist, and avoiding the problems the team already hit. It reads the Spider memory first and writes back what it learned at the end.

Needs the `spider` skill and a web created with the `test-automation-engineer` role (normally `spider/` at the workspace root).

## Rules

- Never apply a line marked `avoid`. It records a shortcut that hid a problem; use it only to know what not to do.
- In governed mode, patterns marked `(candidate)` aren't approved yet. You can use them, but say so in the plan.
- Lines marked `src:kit-<name>` came from another project. Use their conventions, patterns and gotchas, but check that any file path they mention exists in this repo before relying on it.
- The repo is the source of truth. Memory tells you where to look and what to watch for. If memory and code disagree, trust the code and propose a strand that supersedes the old one.
- Reuse before you write. Extend an existing page object, fixture or helper rather than creating a parallel one.
- Never put credentials, tokens, real customer data or environment secrets in tests or memory. Use the mechanism the repo already uses (env vars, vault, fixtures).
- One confirm before generating, one confirm before writing to memory. Don't ask more than that unless something is truly missing.

## Steps

### 1. Load memory

Use the `spider` MCP tools if they're available (`spider_match`, `spider_find`, `spider_read`), otherwise run `python .github/skills/spider/scripts/spider.py` in the terminal, otherwise read the files directly.

1. Read `spider/index.md`.
2. If there is no `framework` thread for this repo, stop and suggest running `/spider-harvest` first. It takes a minute and makes everything after it better.
3. Read the `framework` thread for this repo: stack, layout, naming, tags, retries, assets.
4. Read the `app` thread for the application under test, if there is one: modules, environments, data approach, gotchas.
5. Run `spider_match` (or `spider.py match`) with the request in plain words, then once per scenario in scope. It returns the patterns and gotchas whose triggers match, and the existing functions, page objects and fixtures from the capability catalogue. Treat every hit as a reuse candidate.
6. Find past packs for the same app or a similar module: `spider_find` with `type=pack` and the app or module name. Read the closest one or two.
7. Find any other `pattern` threads and `gotcha` strands for the scenarios in scope (for example login with OTP, file upload, payments, iframes).

### 2. Read the code memory points to

Open the files named in `asset` strands that are relevant to the scope: the page objects, fixtures, helpers and API clients this pack will touch, plus one existing spec close to what you're about to write. Match its style exactly (imports, locator strategy, assertion style, waits, tags, test naming, folder).

### 3. Propose the plan

Show a short plan and wait for one yes:

- Scope: modules and scenarios, with priority (smoke / regression / edge).
- Reused: each existing function, page object, fixture or pattern you'll use, as `path :: name (why)`. List every reuse candidate `spider_match` found and say which ones you're not using and why, so the engineer can see nothing was missed.
- New: what you'll add, and where it goes in the folder layout.
- Watch-outs: gotchas and patterns from memory that apply, and how you'll handle each.
- Data and environment: where test data comes from, which env, setup and teardown.

### 4. Generate

- Follow the conventions from memory and the sample spec.
- Before writing any new helper, page object method or fixture, run `spider_match` with what it will do. If something similar exists, use or extend it instead. Only write a new one when nothing fits, and say why in the plan.
- Put new page objects and helpers where the existing ones live, with the same naming.
- Tag tests the way the repo does (for example `@smoke`, `@regression`).
- Apply known fixes from `gotcha` and `pattern` memory instead of rediscovering them.
- Keep tests independent: own data, own setup, no order dependence.

### 5. Check it

Run the lightest check available and fix what fails: list or compile the tests (`npx playwright test --list`, `npx tsc --noEmit`, `mvn -q test-compile`, `pytest --collect-only`, `dotnet build`). Run the new tests if an environment is configured and the user agrees. Report results plainly.

### 6. Record what memory helped

For each pattern or gotcha you applied, call `spider_feedback` with `used` (or `helped`). If one pointed the wrong way, record `wrong` with the reason.

Put the memory stamp (`spider_stamp`, or `spider.py stamp spider`) in the PR description, so reviewers and evals know which memory the pack was built from.

### 7. Write back to memory

Propose strands as one short list and write them on a yes:

- A new `pack` thread: scope, test count, priority split, what was left out and why (`coverage`), reused assets (`asset`), linked to the app and framework threads with `[[id]]`.
- New reusable assets created (`asset` on the framework thread, with paths).
- New techniques worth reusing (`pattern`, or a new `pattern` thread if it's a technique others will need).
- Problems hit and their fixes (`gotcha` on the app or framework thread), with the error text in `error` so the next person can paste it and find the fix.
- Any convention you inferred from the code that wasn't in memory yet (`convention`).

If you added or changed reusable code, re-run harvest with write so the capability catalogue picks it up, and add doc comments to new functions so the catalogue can describe them. Then refresh the index.

## Changelog

- 2026-10-29: Version 0.4 (memory kits, capability catalogue, use_when triggers).
