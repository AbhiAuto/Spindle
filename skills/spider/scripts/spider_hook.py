#!/usr/bin/env python3
"""Git pre-commit reminder: reusable test code changed but Spider memory didn't.

Never blocks a commit. Prints a short reminder so work done outside Copilot
(or when Copilot forgot to ask) still ends up in memory.

  python3 spider_hook.py --install     add it to this repo's pre-commit hook (once per clone)
  python3 spider_hook.py               what the hook runs (checks staged files)

Silence it for one commit with SPIDER_HOOK_QUIET=1 git commit ...
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REUSABLE_DIR = re.compile(r"(^|/)(pages?|page[-_]?objects?|screens|utils?|helpers?|support|fixtures?|api|apis|"
                          r"clients?|lib|steps?|step[-_]?definitions|stepdefs|commands|components)/", re.I)
CODE_EXT = (".ts", ".js", ".tsx", ".jsx", ".mjs", ".py", ".java", ".cs", ".kt", ".robot")
TEST_FILE = re.compile(r"(\.spec\.|\.test\.|\.cy\.|^test_|_test\.py$|Tests?\.(java|cs|kt)$)")
MARK = "spider_hook.py"
HOOK = """#!/bin/sh
# Spider: remind to update team memory (never blocks the commit)
if command -v python3 >/dev/null 2>&1; then P=python3; else P=python; fi
"$P" .github/skills/spider/scripts/spider_hook.py || true
"""


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def reminder(staged):
    if os.environ.get("SPIDER_HOOK_QUIET"):
        return None
    if any(f.startswith(("spider/", "spider-web/")) for f in staged):
        return None
    changed = [f for f in staged if f.endswith(CODE_EXT) and REUSABLE_DIR.search(f)
               and not TEST_FILE.search(Path(f).name) and not f.startswith((".github/", ".claude/"))]
    if not changed:
        return None
    shown = ", ".join(changed[:5]) + (f" (+{len(changed) - 5} more)" if len(changed) > 5 else "")
    return ("\nSpider: you changed reusable test code (" + shown + ") but not the team memory.\n"
            "  Run /remember in Copilot Chat to save what it does, then re-run /spider-harvest\n"
            "  to refresh the capability catalogue. Skip if there's nothing worth keeping.\n")


def install():
    hooks = git("rev-parse", "--git-path", "hooks")
    if not hooks:
        print("Not a git repo, no hook installed.")
        return 1
    path = Path(hooks) / "pre-commit"
    if path.is_file():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if MARK in text:
            print("Spider reminder already in the pre-commit hook.")
            return 0
        print(f"A pre-commit hook already exists at {path}. Add this line to it yourself:\n"
              f"  python3 .github/skills/spider/scripts/spider_hook.py || true")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HOOK, encoding="utf-8")
    try:
        path.chmod(0o755)
    except OSError:
        pass
    print(f"Spider reminder added to {path}")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--install" in argv:
        return install()
    staged = [l for l in git("diff", "--cached", "--name-only").splitlines() if l]
    msg = reminder(staged)
    if msg:
        sys.stderr.write(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
