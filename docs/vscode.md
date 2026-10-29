# Spindle in VS Code

Spindle runs inside VS Code with GitHub Copilot (agent mode) or the Claude extension. No vector database, no server to host. The memory is a `spindle/` folder of markdown next to your code, and the agent finds things through the index, names, tags and links, the same way a person would.

## What gets installed

```
your-automation-repo/
  .github/
    copilot-instructions.md        Spindle block added (your own text is kept)
    skills/spindle/                 memory skill, roles, CLI, MCP server
    skills/spindle-pack-builder/    builds new test packs from memory
    prompts/                       /spindle-harvest /new-pack /recall /remember /log-gotcha /spindle-review /spindle-export /spindle-import
    instructions/                  spindle-tests.instructions.md, auto-loaded for tests and helpers
    pull_request_template.md       adds a "memory updated" checkbox
  .git/hooks/pre-commit            reminder when reusable code changes without memory (never blocks)
  .vscode/mcp.json                 registers the 'spindle' MCP server
  spindle/                          the memory itself
```

Copilot finds skills in `.github/skills/` and prompt files in `.github/prompts/` automatically. The Claude extension reads the same skill folders.

## Install

You need Python 3.8+ on the machine. Nothing else.

```bash
git clone https://github.com/AbhiAuto/Spindle.git
python Spindle/install_vscode.py path/to/your-automation-repo --name "Your team"
```

Run the same command again later to update Spindle. It never touches `spindle/`.

On Windows the MCP server uses `python`. On macOS and Linux it uses `python3`. Change it with `--python` if your machine is different.

## First run

1. Open the repo in VS Code and trust the `spindle` MCP server when asked (or start it from the MCP servers view).
2. Open Copilot Chat in **Agent** mode.
3. Run `/spindle-harvest`. Spindle scans the repo (nothing is executed), shows what it found (stack, layout, page objects, helpers, fixtures, data, tags, retries, skipped tests, CI), reads a few key files to pick up your conventions, and writes it all after you confirm.

The memory is useful from that point on.

## Day to day

| You want to | Run |
|---|---|
| Build a new pack that follows the team's way of working | `/new-pack` |
| Ask what the team knows | `/recall How do we handle OTP login?` |
| Log a flaky test and its fix | `/log-gotcha` |
| Keep what you just worked out | `/remember` |

`/new-pack` is the main one. It reads the framework, the app, similar past packs, patterns and gotchas, then opens the actual page objects and helpers it plans to reuse. It shows a short plan and generates after you confirm. When it's finished, it proposes what to remember, so the next pack starts from a better place.

## How it avoids missing what you've built

- Harvest writes `spindle/catalogue.md`: every exported function, class, method and fixture in your page objects, helpers, fixtures, API clients and step definitions, with the first line of its doc comment. Good doc comments make the catalogue much better.
- Pattern threads have `use_when` triggers, so "two-step login" finds the OTP pattern even if nobody wrote "OTP".
- Before writing a test or a new helper, Copilot runs `spindle_match` with the scenario and lists what it's reusing in the plan.
- The instructions file makes this happen for any test or helper edit, not just `/new-pack`.

## How memory keeps growing

- Copilot offers to remember at the end of a task when it created or changed reusable code, fixed a failing or flaky test, worked around an environment problem, or finished a pack.
- The pre-commit reminder catches reusable code changed outside Copilot. Each engineer installs it once per clone: `python3 .github/skills/spindle/scripts/spindle_hook.py --install`.
- The PR template checkbox is the final check at review time.

## Sharing across the team

Commit `spindle/` with the automation repo and the whole team shares one memory through normal pull requests. Reviewing memory changes in a PR is a good habit: it keeps the facts honest.

If people work across several clients, keep one memory per client repo. Never copy one client's memory into another's.

## Safety and quality

- **Secrets never land in memory.** Every line written, imported or exported passes through redaction: keys and tokens (AWS, GitHub, Google, Slack, Stripe, npm, JWTs), passwords in `key=value` form, connection strings, private keys, credentials in URLs, e-mail addresses, URLs, hosts and IP addresses. `spindle.py scan spindle` checks existing files; `--fix` removes what it finds.
- **Shortcuts are warnings, not lessons.** A fix that adds a sleep, `force`, a raised timeout, extra retries, a removed or weakened assertion, `networkidle` or a swallowed error is stored as `avoid`. Mentions that reject a shortcut ("not a fixed timeout", "the sleep was removed") aren't flagged. Use `--not-shortcut` when a pause really is the agreed design.
- **Paste an error, get the fix.** `/log-gotcha` stores the error text (`--error`). `spindle_match` on a pasted error lists "Known errors" first, even when numbers like timeouts differ.
- **Every hit says why.** Results show a score and the reason: a `use when` word, a name, a tag, words in the memory, or a known error.

