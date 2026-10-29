#!/usr/bin/env python3
"""Spider: a role-aware work memory kept as plain markdown.

Standard library only. Python 3.8+.

  spider.py init <web> --role <role> [--name NAME]
  spider.py add <web> <thread> <kind> "text" [--type T] [--name N] [--due D] [--open] [--date D] [--src S]
  spider.py done <web> <thread> "part of the commitment text"
  spider.py index <web>
  spider.py check <web>
  spider.py check-role <role-file>
  spider.py find <web> [query] [--kind K] [--type T] [--tag G] [--open] [--since D]
  spider.py due <web> [--days N]
  spider.py match <web> "scenario text"
  spider.py export <web> <kit.zip|folder> [--name N] [--redact "Acme, Northwind"] [--dry-run]
  spider.py import <web> <kit.zip|folder> [--dry-run]
  spider.py roles
"""
import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue  # noqa: E402

HERE = Path(__file__).resolve().parent
ROLES_DIR = HERE.parent / "roles"

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STRAND_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \[([a-z][a-z0-9-]*)([^\]]*)\] (.+)$")
LINK_RE = re.compile(r"\[\[([a-z0-9-]+)\]\]")
FLAGS = {"open", "done", "superseded"}
STATUSES = {"active", "paused", "closed"}


# ---------- parsing ----------

def parse_value(raw):
    raw = re.split(r"\s+#", raw.strip(), maxsplit=1)[0].strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()] if inner else []
    if "#" in raw:
        raw = raw.split("#", 1)[0].strip()
    return raw.strip("'\"")


