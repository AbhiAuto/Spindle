#!/usr/bin/env python3
"""Install Spindle into a VS Code workspace (Copilot or Claude).

  python install_vscode.py <your-repo> [--role test-automation-engineer] [--name "Your Name"]

Safe to run again to update: skill files and prompts are refreshed, your
memory in spindle/ is never touched, and existing config is merged.
Upgrading from before the Spindle rename: the memory in spider/ (or spider-web/)
is moved to spindle/ unchanged, and the old skills, commands and config are replaced.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = ["spindle", "spindle-pack-builder"]
START, END = "<!-- spindle:start -->", "<!-- spindle:end -->"


def copy_skill(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def merge_instructions(path, block):
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), block.strip(), text, flags=re.S)
        action = "updated"
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + block.strip() + "\n"
        action = "added to" if path.is_file() else "created"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return action


TEST_DIRS = ["tests", "test", "e2e", "specs", "src/pages", "pages", "page-objects", "src/locators", "src/fixtures",
             "fixtures", "src/helpers", "helpers", "src/utils", "utils", "support", "cypress", "steps", "src/steps",
             "src/api", "api", "src/test"]
DEFAULT_APPLY_TO = None  # taken from the shipped instructions file


def layout(target):
    """Where this repo keeps skills. Repos shared by Claude Code and Copilot keep them in .claude/skills."""
    if (target / ".claude" / "skills").is_dir():
        return ".claude/skills"
    return ".github/skills"


def localise(text, skills_rel):
    return text.replace(".github/skills/spindle", f"{skills_rel}/spindle")


def write_localised(src, dst, skills_rel):
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(localise(src.read_text(encoding="utf-8"), skills_rel), encoding="utf-8")


def apply_to_for(target, shipped):
    """Point the test instructions at folders that exist; some repos reject globs that match nothing."""
    found = [d for d in TEST_DIRS if (target / d).is_dir()]
    return ",".join(f"{d}/**" for d in found) if found else shipped


def merge_claude_mcp(path, python_cmd, skills_rel):
    """Claude Code reads project MCP servers from .mcp.json (mcpServers), run from the project root."""
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return False
    data.setdefault("mcpServers", {})["spindle"] = {
        "command": python_cmd, "args": [f"{skills_rel}/spindle/scripts/spindle_mcp.py"], "env": {"SPINDLE_WEB": "spindle"}}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def merge_mcp(path, python_cmd, skills_rel=".github/skills"):
    entry = {
        "type": "stdio",
        "command": python_cmd,
        "args": [f"${{workspaceFolder}}/{skills_rel}/spindle/scripts/spindle_mcp.py"],
        "env": {"SPINDLE_WEB": "${workspaceFolder}/spindle"},
    }
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return False, json.dumps({"servers": {"spindle": entry}}, indent=2)
    data.setdefault("servers", {})["spindle"] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True, None


LEGACY_MEMORY = ["spider", "spider-web"]  # memory folders from installs before the rename
OLD_SKILLS = ["spider", "spider-pack-builder"]
OLD_PROMPTS = ["spider-harvest", "spider-review", "spider-export", "spider-import"]
OLD_START, OLD_END = "<!-- spider:start -->", "<!-- spider:end -->"


def prepare_memory_folder(target):
    """The memory lives in spindle/. Move one from an older install there unchanged; never clash with other folders."""
    web = target / "spindle"
    old = [n for n in LEGACY_MEMORY if (target / n / "profile.md").is_file()]
    if old:
        if web.exists() or len(old) > 1:
            found = ", ".join(f"{n}/" for n in (["spindle"] if web.exists() else []) + old)
            raise SystemExit(f"Found more than one memory folder ({found}). Keep the one with your memory, "
                             "remove or rename the others, then run the installer again. Nothing was changed.")
        name = old[0]
        moved = False
        if (target / ".git").exists():
            r = subprocess.run(["git", "mv", name, "spindle"], cwd=target, capture_output=True, text=True)
            moved = r.returncode == 0
        if not moved:
            (target / name).rename(web)
        print(f"Moved your memory from {name}/ to spindle/ (contents unchanged)"
              + (", staged with git mv" if moved else ""))
        ga = target / ".gitattributes"
        if ga.is_file():
            text = ga.read_text(encoding="utf-8")
            new = re.sub(r"(?m)^(spider-web|spider)/", "spindle/", text)
            if new != text:
                ga.write_text(new, encoding="utf-8")
                print("Updated the memory path in .gitattributes")
    elif web.exists() and not (web / "profile.md").is_file() and any(web.iterdir()):
        raise SystemExit("This repo already has a folder called spindle/ that isn't a Spindle memory. "
                         "Rename it, then run the installer again. Nothing was changed.")
    return web


def remove_old_install(target, gh):
    """Replace what an install from before the Spindle rename left behind. Your own text and memory are kept.
    Returns True if the old install had the CI workflow, so the new one takes its place."""
    done = []
    for base in (gh / "skills", target / ".claude" / "skills"):
        for s in OLD_SKILLS:
            if (base / s / "SKILL.md").is_file():
                shutil.rmtree(base / s)
                done.append(f"{base.relative_to(target).as_posix()}/{s}")
    old_files = [gh / "prompts" / f"{n}.prompt.md" for n in OLD_PROMPTS]
    old_files.append(gh / "instructions" / "spider-tests.instructions.md")
    had_ci = (gh / "workflows" / "spider.yml").is_file()
    old_files.append(gh / "workflows" / "spider.yml")
    for f in old_files:
        if f.is_file():
            f.unlink()
            done.append(f.relative_to(target).as_posix())
    for f in (gh / "copilot-instructions.md", target / "AGENTS.md"):
        if f.is_file():
            text = f.read_text(encoding="utf-8")
            if OLD_START in text and OLD_END in text:
                text = re.sub(re.escape(OLD_START) + r".*?" + re.escape(OLD_END) + r"\n?", "", text, flags=re.S)
                f.write_text(text.rstrip() + "\n" if text.strip() else "", encoding="utf-8")
                done.append(f"old block in {f.relative_to(target).as_posix()}")
    for f, key in ((target / ".vscode" / "mcp.json", "servers"), (target / ".mcp.json", "mcpServers")):
        if f.is_file():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if "spider" in data.get(key, {}):
                del data[key]["spider"]
                f.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                done.append(f"'spider' server in {f.relative_to(target).as_posix()}")
    pr = gh / "pull_request_template.md"
    if pr.is_file():
        text = pr.read_text(encoding="utf-8")
        new = text.replace("Spider memory", "Spindle memory").replace("spider.py stamp spider", "spindle.py stamp spindle")
        if new != text:
            pr.write_text(new, encoding="utf-8")
            done.append("PR template wording")
    hook = target / ".git" / "hooks" / "pre-commit"
    if hook.is_file():
        text = hook.read_text(encoding="utf-8")
        new = text.replace("/spider/scripts/spider_hook.py", "/spindle/scripts/spindle_hook.py")
        if new != text:
            hook.write_text(new, encoding="utf-8")
            done.append("pre-commit hook path")
    if done:
        print("Replaced the install from before the Spindle rename: " + ", ".join(done))
    return had_ci


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", help="the workspace / repo folder to install into")
    p.add_argument("--role", default="test-automation-engineer")
    p.add_argument("--name", default=None)
    p.add_argument("--python", default="python" if os.name == "nt" else "python3",
                   help="python command VS Code should use for the MCP server")
    p.add_argument("--no-mcp", action="store_true", help="skip .vscode/mcp.json")
    p.add_argument("--no-hook", action="store_true", help="skip the git pre-commit reminder")
    p.add_argument("--governed", action="store_true",
                   help="new memory only: patterns need evidence and a named approver before they count as approved")
    p.add_argument("--ci", action="store_true", help="add .github/workflows/spindle.yml (check, scan, evals)")
    p.add_argument("--skills-dir", choices=[".github/skills", ".claude/skills"],
                   help="where to put the skills (default: .claude/skills if the repo has it, else .github/skills)")
    a = p.parse_args(argv)

    target = Path(a.target).resolve()
    if not target.is_dir():
        raise SystemExit(f"Not a folder: {target}")
    web = prepare_memory_folder(target)
    gh = target / ".github"
    had_ci = remove_old_install(target, gh)
    skills_rel = a.skills_dir or layout(target)
    skills_dir = target / skills_rel

    for s in SKILLS:
        copy_skill(HERE / "skills" / s, skills_dir / s)
        for f in (skills_dir / s).rglob("*"):
            if f.suffix in (".md", ".py"):
                f.write_text(localise(f.read_text(encoding="utf-8"), skills_rel), encoding="utf-8")
        old = gh / "skills" / s
        if skills_rel != ".github/skills" and (old / "SKILL.md").is_file():
            shutil.rmtree(old)
            print(f"Removed the older copy in .github/skills/{s}")
    print(f"Skills installed in {skills_rel}/: {', '.join(SKILLS)}"
          + (" (this repo keeps skills there, and both Claude Code and Copilot read it)" if skills_rel != ".github/skills" else ""))

    prompts = sorted((HERE / "vscode" / "prompts").glob("*.prompt.md"))
    for f in prompts:
        write_localised(f, gh / "prompts" / f.name, skills_rel)
    print(f"Prompt files: {', '.join('/' + f.name.replace('.prompt.md', '') for f in prompts)}")

    for f in sorted((HERE / "vscode" / "instructions").glob("*.instructions.md")):
        text = localise(f.read_text(encoding="utf-8"), skills_rel)
        shipped = re.search(r"^applyTo: '([^']*)'", text, flags=re.M).group(1)
        text = text.replace(f"applyTo: '{shipped}'", f"applyTo: '{apply_to_for(target, shipped)}'")
        (gh / "instructions").mkdir(parents=True, exist_ok=True)
        (gh / "instructions" / f.name).write_text(text, encoding="utf-8")
    print("Test-file instructions: .github/instructions/spindle-tests.instructions.md "
          "(loaded automatically when Copilot works on tests and helpers)")

    pr = gh / "pull_request_template.md"
    line = "- [ ] Spindle memory updated (`/remember` or `/log-gotcha`), or nothing worth remembering"
    if not pr.is_file():
        shutil.copyfile(HERE / "vscode" / "pull_request_template.md", pr)
        print("PR template created with a memory checkbox")
    elif "Spindle memory updated" not in pr.read_text(encoding="utf-8"):
        pr.write_text(pr.read_text(encoding="utf-8").rstrip() + "\n" + line + "\n", encoding="utf-8")
        print("Memory checkbox added to your PR template")
    if "Spindle memory stamp" not in pr.read_text(encoding="utf-8"):
        pr.write_text(pr.read_text(encoding="utf-8").rstrip() + "\n\nSpindle memory stamp: [output of `spindle.py stamp spindle`]\n",
                      encoding="utf-8")

    if a.ci or had_ci:
        wf = gh / "workflows" / "spindle.yml"
        write_localised(HERE / "vscode" / "spindle-ci.yml", wf, skills_rel)
        print("CI workflow added: .github/workflows/spindle.yml (check, secret scan, retrieval evals)")

    block = localise((HERE / "vscode" / "copilot-instructions-spindle.md").read_text(encoding="utf-8"), skills_rel)
    action = merge_instructions(gh / "copilot-instructions.md", block)
    print(f"Spindle instructions {action} .github/copilot-instructions.md")
    if (target / "AGENTS.md").is_file():
        merge_instructions(target / "AGENTS.md", block.replace("## Spindle memory", "## Spindle memory (team memory for every assistant)"))
        print("Spindle section added to AGENTS.md (read by Claude Code, Copilot's coding agent and other tools)")

    if not a.no_mcp and ((target / ".mcp.json").is_file() or (target / ".claude").is_dir()):
        if merge_claude_mcp(target / ".mcp.json", a.python, skills_rel):
            print("MCP server 'spindle' registered in .mcp.json for Claude Code")
        else:
            print("Couldn't parse .mcp.json. Add a 'spindle' entry under mcpServers by hand.")

    if not a.no_mcp:
        ok, snippet = merge_mcp(target / ".vscode" / "mcp.json", a.python, skills_rel)
        if ok:
            print("MCP server 'spindle' registered in .vscode/mcp.json")
        else:
            print("Couldn't parse your .vscode/mcp.json (comments?). Add this under 'servers' by hand:\n" + snippet)

    sys.path.insert(0, str(HERE / "skills" / "spindle" / "scripts"))
    import spindle  # noqa: E402
    if (web / "profile.md").is_file():
        print(f"Memory already exists at {web}, left as is")
    else:
        args = ["init", str(web), "--role", a.role] + (["--name", a.name] if a.name else []) \
            + (["--governed"] if a.governed else [])
        spindle.main(args)

    if not a.no_hook and (target / ".git").exists():
        r = subprocess.run([sys.executable, str(skills_dir / "spindle" / "scripts" / "spindle_hook.py"), "--install"],
                           cwd=target, capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        print("Each teammate adds the reminder to their own clone once with: "
              f"python3 {skills_rel}/spindle/scripts/spindle_hook.py --install")

    pkg = target / "package.json"
    if pkg.is_file():
        try:
            scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {})
        except ValueError:
            scripts = {}
        if "ai:sync" in scripts:
            npm = shutil.which("npm")
            r = subprocess.run([npm, "run", "-s", "ai:sync"], cwd=target, capture_output=True, text=True) if npm else None
            if r is not None and r.returncode == 0:
                print("Ran npm run ai:sync, so Claude Code gets the Spindle commands too")
            else:
                print("This repo syncs Copilot prompts to Claude Code: run `npm run ai:sync` and commit the result")

    print("\nNext: open the folder in VS Code, start the 'spindle' MCP server if prompted, "
          "switch Copilot Chat to Agent mode and run /spindle-harvest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
