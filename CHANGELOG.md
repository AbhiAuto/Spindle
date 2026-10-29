# Changelog

All notable changes to Spindle are listed here. Versions follow [Semantic Versioning](https://semver.org/). Until 1.0, minor versions may change the memory format; the installer migrates older memories when they do.

## [0.6.0] - 2026-10-29

### Changed
- Spindle names throughout. The memory folder is now `spindle/`, the commands are `/spindle-harvest`, `/spindle-review`, `/spindle-export` and `/spindle-import`, the skills are `spindle` and `spindle-pack-builder`, the scripts are `spindle.py`, `spindle_mcp.py` and `spindle_hook.py`, the MCP server and its tools are `spindle` and `spindle_*`, and the environment variable is `SPINDLE_WEB`.

### Upgrading
- Run the installer again. It moves `spider/` (or `spider-web/`) to `spindle/` unchanged with `git mv`, updates `.gitattributes`, and replaces the old skills, prompts, instructions, CI workflow, MCP entries, instructions block, PR template wording and pre-commit hook path. Your own text is kept.
- Each teammate runs `spindle_hook.py --install` once in their clone. It updates an old hook line in place.
- `SPIDER_WEB`, `SPIDER_HOOK_QUIET` and a `spider/` memory folder are still recognised, so nothing breaks before you upgrade.

## [0.5.1] - 2026-10-29

### Fixed
- Removed an outdated self-install copy of the skills, prompts and instructions from `.github/` (the real sources live in `skills/` and `vscode/`).

## [0.5.0] - 2026-10-29

### Added
- Secret and personal-data removal on every write, import and export (keys, tokens, passwords, connection strings, private keys, e-mail addresses, URLs, hosts, IP addresses). `spider.py scan [--fix]` checks existing memory.
- Shortcut detection: sleeps, `force`, raised timeouts, extra retries, removed or weakened assertions, `networkidle` and swallowed errors are stored as `avoid` and shown only as warnings. `--not-shortcut` overrides it.
- Error signatures: `--error` on gotchas. Pasting the same error into `match` lists the recorded fix first under "Known errors", even when numbers differ.
- Ranked matching with a score and reasons for every hit, plus an "Avoid" section.
- Governed mode (`--governed`): patterns start as candidates and need evidence and a named approver. New commands: `candidates`, `approve`, `retire`.
- Feedback and efficacy: `feedback --used|--helped|--wrong`, `efficacy`, and `prune` proposals.
- `stamp` (memory version hash), `eval` (retrieval test cases with baselines) and `ci` (check + scan + evals).
- `/spider-review` slash command and an optional GitHub Actions workflow (`--ci`).
- MCP tools: `spider_feedback`, `spider_candidates`, `spider_efficacy`, `spider_scan`, `spider_stamp`. Approving and retiring are deliberately not exposed to agents.

### Changed
- Kit import treats kits as untrusted: size limits, field whitelist, redaction and shortcut checks on every line. Exports drop people's names, and governed exports carry approved patterns only.

## [0.4.1] - 2026-10-29

### Added
- Installer support for repos shared by Claude Code and Copilot: skills in `.claude/skills/`, `.mcp.json` registration, an `AGENTS.md` section, and `npm run ai:sync` when present.
- Test instructions now target folders that exist in the repo.

### Fixed
- Harvest no longer catalogues test files as assets, eval sample code, or its own scripts.
- Prompts use plain `${input:name}` placeholders for tools that sync them to Claude Code.
- Skills end with a `## Changelog` section for repos that validate Copilot assets in CI.

## [0.4.0] - 2026-10-29

### Added
- Memory kits: `spider.py export` and `import`, with `/spider-export` and `/spider-import`. Export scrubs client names, URLs, emails, IP addresses and source references, and gives framework threads neutral ids. Import merges and de-duplicates.

## [0.3.1] - 2026-10-29

### Changed
- The memory folder is now `spider/` (was `spider-web/`). The installer moves existing memories with `git mv`.

## [0.3.0] - 2026-10-28

### Added
- Capability catalogue built by harvest from exported functions and doc comments.
- `use_when` triggers on threads, `spider.py match` and the `spider_match` MCP tool.
- Named moments when Copilot offers to remember, a non-blocking pre-commit reminder, and a PR template checkbox.
- Test-file instructions that load automatically when Copilot edits tests and helpers.

## [0.2.0] - 2026-10-28

### Added
- VS Code and GitHub Copilot support: installer, slash commands, Copilot instructions, and a zero-dependency MCP server.
- Test automation engineer role, repo harvest and the pack builder skill.
- Sample Playwright repo with a filled-in memory.

## [0.1.0] - 2026-10-28

### Added
- Role-shaped markdown memory (threads and strands), a CLI, role templates and tests.

[0.6.0]: https://github.com/AbhiAuto/Spindle/releases/tag/v0.6.0
[0.5.1]: https://github.com/AbhiAuto/Spindle/releases/tag/v0.5.1
[0.5.0]: https://github.com/AbhiAuto/Spindle/releases/tag/v0.5.0
