#!/usr/bin/env python3
"""Spider MCP server (stdio). Standard library only.

Gives VS Code (Copilot agent mode), Claude and any MCP client proper tools
for the Spider memory instead of shelling out.

Web location: SPIDER_WEB env var, else ./spider in the working folder
(./spider-web for installs made before the rename).
"""
import contextlib
import io
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spider  # noqa: E402
import harvest  # noqa: E402

VERSION = "0.2.0"


def web_path():
    if os.environ.get("SPIDER_WEB"):
        return os.environ["SPIDER_WEB"]
    legacy = Path.cwd() / "spider-web"
    if (legacy / "profile.md").is_file() and not (Path.cwd() / "spider" / "profile.md").is_file():
        return str(legacy)
    return str(Path.cwd() / "spider")


def S(desc, props, required=()):
    return {"type": "object", "properties": props, "required": list(required), "description": desc}


STR = {"type": "string"}
TOOLS = [
    {"name": "spider_find",
     "description": "Search memory strands. Filter by text, kind (e.g. gotcha, asset, convention), "
                    "thread type (framework, app, pack, pattern), tag, or open commitments.",
     "inputSchema": S("", {"query": STR, "kind": STR, "type": STR, "tag": STR,
                           "open": {"type": "boolean"}, "since": STR})},
    {"name": "spider_match",
     "description": "Before writing tests or any new helper: describe the scenario in plain words and get the "
                    "patterns, gotchas and existing reusable code (functions, page objects, fixtures) that cover it.",
     "inputSchema": S("", {"text": STR, "limit": {"type": "integer"}}, ["text"])},
    {"name": "spider_read",
     "description": "Read one memory thread in full, by id, name or alias. Use 'index' for the index and "
                    "'catalogue' for the full capability catalogue.",
     "inputSchema": S("", {"thread": STR}, ["thread"])},
    {"name": "spider_add",
     "description": "Add one strand (dated fact) to a thread. Pass type and name to create a new thread. "
                    "Only call after the user has confirmed what to remember.",
     "inputSchema": S("", {"thread": STR, "kind": STR, "text": STR, "type": STR, "name": STR,
                           "due": STR, "src": STR, "use_when": STR}, ["thread", "kind", "text"])},
    {"name": "spider_done",
     "description": "Mark an open commitment done, matching part of its text.",
     "inputSchema": S("", {"thread": STR, "match": STR}, ["thread", "match"])},
    {"name": "spider_due",
     "description": "Open commitments that are overdue or due within N days.",
     "inputSchema": S("", {"days": {"type": "integer"}})},
    {"name": "spider_check",
     "description": "Validate the memory and report errors, duplicates, broken links and stale threads.",
     "inputSchema": S("", {})},
    {"name": "spider_export",
     "description": "Export reusable memory (framework conventions, patterns, gotchas, decisions) as a kit for "
                    "another project, with client details scrubbed. Always do a dry run first and show the user.",
     "inputSchema": S("", {"out": STR, "name": STR, "redact": STR, "types": STR, "threads": STR,
                           "dry_run": {"type": "boolean"}}, ["out"])},
    {"name": "spider_import",
     "description": "Merge a memory kit (.zip or folder) from another project into this memory. Dry run first.",
     "inputSchema": S("", {"kit": STR, "dry_run": {"type": "boolean"}}, ["kit"])},
    {"name": "spider_harvest",
     "description": "Scan a test automation repo (static, nothing executed) and propose framework memory. "
                    "Dry run unless write is true.",
     "inputSchema": S("", {"repo": STR, "name": STR, "write": {"type": "boolean"}}, ["repo"])},
]


def capture(fn, argv):
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = fn(argv)
        return out.getvalue().strip() or "Done.", bool(code)
    except SystemExit as e:
        msg = out.getvalue().strip()
        detail = e.code if isinstance(e.code, str) else f"exit {e.code}"
        return (msg + "\n" + detail).strip(), True


def call(name, args):
    web = web_path()
    if name == "spider_find":
        argv = ["find", web]
        if args.get("query"):
            argv.append(args["query"])
        for k in ("kind", "type", "tag", "since"):
            if args.get(k):
                argv += [f"--{k}", str(args[k])]
        if args.get("open"):
            argv.append("--open")
        return capture(spider.main, argv)
    if name == "spider_read":
        key = args["thread"]
        if key.lower() in ("index", "index.md", "catalogue", "catalogue.md"):
            p = Path(web) / ("catalogue.md" if key.lower().startswith("catalogue") else "index.md")
            return (p.read_text(encoding="utf-8"), False) if p.is_file() else (f"No index at {p}", True)
        try:
            _, _, threads = spider.load_web(web)
        except SystemExit as e:
            return str(e.code), True
        t = spider.find_thread(threads, key)
        if not t:
            return f"No thread '{key}'. Read 'index' to see what exists.", True
        return t.path.read_text(encoding="utf-8"), False
    if name == "spider_match":
        return capture(spider.main, ["match", web, args["text"], "--limit", str(args.get("limit", 10))])
    if name == "spider_add":
        argv = ["add", web, args["thread"], args["kind"], args["text"]]
        for k in ("type", "name", "due", "src", "use_when"):
            if args.get(k):
                argv += [f"--{k.replace('_', '-')}", str(args[k])]
        return capture(spider.main, argv)
    if name == "spider_done":
        return capture(spider.main, ["done", web, args["thread"], args["match"]])
    if name == "spider_due":
        return capture(spider.main, ["due", web, "--days", str(args.get("days", 7))])
    if name == "spider_check":
        text, err = capture(spider.main, ["check", web])
        return text, False  # findings are content, not a tool failure
    if name == "spider_export":
        argv = ["export", web, args["out"]]
        for k in ("name", "redact", "types", "threads"):
            if args.get(k):
                argv += [f"--{k}", str(args[k])]
        if args.get("dry_run", True):
            argv.append("--dry-run")
        return capture(spider.main, argv)
    if name == "spider_import":
        argv = ["import", web, args["kit"]] + (["--dry-run"] if args.get("dry_run", True) else [])
        return capture(spider.main, argv)
    if name == "spider_harvest":
        argv = [args["repo"], web]
        if args.get("name"):
            argv += ["--name", args["name"]]
        if args.get("write"):
            argv.append("--write")
        return capture(harvest.main, argv)
    return f"Unknown tool {name}", True


def handle(msg):
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if mid is None:
        return None  # notification
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "spider", "version": VERSION}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        try:
            text, is_err = call(params.get("name"), params.get("arguments") or {})
        except Exception as e:  # keep the server alive whatever happens
            text, is_err = f"{type(e).__name__}: {e}", True
        result = {"content": [{"type": "text", "text": text}], "isError": is_err}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