def split_frontmatter(text):
    """Return (meta dict, body str). Only flat key: value and [a, b] lists."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    meta, end = {}, None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip()] = parse_value(v)
    if end is None:
        return {}, text
    return meta, "\n".join(lines[end + 1:])


def dump_frontmatter(meta):
    out = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            out.append(f"{k}: [{', '.join(v)}]")
        else:
            out.append(f"{k}: {v}")
    out.append("---")
    return "\n".join(out)


def parse_strand(line):
    m = STRAND_RE.match(line.rstrip())
    if not m:
        return None
    date, kind, attr_str, text = m.groups()
    attrs, flags = {}, set()
    for tok in attr_str.split():
        if ":" in tok:
            k, v = tok.split(":", 1)
            attrs[k] = v
        else:
            flags.add(tok)
    return {"date": date, "kind": kind, "attrs": attrs, "flags": flags,
            "text": text, "links": LINK_RE.findall(text), "raw": line.rstrip()}


class Thread:
    def __init__(self, path):
        self.path = Path(path)
        self.meta, self.body = split_frontmatter(self.path.read_text(encoding="utf-8"))
        self.strands = []
        self.bad_lines = []
        for n, line in enumerate(self.body.splitlines(), start=1):
            if line.startswith("- ") and DATE_RE.match(line[2:12] if len(line) >= 12 else ""):
                s = parse_strand(line)
                if s:
                    self.strands.append(s)
                else:
                    self.bad_lines.append((n, line))

    @property
    def id(self):
        return self.meta.get("id", self.path.stem)

    def listv(self, key):
        v = self.meta.get(key, [])
        return v if isinstance(v, list) else [v] if v else []

    def open_commitments(self):
        return [s for s in self.strands if "open" in s["flags"] and "superseded" not in s["flags"]]


def load_role(path):
    meta, body = split_frontmatter(Path(path).read_text(encoding="utf-8"))
    return meta, body


def resolve_role(role):
    p = Path(role)
    if p.is_file():
        return p
    cand = ROLES_DIR / (role if role.endswith(".md") else role + ".md")
    if cand.is_file():
        return cand
    raise SystemExit(f"Role not found: {role}. Run 'spider.py roles' to list them.")


def load_web(web):
    web = Path(web)
    if not (web / "profile.md").is_file():
        raise SystemExit(f"No web at {web} (profile.md missing). Run 'spider.py init' first.")
    profile, _ = split_frontmatter((web / "profile.md").read_text(encoding="utf-8"))
    role_meta, _ = load_role(web / "role.md") if (web / "role.md").is_file() else ({}, "")
    threads = []
    tdir = web / "threads"
    if tdir.is_dir():
        for p in sorted(tdir.rglob("*.md")):
            if "_archive" in p.parts:
                continue
            threads.append(Thread(p))
    return profile, role_meta, threads


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "untitled"


def today():
    return dt.date.today().isoformat()


# ---------- commands ----------

def cmd_roles(_):
    for p in sorted(ROLES_DIR.glob("*.md")):
        meta, _ = load_role(p)
        print(f"{p.stem:24} {meta.get('title', '')}")


def check_role_meta(meta):
    errs = []
    for key in ("title", "thread_types", "strand_kinds"):
        if key not in meta:
            errs.append(f"missing '{key}'")
    for key in ("thread_types", "strand_kinds"):
        v = meta.get(key)
        if key in meta and (not isinstance(v, list) or not v):
            errs.append(f"'{key}' must be a non-empty [a, b] list")
        elif isinstance(v, list):
            for x in v:
                if not ID_RE.match(x):
                    errs.append(f"'{key}' entry '{x}' must be lowercase letters, digits, hyphens")
    if "stale_after_days" in meta and not str(meta["stale_after_days"]).isdigit():
        errs.append("'stale_after_days' must be a whole number")
    return errs


def cmd_check_role(a):
    meta, body = load_role(a.role)
    errs = check_role_meta(meta)
    for section in ("## Capture", "## Never store", "## Shortcuts"):
        if section not in body:
            errs.append(f"missing section '{section}'")
    if errs:
        for e in errs:
            print(f"ERROR {a.role}: {e}")
        return 1
    print(f"OK {a.role}")
    return 0


def cmd_init(a):
    web = Path(a.web)
    if (web / "profile.md").exists():
        raise SystemExit(f"A web already exists at {web}. Nothing changed.")
    role_path = resolve_role(a.role)
    meta, _ = load_role(role_path)
    errs = check_role_meta(meta)
    if errs:
        raise SystemExit("Role file has problems: " + "; ".join(errs))
    (web / "threads").mkdir(parents=True, exist_ok=True)
    for t in meta["thread_types"]:
        (web / "threads" / t).mkdir(exist_ok=True)
    (web / "threads" / "_archive").mkdir(exist_ok=True)
    shutil.copyfile(role_path, web / "role.md")
    profile = {
        "name": a.name or "Your name",
        "role": role_path.stem,
        "capture_mode": "confirm",
        "stale_after_days": meta.get("stale_after_days", "90"),
    }
    (web / "profile.md").write_text(
        dump_frontmatter(profile) + "\n- Add your own never-store rules or preferences here, one per line.\n",
        encoding="utf-8")
    write_index(web)
    print(f"Web created at {web} for role '{role_path.stem}'. Thread types: {', '.join(meta['thread_types'])}")
    return 0


def find_thread(threads, key):
    key_l = key.lower()
    for t in threads:
        if t.id == key_l:
            return t
    for t in threads:
        names = [t.meta.get("name", "")] + t.listv("aliases")
        if any(n.lower() == key_l for n in names if n):
            return t
    return None


def cmd_add(a):
    web = Path(a.web)
    profile, role, threads = load_web(web)
    kinds = role.get("strand_kinds") or []
    types = role.get("thread_types") or []
    if kinds and a.kind not in kinds:
        raise SystemExit(f"Kind '{a.kind}' isn't in this role. Use one of: {', '.join(kinds)}")
    date = a.date or today()
    if not DATE_RE.match(date):
        raise SystemExit("--date must be YYYY-MM-DD")
    if a.due and not DATE_RE.match(a.due):
        raise SystemExit("--due must be YYYY-MM-DD")
    t = find_thread(threads, a.thread)
    if t is None:
        if not a.type:
            raise SystemExit(f"No thread '{a.thread}'. Pass --type ({', '.join(types)}) to create it.")
        if types and a.type not in types:
            raise SystemExit(f"Type '{a.type}' isn't in this role. Use one of: {', '.join(types)}")
        tid = slugify(a.thread)
        path = web / "threads" / a.type / f"{tid}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {"id": tid, "type": a.type, "name": a.name or a.thread, "aliases": [],
                "tags": [], "status": "active", "links": []}
        path.write_text(dump_frontmatter(meta) + "\n", encoding="utf-8")
        t = Thread(path)
    attrs = []
    if a.kind == "commitment" or a.open:
        attrs.append("open")
    if a.due:
        attrs.append(f"due:{a.due}")
    text = " ".join(a.text.split())
    if a.src:
        text += f" src:{a.src}"
    line = f"- {date} [{a.kind}{(' ' + ' '.join(attrs)) if attrs else ''}] {text}"
    if not parse_strand(line):
        raise SystemExit("Could not build a valid strand from that input.")
    # keep frontmatter links in step with [[links]] in the text
    new_links = [l for l in LINK_RE.findall(text) if l not in t.listv("links") and l != t.id]
    triggers = [w.strip() for w in (a.use_when or "").split(",") if w.strip()]
    new_triggers = [w for w in triggers if w.lower() not in [x.lower() for x in t.listv("use_when")]]
    raw = t.path.read_text(encoding="utf-8")
    if new_links or new_triggers:
        meta, body = split_frontmatter(raw)
        if new_links:
            meta["links"] = (meta.get("links") if isinstance(meta.get("links"), list) else []) + new_links
        if new_triggers:
            meta["use_when"] = t.listv("use_when") + new_triggers
        raw = dump_frontmatter(meta) + "\n" + body.lstrip("\n")
    if not raw.endswith("\n"):
        raw += "\n"
    t.path.write_text(raw + line + "\n", encoding="utf-8")
    write_index(web)
    print(f"Added to {t.id}: {line}")
    return 0


def cmd_done(a):
    web = Path(a.web)
    _, _, threads = load_web(web)
    t = find_thread(threads, a.thread)
    if t is None:
        raise SystemExit(f"No thread '{a.thread}'.")
    frag = a.match.lower()
    matches = [s for s in t.open_commitments() if frag in s["text"].lower()]
    if not matches:
        raise SystemExit(f"No open commitment in '{t.id}' matching '{a.match}'.")
    if len(matches) > 1:
        print("More than one match, be more specific:")
        for s in matches:
            print("  ", s["raw"])
        return 1
    old = matches[0]["raw"]
    new = re.sub(r"\[([a-z0-9-]+)([^\]]*)\]",
                 lambda m: "[" + m.group(1) + re.sub(r"\bopen\b", "done", m.group(2)) + "]", old, count=1)
    raw = t.path.read_text(encoding="utf-8")
    t.path.write_text(raw.replace(old, new, 1), encoding="utf-8")
    write_index(web)
    print(f"Closed in {t.id}: {new}")
    return 0


STOP = set("""a an and are as at be by can check click create do does for from has have how i in into is it
its make new of on or our should that the their then this to test tests using user verify via when where
which will with write script scenario steps step page able add we you""".split())


def trigger_hit(trigger, text):
    t = trigger.lower().strip()
    return bool(t) and re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", text) is not None


def cmd_match(a):
    """What memory and code already cover the scenario described in the text."""
    web = Path(a.web)
    _, _, threads = load_web(web)
    text = " ".join(a.text).lower()
    words = {w for w in re.findall(r"[a-z0-9]+", text) if len(w) >= 3 and w not in STOP}
    hits = []
    for t in threads:
        if t.meta.get("status", "active") == "closed":
            continue
        triggers = t.listv("use_when") + t.listv("aliases") + [t.meta.get("name", "")]
        found = [g for g in triggers if trigger_hit(g, text)]
        if found:
            hits.append((t, found))
    order = {"pattern": 0, "app": 1, "framework": 2, "pack": 3}
    hits.sort(key=lambda h: (order.get(h[0].meta.get("type"), 9), h[0].id))
    print("Memory that applies:")
    if not hits:
        print("  none matched. Try other words, or add use_when triggers to the pattern threads.")
    for t, found in hits:
        print(f"  [{t.meta.get('type')}] {t.id}: {t.meta.get('name', t.id)} (matched: {', '.join(found)})")
        keep = [s for s in t.strands if "superseded" not in s["flags"]
                and s["kind"] in ("pattern", "gotcha", "convention", "asset", "data", "env", "decision")]
        for s in keep[-4:]:
            print(f"      {s['date']} [{s['kind']}] {s['text']}")
    cat = web / "catalogue.md"
    rows = catalogue.parse(cat.read_text(encoding="utf-8")) if cat.is_file() else []
    for t, _ in hits:  # a matched pattern's triggers widen the code search
        words |= {w for g in t.listv("use_when") for w in re.findall(r"[a-z0-9]+", g.lower()) if len(w) >= 3}
    scored = []
    for r in rows:
        sym_words = catalogue.words_of(r["symbol"]) | catalogue.words_of(Path(r["path"]).stem)
        doc_words = catalogue.words_of(r["doc"])
        score = 2 * len(words & sym_words) + len(words & doc_words)
        score += sum(1 for w in words if len(w) >= 4 and any(w in s for s in sym_words) and w not in sym_words)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]["path"], x[1]["symbol"]))
    print("\nCode you can reuse:")
    if not rows:
        print("  no catalogue yet. Run harvest to build it.")
    elif not scored:
        print("  nothing in the catalogue matched.")
    for score, r in scored[:a.limit]:
        doc = f": {r['doc']}" if r["doc"] else ""
        print(f"  {r['path']} :: {r['symbol']}{doc}")
    return 0


def write_index(web):
    web = Path(web)
    _, _, threads = load_web(web)
    lines = ["# Index", "", f"Generated {today()}. {len(threads)} threads. Run 'spider.py index' to refresh.", ""]
    cat = web / "catalogue.md"
    if cat.is_file():
        n_caps = len(catalogue.parse(cat.read_text(encoding="utf-8")))
        lines += [f"Capability catalogue: {n_caps} reusable functions, classes and fixtures in catalogue.md. "
                  "Search it with 'spider.py match' before writing a new helper.", ""]
    for t in sorted(threads, key=lambda x: (x.meta.get("type", ""), x.id)):
        last = max((s["date"] for s in t.strands), default="none")
        aliases = t.listv("aliases")
        tags = " ".join("#" + g for g in t.listv("tags"))
        bits = [f"- [{t.meta.get('type', '?')}] {t.id}: {t.meta.get('name', t.id)}"]
        if aliases:
            bits.append(f" (aka {', '.join(aliases)})")
        if tags:
            bits.append(f" {tags}")
        if t.listv("use_when"):
            bits.append(f" [use when: {', '.join(t.listv('use_when'))}]")
        n = len(t.strands)
        bits.append(f", {n} strand{'' if n == 1 else 's'}, last {last}, {len(t.open_commitments())} open")
        if t.meta.get("status", "active") != "active":
            bits.append(f", {t.meta.get('status')}")
        lines.append("".join(bits))
    (web / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_index(a):
    write_index(a.web)
    print(f"Index refreshed: {Path(a.web) / 'index.md'}")
    return 0


def cmd_check(a):
    web = Path(a.web)
    profile, role, threads = load_web(web)
    errs, warns = [], []
    kinds = set(role.get("strand_kinds") or [])
    types = set(role.get("thread_types") or [])
    if not role:
        warns.append("role.md missing: kinds and types can't be checked")
    if profile.get("capture_mode") not in ("confirm", "auto", "manual"):
        errs.append("profile.md: capture_mode must be confirm, auto or manual")
    ids = {}
    all_names = {}
    for t in threads:
        rel = t.path.relative_to(web)
        if not t.meta:
            errs.append(f"{rel}: missing frontmatter")
            continue
        tid = t.meta.get("id")
        if not tid:
            errs.append(f"{rel}: missing id")
        elif tid != t.path.stem:
            errs.append(f"{rel}: id '{tid}' doesn't match file name")
        elif not ID_RE.match(tid):
            errs.append(f"{rel}: id must be lowercase letters, digits, hyphens")
        if tid in ids:
            errs.append(f"{rel}: duplicate id '{tid}' (also {ids[tid]})")
        ids[tid] = rel
        if not t.meta.get("name"):
            errs.append(f"{rel}: missing name")
        ttype = t.meta.get("type")
        if types and ttype not in types:
            errs.append(f"{rel}: type '{ttype}' isn't in the role")
        if ttype and t.path.parent.name != ttype:
            errs.append(f"{rel}: type '{ttype}' doesn't match folder '{t.path.parent.name}'")
        st = t.meta.get("status", "active")
        if st not in STATUSES:
            errs.append(f"{rel}: status '{st}' should be active, paused or closed")
        for key in ("aliases", "tags", "links", "use_when"):
            if key in t.meta and not isinstance(t.meta[key], list):
                errs.append(f"{rel}: '{key}' must be a [a, b] list")
        for n in [t.meta.get("name", "")] + t.listv("aliases"):
            if n:
                k = n.lower()
                if k in all_names and all_names[k] != tid:
                    warns.append(f"{rel}: name/alias '{n}' also used by '{all_names[k]}' (duplicate thread?)")
                all_names[k] = tid
        for n, line in t.bad_lines:
            errs.append(f"{rel}:{n}: strand doesn't match '- YYYY-MM-DD [kind attrs] text': {line[:60]}")
        for s in t.strands:
            where = f"{rel}: {s['date']} [{s['kind']}]"
            try:
                dt.date.fromisoformat(s["date"])
            except ValueError:
                errs.append(f"{where}: bad date")
            if kinds and s["kind"] not in kinds:
                errs.append(f"{where}: kind '{s['kind']}' isn't in the role")
            bad_flags = s["flags"] - FLAGS
            if bad_flags:
                errs.append(f"{where}: unknown flag(s) {', '.join(sorted(bad_flags))}")
            if {"open", "done"} <= s["flags"]:
                errs.append(f"{where}: can't be both open and done")
            if "due" in s["attrs"]:
                try:
                    dt.date.fromisoformat(s["attrs"]["due"])
                except ValueError:
                    errs.append(f"{where}: bad due date")
    for t in threads:
        rel = t.path.relative_to(web)
        for l in set(t.listv("links")) | {l for s in t.strands for l in s["links"]}:
            if l not in ids:
                warns.append(f"{rel}: link to missing thread '{l}'")
    stale = int(profile.get("stale_after_days") or role.get("stale_after_days") or 90)
    cutoff = (dt.date.today() - dt.timedelta(days=stale)).isoformat()
    for t in threads:
        last = max((s["date"] for s in t.strands), default=None)
        if last and last < cutoff and t.meta.get("status", "active") == "active":
            warns.append(f"{t.path.relative_to(web)}: no strands since {last} (stale after {stale} days)")
    for e in errs:
        print("ERROR", e)
    for w in warns:
        print("WARN ", w)
    def pl(n, w):
        return f"{n} {w}{'' if n == 1 else 's'}"
    print(f"{pl(len(threads), 'thread')}, {pl(sum(len(t.strands) for t in threads), 'strand')}, "
          f"{pl(len(errs), 'error')}, {pl(len(warns), 'warning')}")
    return 1 if errs else 0


def iter_strands(threads):
    for t in threads:
        for s in t.strands:
            yield t, s


def print_hit(t, s):
    print(f"{t.id:22} {s['raw'][2:]}")


def cmd_find(a):
    _, _, threads = load_web(a.web)
    q = (a.query or "").lower()
    hits = 0
    for t, s in iter_strands(threads):
        if a.type and t.meta.get("type") != a.type:
            continue
        if a.tag and a.tag not in t.listv("tags"):
            continue
        if a.kind and s["kind"] != a.kind:
            continue
        if a.open and ("open" not in s["flags"] or "superseded" in s["flags"]):
            continue
        if a.since and s["date"] < a.since:
            continue
        if not a.all and "superseded" in s["flags"]:
            continue
        if q:
            hay = " ".join([s["text"], t.id, t.meta.get("name", "")] + t.listv("aliases")).lower()
            if q not in hay:
                continue
        print_hit(t, s)
        hits += 1
    if not hits:
        print("Nothing found.")
    return 0


def cmd_due(a):
    _, _, threads = load_web(a.web)
    now = dt.date.today()
    horizon = (now + dt.timedelta(days=a.days)).isoformat()
    rows = []
    undated = []
    for t, s in iter_strands(threads):
        if "open" not in s["flags"] or "superseded" in s["flags"]:
            continue
        due = s["attrs"].get("due")
        if due and due <= horizon:
            rows.append((due, t, s))
        elif not due:
            undated.append((t, s))
    rows.sort(key=lambda r: r[0])
    for due, t, s in rows:
        tag = "OVERDUE" if due < now.isoformat() else "due    "
        print(f"{tag} {due}  {t.id:20} {s['text']}")
    if undated:
        print(f"\n{len(undated)} open commitment(s) with no due date:")
        for t, s in undated:
            print(f"        {s['date']}  {t.id:20} {s['text']}")
    if not rows and not undated:
        print("Nothing open.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="spider", description="Role-aware work memory in plain markdown.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("roles", help="list built-in roles").set_defaults(fn=cmd_roles)

    s = sub.add_parser("init", help="create a new web")
    s.add_argument("web"); s.add_argument("--role", required=True); s.add_argument("--name")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("add", help="add a strand to a thread")
    s.add_argument("web"); s.add_argument("thread"); s.add_argument("kind"); s.add_argument("text")
    s.add_argument("--type"); s.add_argument("--name"); s.add_argument("--due")
    s.add_argument("--open", action="store_true"); s.add_argument("--date"); s.add_argument("--src")
    s.add_argument("--use-when", help="comma-separated words that should bring this thread up")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("done", help="mark an open commitment done")
    s.add_argument("web"); s.add_argument("thread"); s.add_argument("match")
    s.set_defaults(fn=cmd_done)

    s = sub.add_parser("index", help="rebuild index.md"); s.add_argument("web"); s.set_defaults(fn=cmd_index)
    s = sub.add_parser("check", help="validate a web"); s.add_argument("web"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("check-role", help="validate a role file"); s.add_argument("role")
    s.set_defaults(fn=cmd_check_role)

    s = sub.add_parser("find", help="search strands")
    s.add_argument("web"); s.add_argument("query", nargs="?")
    s.add_argument("--kind"); s.add_argument("--type"); s.add_argument("--tag")
    s.add_argument("--open", action="store_true"); s.add_argument("--since")
    s.add_argument("--all", action="store_true", help="include superseded strands")
    s.set_defaults(fn=cmd_find)

    s = sub.add_parser("match", help="memory and reusable code that cover a scenario")
    s.add_argument("web"); s.add_argument("text", nargs="+"); s.add_argument("--limit", type=int, default=10)
    s.set_defaults(fn=cmd_match)

    def run_kit(name):
        def go(a):
            import kit
            return getattr(kit, name)(a)
        return go

    s = sub.add_parser("export", help="export reusable memory as a kit for another project")
    s.add_argument("web"); s.add_argument("out", help="kit file (.zip) or a new folder")
    s.add_argument("--name"); s.add_argument("--redact", help="comma-separated client names to replace with [client]")
    s.add_argument("--types", help="thread types to include (default framework,pattern)")
    s.add_argument("--kinds", help="strand kinds to include (default convention,pattern,gotcha,decision,asset,insight)")
    s.add_argument("--threads", help="export only these thread ids")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=run_kit("cmd_export"))

    s = sub.add_parser("import", help="merge a memory kit into this memory")
    s.add_argument("web"); s.add_argument("kit"); s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=run_kit("cmd_import"))

    s = sub.add_parser("due", help="open commitments due soon or overdue")
    s.add_argument("web"); s.add_argument("--days", type=int, default=7)
    s.set_defaults(fn=cmd_due)

    a = p.parse_args(argv)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
