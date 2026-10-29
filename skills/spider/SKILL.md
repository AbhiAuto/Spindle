---
name: spider
description: Role-aware work memory. Use when the user asks to remember, save or log something from their work, asks what they did, decided, promised or sent before ("what did I pitch to X", "what's open on Y", "who did I meet at Z"), says "spider" or "/spider", or finishes a substantial task worth keeping. Stores memory as plain markdown files the user owns.
---

# Spider

Spider keeps a memory of the user's work in a folder called the **web**. The web is shaped by the user's role, so a sales lead's web holds accounts, contacts and deals, while an engineer's web holds services, decisions and incidents. Everything is plain markdown, so the user owns it, can read it, can put it in git, and can point any other LLM at it.

Three words, used throughout:

- **web**: the memory folder.
- **thread**: one file in the web about one thing (an account, a person, a project, a service).
- **strand**: one dated line inside a thread (a decision, a commitment, a contact, an insight).

## Where the web lives

Look for the web in this order and use the first one found:

1. A path the user has given in this conversation.
2. `SPIDER_WEB` environment variable.
3. `./spider/` in the current working folder, if it contains `profile.md`. This is where the VS Code installer puts a repo's memory.
4. `./spider-web/` in the current working folder (older installs).
5. `~/.spider/` for a personal memory outside any repo.

If none exists, run setup.

## Setup (first run only)

1. Ask the user one question: which role file fits them. List the files in `roles/` by their `title`. If none fits, offer `roles/_template.md` and build a custom one with them in two or three questions (what things they track, what they want to find later, what they must never store).
2. Create the web. If a shell is available, run `python scripts/spider.py init <web-path> --role <role-file>`. Otherwise create the same layout by hand (see `references/store-format.md`).
3. Write `profile.md` in the web with the user's name, role, capture mode (default `confirm`) and any extra never-store rules they gave.
4. Tell the user in one line where the web is and how to use it. Don't lecture.

## Every session

Read `profile.md` and the role file named in it. Read `index.md` only when you need to find or write something. Don't load threads you don't need.

## Capture

Capture when one of these happens:

- The user explicitly asks ("spider, remember this", "log that", "save this").
- A task ends that produced something the role file lists under **Capture**.
- A task ends and one of the role file's **Offer to remember when** moments happened. Offer even if the user didn't ask. This is the main way memory grows, so don't skip it after long sessions.
- The user states a fact the role file lists under **Capture** (a new contact, a decision, a deadline).

How to capture depends on `capture_mode` in `profile.md`:

- `confirm` (default): at the end of the task, show the proposed strands as a short list, each tagged with its thread. Write them on a yes. Edit or drop any the user corrects. One confirm per task, never per strand.
- `auto`: write without asking, then mention in one line what was added.
- `manual`: only write on an explicit ask.

Rules for every strand:

