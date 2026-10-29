"""Memory kits: take reusable memory from one project to another.

A kit is a folder or .zip holding kit.md (what's inside) and threads/<type>/<id>.md.
Export picks the reusable parts (framework conventions, patterns, gotchas, decisions)
and scrubs client details. Import merges a kit into another project's memory.

  spider.py export <web> <kit.zip|folder> [--name N] [--redact "Acme, Northwind"] [--types framework,pattern]
                   [--kinds ...] [--threads id,id] [--dry-run]
  spider.py import <web> <kit.zip|folder> [--dry-run]
"""
import datetime as dt
import re
import zipfile
from pathlib import Path

import spider

DEFAULT_TYPES = ["framework", "pattern"]
DEFAULT_KINDS = ["convention", "pattern", "gotcha", "decision", "asset", "insight"]
URL_RE = re.compile(r"\bhttps?://\S+", re.I)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
SRC_RE = re.compile(r"\s+src:.*$")
KIT_PATH_RE = re.compile(r"^threads/[a-z0-9-]+/[a-z0-9][a-z0-9-]*\.md$")


def _list(v):
    return v if isinstance(v, list) else ([v] if v else [])


def scrub(text, terms, keep_ids):
    """Remove client-identifying details from one strand's text."""
    text = SRC_RE.sub("", text)
    text = URL_RE.sub("[url removed]", text)
    text = EMAIL_RE.sub("[email removed]", text)
    text = IP_RE.sub("[ip removed]", text)
    text = spider.LINK_RE.sub(lambda m: f"[[{m.group(1)}]]" if m.group(1) in keep_ids else m.group(1), text)
    for t in sorted(terms, key=len, reverse=True):
        text = re.sub(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", "[client]", text, flags=re.I)
    return text


def source_only(s):
    """Harvest lines that only describe the source repo's inventory, not how the team works."""
    if "src:harvest" not in s["text"]:
        return False
    return s["kind"] == "gotcha" or re.match(r"^\d+ test files", s["text"]) is not None


def select(threads, types, kinds, only_ids):
    out = []
    for t in threads:
        if only_ids and t.id not in only_ids:
            continue
        if not only_ids and t.meta.get("type") not in types:
            continue
        strands = [s for s in t.strands if s["kind"] in kinds and "superseded" not in s["flags"]
                   and "open" not in s["flags"] and not source_only(s)]
        if strands:
            out.append((t, strands))
    return out


def cmd_export(a):
    web = Path(a.web)
    profile, role, threads = spider.load_web(web)
    types = [x.strip() for x in a.types.split(",")] if a.types else DEFAULT_TYPES
    kinds = [x.strip() for x in a.kinds.split(",")] if a.kinds else DEFAULT_KINDS
    only = {x.strip() for x in a.threads.split(",")} if a.threads else set()
    chosen = select(threads, types, kinds, only)
    if not chosen:
        raise SystemExit("Nothing to export with those filters.")
    name = spider.slugify(a.name or f"{web.resolve().parent.name}-kit")
    # framework threads are named after the source repo: give them neutral ids in the kit
    new_ids, n_fw = {}, 0
    for t, _ in chosen:
        if t.meta.get("type") == "framework":
            n_fw += 1
            new_ids[t.id] = f"{name}-framework" + (f"-{n_fw}" if n_fw > 1 else "")
    keep_ids = {new_ids.get(t.id, t.id) for t, _ in chosen}

    # client terms: what the user names, plus names and aliases of threads that stay behind (apps, packs, people)
    terms = {x.strip() for x in (a.redact or "").split(",") if len(x.strip()) >= 2}
    for t in threads:
        if t.id not in keep_ids and t.meta.get("type") in ("app", "account", "person", "pack", "opportunity", "vendor"):
            terms |= {n for n in [t.meta.get("name", "")] + t.listv("aliases") if len(n) >= 3}
            terms.add(t.id)
    if profile.get("name") and profile.get("name") != "Your name":
        terms.add(profile["name"])

    for old in new_ids:
        terms.add(old)
    files, n_strands, n_scrubbed = {}, 0, 0
    for t, strands in chosen:
        tid = new_ids.get(t.id, t.id)
        tname = (f"{name} framework" if t.id in new_ids else scrub(t.meta.get("name", t.id), terms, keep_ids))
        meta = {"id": tid, "type": t.meta.get("type"), "name": tname,
                "aliases": [scrub(x, terms, keep_ids) for x in t.listv("aliases") if scrub(x, terms, keep_ids) == x],
                "tags": t.listv("tags"), "status": "active",
                "links": [new_ids.get(l, l) for l in t.listv("links") if new_ids.get(l, l) in keep_ids]}
        if t.listv("use_when"):
            meta["use_when"] = t.listv("use_when")
        lines = []
        for s in strands:
            attrs = " ".join(sorted(s["flags"] - {"open", "done", "superseded"}))
            text = spider.LINK_RE.sub(lambda m: f"[[{new_ids.get(m.group(1), m.group(1))}]]", s["text"])
            clean = scrub(text, terms, keep_ids)
            n_scrubbed += clean != text
            lines.append(f"- {s['date']} [{s['kind']}{(' ' + attrs) if attrs else ''}] {clean}")
            n_strands += 1
        files[f"threads/{meta['type']}/{tid}.md"] = spider.dump_frontmatter(meta) + "\n" + "\n".join(lines) + "\n"

    manifest = spider.dump_frontmatter({
        "kit": name, "created": spider.today(), "role": profile.get("role", ""),
        "threads": str(len(files)), "strands": str(n_strands),
        "types": types if not only else sorted({t.meta.get("type") for t, _ in chosen}), "kinds": kinds,
    }) + (
        f"\n# Spider memory kit: {name}\n\n"
        f"Reusable memory exported from another project: {len(files)} threads, {n_strands} strands.\n\n"
        "- Client details were scrubbed: source references, URLs, emails, IP addresses, linked threads that "
        f"were not exported, and {len(terms)} client names and aliases (replaced with [client]).\n"
        "- Open commitments and superseded lines were left out.\n"
        "- Asset paths point to files in the source project. They only apply if that code was copied across.\n"
        "- Review every file before sharing, and never move a kit between clients without checking it.\n\n"
        "Import with: python3 .github/skills/spider/scripts/spider.py import spider <this kit>\n\n"
        "## Threads\n\n" + "\n".join(f"- {p}" for p in sorted(files)) + "\n")

    print(f"Kit '{name}': {len(files)} threads, {n_strands} strands, {n_scrubbed} strands scrubbed, "
          f"{len(terms)} client terms redacted")
    for p in sorted(files):
        print(f"  {p}")
    if a.dry_run:
        print("\nDry run. Nothing written. Check the list, add --redact for any client names Spider can't know, "
              "then run again without --dry-run.")
        for p in sorted(files)[:1]:
            print(f"\nPreview of {p}:\n" + files[p])
        return 0
    out = Path(a.out)
    if out.suffix.lower() == ".zip":
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("kit.md", manifest)
            for p, text in files.items():
                z.writestr(p, text)
    else:
        if out.exists() and any(out.iterdir()):
            raise SystemExit(f"{out} already exists and isn't empty. Pick a new folder or a .zip name.")
        for p, text in {"kit.md": manifest, **files}.items():
            (out / p).parent.mkdir(parents=True, exist_ok=True)
            (out / p).write_text(text, encoding="utf-8")
    print(f"\nWrote {out}. Open it and review every file before you share it.")
    return 0


def read_kit(path):
    path = Path(path)
    files = {}
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n == "kit.md" or KIT_PATH_RE.match(n):
                    files[n] = z.read(n).decode("utf-8", errors="replace")
    elif path.is_dir():
        if (path / "kit.md").is_file():
            files["kit.md"] = (path / "kit.md").read_text(encoding="utf-8")
        for p in (path / "threads").rglob("*.md") if (path / "threads").is_dir() else []:
            rel = p.relative_to(path).as_posix()
            if KIT_PATH_RE.match(rel) and not p.is_symlink():
                files[rel] = p.read_text(encoding="utf-8")
    else:
        raise SystemExit(f"Not a kit: {path}")
    if "kit.md" not in files:
        raise SystemExit(f"{path} has no kit.md, so it isn't a Spider memory kit.")
    return files


def cmd_import(a):
    web = Path(a.web)
    _, role, threads = spider.load_web(web)
    files = read_kit(a.kit)
    kit_meta, _ = spider.split_frontmatter(files["kit.md"])
    kit_name = kit_meta.get("kit") or Path(a.kit).stem
    types, kinds = set(role.get("thread_types") or []), set(role.get("strand_kinds") or [])
    added_threads, added_strands, merged, skipped = 0, 0, 0, []
    plan = []
    for rel, text in sorted(files.items()):
        if rel == "kit.md":
            continue
        meta, body = spider.split_frontmatter(text)
        tid, ttype = meta.get("id", ""), meta.get("type", "")
        if not spider.ID_RE.match(tid or "") or rel != f"threads/{ttype}/{tid}.md":
            skipped.append(f"{rel}: id or type doesn't match its path")
            continue
        if types and ttype not in types:
            skipped.append(f"{rel}: this memory's role has no '{ttype}' threads")
            continue
        strands = [spider.parse_strand(l) for l in body.splitlines()]
        strands = [s for s in strands if s and (not kinds or s["kind"] in kinds)]
        existing = spider.find_thread(threads, tid)
        have = existing.path.read_text(encoding="utf-8") if existing else ""
        tag = f"src:kit-{kit_name}"
        new_lines = [f"{s['raw']} {tag}" for s in strands if s["text"] not in have]
        if not new_lines:
            continue
        plan.append((rel, meta, existing, new_lines))
        added_strands += len(new_lines)
        if existing:
            merged += 1
        else:
            added_threads += 1

    print(f"Kit '{kit_name}' ({kit_meta.get('created', '?')}, role {kit_meta.get('role', '?')})")
    for rel, meta, existing, lines in plan:
        print(f"  {'merge into' if existing else 'new      '} {rel}: {len(lines)} strand(s)")
    for s in skipped:
        print(f"  skipped   {s}")
    if not plan:
        print("Nothing new to import.")
        return 0
    if a.dry_run:
        print(f"\nDry run. Would add {added_threads} thread(s) and {added_strands} strand(s). Run again without --dry-run.")
        return 0

    for rel, meta, existing, lines in plan:
        if existing:
            raw = existing.path.read_text(encoding="utf-8")
            em, body = spider.split_frontmatter(raw)
            for key in ("use_when", "aliases", "tags"):
                cur = _list(em.get(key))
                extra = [x for x in _list(meta.get(key)) if x.lower() not in [c.lower() for c in cur]]
                if extra:
                    em[key] = cur + extra
            em["imported_from"] = list(dict.fromkeys(_list(em.get("imported_from")) + [kit_name]))
            raw = spider.dump_frontmatter(em) + "\n" + body.lstrip("\n")
            if not raw.endswith("\n"):
                raw += "\n"
            existing.path.write_text(raw + "\n".join(lines) + "\n", encoding="utf-8")
        else:
            meta["imported_from"] = [kit_name]
            meta["links"] = [l for l in _list(meta.get("links")) if spider.find_thread(threads, l) or
                             any(m.get("id") == l for _, m, _, _ in plan)]
            path = web / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(spider.dump_frontmatter(meta) + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    spider.write_index(web)
    print(f"\nImported {added_threads} new thread(s), merged into {merged}, {added_strands} strand(s) added, "
          f"each marked {tag if plan else ''}.")
    print("Next: run /spider-harvest in this repo so the catalogue reflects this project's own code, "
          "then check that asset paths from the kit exist here.")
    return 0