## Governed mode (optional)

Install with `--governed` (or set `governance: governed` in `spindle/profile.md`). New pattern threads start as **candidates**:

```bash
python3 .github/skills/spindle/scripts/spindle.py candidates spindle                 # evidence per pattern
python3 .github/skills/spindle/scripts/spindle.py approve spindle otp-login --by "Abhi"
python3 .github/skills/spindle/scripts/spindle.py retire spindle otp-login --by "Abhi" --why "SSO replaced OTP"
```

- A pattern is ready when it has 3 lines from 2 people (`min_evidence`, `min_authors`, `min_files` in `profile.md`). `--override "<reason>"` approves earlier.
- Only a person approves or retires. The MCP tools let agents list candidates, never approve them.
- Kits carry approved patterns only (`--include-candidates` to change that). Imported patterns arrive as candidates.

## Is memory helping?

- Agents record `spindle_feedback` after using a pattern: `used`, `helped`, or `wrong` with a reason.
- `spindle.py efficacy spindle`: each pattern is effective, watch, disputed, unused or insufficient-data.
- `spindle.py prune spindle`: proposals to reword or retire. Nothing changes until a person runs `retire`.
- `/spindle-review` in Copilot runs scan, candidates, efficacy and prune, and prints the commands for you to decide on.

## Stamp, evals and CI

- `spindle.py stamp spindle` prints a short hash of the memory. Put it in PR notes so you know which memory a pack was built from.
- `spindle/evals.json` holds retrieval test cases: a request, what it should find, and what it must not. `spindle.py eval spindle spindle/evals.json --write-baseline spindle/evals-baseline.json` records the baseline.
- `spindle.py ci spindle` runs check, scan and evals, and fails if anything breaks or gets worse than the baseline. Install with `--ci` to add `.github/workflows/spindle.yml`.

## Reuse memory in another project

Export the reusable part of one project's memory as a kit, then import it into another project.

```bash
# in the source repo: dry run first, then write the kit
python3 .github/skills/spindle/scripts/spindle.py export spindle kits/pw-kit.zip --name pw-kit --redact "ClientName, Codename" --dry-run
python3 .github/skills/spindle/scripts/spindle.py export spindle kits/pw-kit.zip --name pw-kit --redact "ClientName, Codename"

# in the target repo (after installing Spindle there)
python3 .github/skills/spindle/scripts/spindle.py import spindle path/to/pw-kit.zip --dry-run
python3 .github/skills/spindle/scripts/spindle.py import spindle path/to/pw-kit.zip
```

- By default a kit holds framework and pattern threads, and conventions, patterns, gotchas, decisions, assets and insights. App, pack and people threads stay behind, as do open commitments and superseded lines. Use `--types`, `--kinds` or `--threads` to change that.
- Export removes source references, URLs, emails and IP addresses, drops links to threads that stay behind, and replaces client names with `[client]`: the names and aliases of app, pack and people threads, the team name, and anything you pass with `--redact`. Framework threads get a neutral id (`<kit>-framework`).
- Import adds new threads and merges into existing ones (same id), skips lines it already has, and marks every imported line `src:kit-<name>`. Run `/spindle-harvest` afterwards.
- Scrubbing is automatic but not perfect: file paths and wording can still hint at a client. Review every file in the kit before sharing it.

In Copilot, `/spindle-export` and `/spindle-import` walk through the same steps with a dry run and a review.

## Try it on the sample

`examples/sample-playwright-repo` is a small made-up Playwright repo with a team memory already in it: a framework thread, an app with gotchas and data rules, an OTP pattern and a past regression pack.

```bash
cp -r Spindle/examples/sample-playwright-repo ~/spindle-demo
python Spindle/install_vscode.py ~/spindle-demo
code ~/spindle-demo
```

Then try `/new-pack` with "Claims portal, withdraw claim journey, regression". The plan should reuse `ClaimsPage` and `buildClaim`, create the claim through the API rather than the UI, and steer clear of the Sunday-night SIT refresh.

## Without MCP

If MCP servers are blocked on your machine, install with `--no-mcp`. The skills fall back to running `python .github/skills/spindle/scripts/spindle.py` in the terminal, or to reading the files directly.

## Limits

- Search is by words, names, tags and aliases, not meaning. Add aliases and tags to threads so related words still find them.
- It works well up to a few thousand threads. Past that, SQLite full-text search is the next step, and it still doesn't need a vector database.
- Generated tests still need an engineer's review. Spindle makes packs consistent and quicker to build. It doesn't decide what's worth testing.