- One fact per strand, in the user's words where possible. Short.
- Format: `- YYYY-MM-DD [kind attrs] text`. Kinds come from the role file. See `references/store-format.md`.
- Commitments carry `open` or `done`, and `due:YYYY-MM-DD` when a date was given.
- Record what the user said or confirmed, not your conclusions or advice.
- Add `src:` with where it came from when that helps later (a meeting, a file name, an email subject).
- Put the strand in the thread it is about. If the thread doesn't exist, create it from the role's thread types. Before creating, check `index.md` and thread aliases for the same thing under another name.
- Link threads that relate with `[[thread-id]]` in the text and add the id to `links` in frontmatter.
- Give technique or how-to threads `use_when` triggers: the words someone would use when they need it, including synonyms (`--use-when "otp, mfa, two-step"`). Retrieval is by words, so triggers are what stop a pattern being missed.
- For a gotcha, store the error text it fixes (`--error "<error message>"`, or `error` in `spider_add`). Pasting that error into `spider_match` later finds the fix, even when numbers like timeouts differ.
- Record the real fix, not the shortcut. If the fix was a sleep, `force`, a raised timeout or retries, a removed or weakened assertion, or a swallowed error, Spider stores the line as `avoid`: it is shown as a warning and never offered as guidance. When that happens, ask what the proper fix was and record that as its own line.
- Secrets and personal details (keys, tokens, passwords, connection strings, e-mail addresses, URLs, hosts, IP addresses) are removed automatically when a line is written. Still don't paste them in.
- Pass `--by` with the person's name when you know who found something. In governed mode it counts as evidence.
- When a commitment is completed, flip its `open` to `done` in place (`spider.py done <web> <thread> "<text>"`).
- Never delete history to update a fact. Mark the old strand `superseded` and add the new one.
- After writing, refresh `index.md` (run `python scripts/spider.py index <web>` if a shell is available, otherwise update the thread's line by hand).

## Never store

Apply the role file's **Never store** list and these, always:

- Passwords, API keys, tokens, card or bank numbers, government IDs.
- Health, religion, sexuality, politics or other sensitive personal details about anyone.
- Content the user marks confidential or says not to keep.
- Client data the user's contracts don't allow them to hold. When in doubt, store a pointer ("pricing sheet sent, see SharePoint folder X") rather than the content.

If a capture would break one of these, skip that part silently and keep the rest.

## Retrieve

When the user asks about past work:

1. For "what applies to this scenario" questions, and for any pasted error message, run `spider_match` (or `spider.py match <web> "<text>"`) first. It returns known errors with their fixes, ranked memory with the reason each item matched, shortcuts to avoid, and reusable code from `catalogue.md`.
1. Otherwise check `index.md` for matching threads (by name, alias, tag or type).
2. Read those threads. Follow `links` one hop if the question needs it (a person linked to an account).
3. For cross-cutting questions ("what's open", "what's due this week", "everything tagged ai-testing"), use `python scripts/spider.py find` or `due` if a shell exists, otherwise scan the index and threads.
4. Answer directly, with dates. Say which thread an answer came from when there is more than one source. Flag anything older than the role's `stale_after_days` as possibly out of date.
5. If nothing is found, say so plainly and ask for the missing detail. Don't guess.

The role file's **Shortcuts** section lists the questions this role asks most, with how to answer each. Use them.

Never present an `avoid` line as something to do. If a pattern is shown as `(candidate)`, say it hasn't been approved yet.

## After using memory

When you apply a pattern or a gotcha's fix, record it: `spider_feedback` with `used`, or `helped` if it clearly saved time. If it pointed the wrong way, record `wrong` with the reason. This is how the team learns which patterns help (`spider.py efficacy`).

## Governed mode

When `profile.md` has `governance: governed`, new pattern threads start as `candidate`. A person approves them with `spider.py approve <web> <pattern> --by "<name>"` once there's enough evidence (`spider.py candidates` shows it). You can list candidates, efficacy and prune proposals, but you never approve or retire a pattern yourself. Print the command for the person to run instead.

## Maintenance

When the user asks for a tidy-up ("spider, clean up", "weekly review"):

- List open commitments past their due date and ask which are done.
- List threads not touched for longer than `stale_after_days` and ask whether to archive them (move to `threads/_archive/`).
- Merge duplicate threads the user confirms, keeping aliases.
- Run `python scripts/spider.py check <web>` and fix anything it reports.
- Run `spider.py scan <web>` for secrets, and `spider.py prune <web>` for patterns that are disputed or unused. Show the proposals; a person decides.

## Using Spider outside Claude

This file and a role file work as custom instructions for any LLM that can read and write files. For chat tools that can't write files, the user pastes the strands the model proposes into the web themselves, or uses the CLI (`spider.py add`). See `docs/other-llms.md`.

## Changelog

- 2026-10-29: Version 0.5: automatic secret removal, shortcuts stored as `avoid`, error signatures, ranked matching with reasons, feedback, governed mode, stamp, evals and CI.
- 2026-10-29: Version 0.4 (memory kits, capability catalogue, use_when triggers).
