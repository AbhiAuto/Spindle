# Using Spider with other LLMs

Spider is just instructions plus a folder of markdown, so it works anywhere the model can see the instructions. How well it works depends on whether the tool can read and write your files.

## Tools that can read and write files

Claude Code, Cowork, Cursor, Copilot in VS Code (agent mode), Aider, and local agents with file access.

1. Put `SKILL.md` and your role file where the tool picks up instructions (for example `.github/copilot-instructions.md`, `.cursor/rules/`, or `AGENTS.md`), or reference them from there.
2. Set `SPIDER_WEB` to your web folder, or keep the web at `./spider/`.
3. Use it as described in the README. The tool can run `scripts/spider.py` itself.

## Chat tools without file access

ChatGPT, Copilot chat, Gemini and similar.

1. Paste `SKILL.md` and your role file into custom instructions (or a custom GPT / Gem / agent).
2. Add this line: "You can't write files. At the end of a task, give me the strands to add as a code block, grouped by thread."
3. Paste the strands into your thread files, or add them with `spider.py add`.
4. To retrieve, upload `index.md` and the relevant thread files to the chat, then ask your question.

It's more manual, but the web stays the same format, so you can move between tools without losing anything.

## Local models

Any model that follows instructions reasonably well handles capture. Retrieval is better if the agent can run `spider.py find` and `due` instead of reading every file.
