"""Trust and quality for a shared memory.

  scan        secrets and personal details in memory files (CI fails on findings)
  candidates  governed patterns, their evidence, and whether they're ready to approve
  approve     a named person promotes a pattern (agents never do this)
  retire      a named person withdraws a pattern
  feedback    record that a pattern was used, helped, or pointed the wrong way
  efficacy    is each pattern helping? effective / watch / disputed / unused / insufficient-data
  prune       proposals to retire or reword patterns, never applied automatically
  stamp       a short hash of the memory, to put in PR notes and eval results
  eval        retrieval test cases: does match still find what it should?
  ci          check + scan + evals in one command, non-zero exit on failure

Governance is opt-in: `governance: governed` in profile.md (or init --governed).
In simple mode patterns are usable as soon as they are written, and these
commands still report evidence and usage.
"""
import contextlib
import datetime as dt
import hashlib
import io
import json
import re
from pathlib import Path

import redact as redactor
import spider

USAGE = "usage.log"
EVENTS = ("used", "helped", "wrong")
PATH_RE = re.compile(r"[\w./-]+\.(?:ts|tsx|js|jsx|py|java|cs|kt|feature|robot|json)\b")
DEFAULTS = {"min_evidence": 3, "min_authors": 2, "min_files": 0, "min_exposure": 3}


def setting(profile, key):
    try:
        return int(profile.get(key, DEFAULTS[key]))
    except (TypeError, ValueError):
        return DEFAULTS[key]


# ---------- usage log ----------

def read_usage(web):
    path = Path(web) / USAGE
    out = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and spider.DATE_RE.match(parts[0]) and parts[1] in EVENTS:
            out.append({"date": parts[0], "event": parts[1], "thread": parts[2],
                        "by": parts[3] if len(parts) > 3 else "", "why": parts[4] if len(parts) > 4 else ""})
    return out


def cmd_feedback(a):
    web = Path(a.web)
    _, _, threads = spider.load_web(web)
    t = spider.find_thread(threads, a.thread)
    if t is None:
        raise SystemExit(f"No thread '{a.thread}'.")
    event = "wrong" if a.wrong else "helped" if a.helped else "used"
    why, _ = redactor.redact(" ".join((a.why or "").split()))
    if event == "wrong" and not why:
        raise SystemExit('Say what it got wrong: --why "<what happened>"')
    by = spider.slugify(a.by) if a.by else ""
    line = "\t".join([spider.today(), event, t.id, by, why.replace("\t", " ")[:300]])
    with open(web / USAGE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"Recorded: {event} {t.id}" + (f" ({why})" if why else ""))
    return 0


# ---------- evidence and governance ----------

def evidence(t, usage):
    live = [s for s in t.strands if not s["flags"] & {"superseded", "avoid"} and s["kind"] in spider.GUIDANCE_KINDS]
    authors = {s["attrs"]["by"] for s in live if s["attrs"].get("by")}
    authors |= {u["by"] for u in usage if u["thread"] == t.id and u["by"] and u["event"] in ("used", "helped")}
    files = {p for s in live for p in PATH_RE.findall(s["text"])}
    return {"strands": len(live), "authors": len(authors), "files": len(files)}


def ready(ev, profile):
    need = {"strands": setting(profile, "min_evidence"), "authors": setting(profile, "min_authors"),
            "files": setting(profile, "min_files")}
    label = {"strands": "lines", "authors": "people", "files": "files"}
    gaps = [f"{label[k]} {ev[k]}/{n}" for k, n in need.items() if ev[k] < n]
    return not gaps, gaps


def governed_threads(profile, threads):
    return [t for t in threads if t.meta.get("type") in spider.governed_types(profile)]


def cmd_candidates(a):
    profile, _, threads = spider.load_web(a.web)
    usage = read_usage(a.web)
    rows = governed_threads(profile, threads)
    print(f"Governance: {profile.get('governance', 'simple')}. Ready to approve needs "
          f"{setting(profile, 'min_evidence')} lines, {setting(profile, 'min_authors')} people"
          + (f", {setting(profile, 'min_files')} files" if setting(profile, 'min_files') else "") + ".")
    if not rows:
        print("No pattern threads yet.")
    for t in sorted(rows, key=lambda x: x.id):
        state = spider.review_state(t, profile)
        ev = evidence(t, usage)
        ok, gaps = ready(ev, profile)
        note = "" if state != "candidate" else ("  READY: approve with spider.py approve" if ok else f"  needs {', '.join(gaps)}")
        print(f"  {state:9} {t.id:28} lines {ev['strands']}, people {ev['authors']}, files {ev['files']}{note}")
    return 0


def set_meta(t, updates):
    raw = t.path.read_text(encoding="utf-8")
    meta, body = spider.split_frontmatter(raw)
    meta.update(updates)
    t.path.write_text(spider.dump_frontmatter(meta) + "\n" + body.lstrip("\n"), encoding="utf-8")


def cmd_approve(a):
    web = Path(a.web)
    profile, _, threads = spider.load_web(web)
    t = spider.find_thread(threads, a.thread)
    if t is None or t.meta.get("type") not in spider.governed_types(profile):
        raise SystemExit(f"'{a.thread}' isn't a pattern thread.")
    by = " ".join(a.by.split())
    if len(by) < 2:
        raise SystemExit('Approval needs a person: --by "<your name>"')
    ok, gaps = ready(evidence(t, read_usage(web)), profile)
    if not ok and not a.override:
        raise SystemExit(f"Not enough evidence yet ({', '.join(gaps)}). "
                         'If you still want to approve, add --override "<why>".')
    updates = {"review": "approved", "approved_by": redactor.redact(by)[0], "approved_on": spider.today()}
    if a.override:
        updates["approve_note"] = redactor.redact(" ".join(a.override.split()))[0].replace(",", ";")
    set_meta(t, updates)
    spider.write_index(web)
    print(f"Approved {t.id} by {updates['approved_by']}" + (" (override)" if a.override else ""))
    return 0


def cmd_retire(a):
    web = Path(a.web)
    profile, _, threads = spider.load_web(web)
    t = spider.find_thread(threads, a.thread)
    if t is None:
        raise SystemExit(f"No thread '{a.thread}'.")
    if not a.why or len(" ".join(a.by.split())) < 2:
        raise SystemExit('Retiring needs --by "<name>" and --why "<reason>".')
    set_meta(t, {"review": "retired", "retired_by": redactor.redact(a.by)[0], "retired_on": spider.today(),
                 "retired_why": redactor.redact(" ".join(a.why.split()))[0].replace(",", ";")})
    spider.write_index(web)
    print(f"Retired {t.id}. It no longer appears in match results or kits.")
    return 0


# ---------- efficacy and prune ----------

def efficacy(web):
    profile, _, threads = spider.load_web(web)
    usage = read_usage(web)
    stale = int(profile.get("stale_after_days") or 90)
    cutoff = (dt.date.today() - dt.timedelta(days=stale)).isoformat()
    out = []
    for t in governed_threads(profile, threads):
        if spider.review_state(t, profile) == "retired":
            continue
        ev = [u for u in usage if u["thread"] == t.id]
        good = sum(1 for u in ev if u["event"] in ("used", "helped"))
        wrong = sum(1 for u in ev if u["event"] == "wrong")
        total = good + wrong
        last = max([s["date"] for s in t.strands] + [u["date"] for u in ev], default="")
        rate = wrong / total if total else 0
        if wrong >= 2 and rate >= 0.3:
            status = "disputed"
        elif total < setting(profile, "min_exposure"):
            status = "unused" if last and last < cutoff else "insufficient-data"
        elif rate > 0.1:
            status = "watch"
        else:
            status = "effective"
        reasons = [u["why"] for u in ev if u["event"] == "wrong" and u["why"]][-3:]
        out.append({"thread": t.id, "status": status, "used": good, "wrong": wrong, "last": last,
                    "review": spider.review_state(t, profile), "reasons": reasons})
    return out


def cmd_efficacy(a):
    rows = efficacy(a.web)
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("No pattern threads to measure.")
    for r in rows:
        print(f"  {r['status']:17} {r['thread']:28} used {r['used']}, wrong {r['wrong']}, last {r['last'] or 'never'}")
        for why in r["reasons"]:
            print(f"      wrong: {why}")
    return 0


def cmd_prune(a):
    rows = efficacy(a.web)
    profile, _, threads = spider.load_web(a.web)
    usage = read_usage(a.web)
    stale = int(profile.get("stale_after_days") or 90)
    cutoff = (dt.date.today() - dt.timedelta(days=stale)).isoformat()
    proposals = []
    for r in rows:
        if r["status"] == "disputed":
            proposals.append((r["thread"], "disputed: it pointed the wrong way more than once. Reword it or retire it."))
        elif r["status"] == "unused":
            proposals.append((r["thread"], f"unused since {r['last']}. Archive or retire it if it no longer applies."))
    for t in governed_threads(profile, threads):
        if spider.review_state(t, profile) == "candidate":
            last = max([s["date"] for s in t.strands], default="")
            if last and last < cutoff and not ready(evidence(t, usage), profile)[0]:
                proposals.append((t.id, f"candidate with no new evidence since {last}. Approve with --override or retire it."))
    if not proposals:
        print("Nothing to prune.")
        return 0
    print("Proposals (nothing has been changed; a person decides):")
    for tid, why in proposals:
        print(f"  {tid}: {why}")
        print(f'      spider.py retire <web> {tid} --by "<name>" --why "<reason>"')
    return 0


# ---------- stamp ----------

def stamp(web):
    web = Path(web)
    h = hashlib.sha256()
    files = sorted(p for p in (web / "threads").rglob("*.md") if "_archive" not in p.parts)
    for p in files + [web / "role.md"]:
        if p.is_file():
            h.update(p.relative_to(web).as_posix().encode())
            h.update(b"\0")
            h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return "spider-" + h.hexdigest()[:12], len(files)


def cmd_stamp(a):
    value, n = stamp(a.web)
    if a.json:
        print(json.dumps({"stamp": value, "threads": n}))
    else:
        print(f"{value}  ({n} threads)")
    return 0


# ---------- scan ----------

def scan(web, include_urls=False, fix=False):
    web = Path(web)
    findings = []
    paths = sorted((web / "threads").rglob("*.md")) + [p for p in [web / "profile.md", web / USAGE] if p.is_file()]
    for p in paths:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        changed = False
        for i, line in enumerate(lines):
            clean, labels = redactor.redact(line, keep_urls=not include_urls)
            if labels:
                findings.append((p.relative_to(web).as_posix(), i + 1, labels))
                if fix:
                    lines[i], changed = clean, True
        if changed:
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return findings


def cmd_scan(a):
    findings = scan(a.web, include_urls=a.urls, fix=a.fix)
    for f, n, labels in findings:
        print(f"  {f}:{n}: {', '.join(labels)}")
    if not findings:
        print("No secrets or personal details found.")
        return 0
    if a.fix:
        print(f"Removed {len(findings)} finding(s). Review the change before committing.")
        return 0
    print(f"{len(findings)} finding(s). Run again with --fix to remove them.")
    return 1


# ---------- evals ----------

def run_eval(web, cases):
    results = []
    for c in cases:
        res = spider.compute_match(web, c["request"], limit=int(c.get("top", 5)))
        threads = [t.id for t, _, _ in res["memory"]] + [t.id for t, _ in res["errors"]]
        code = [f"{r['path']} :: {r['symbol']}" for r, _, _ in res["code"]]
        missing = [e for e in c.get("expect", []) if not (e in threads or any(e in x for x in code))]
        unwanted = [f for f in c.get("forbid", []) if f in threads or any(f in x for x in code)]
        results.append({"id": c["id"], "pass": not missing and not unwanted, "missing": missing, "unwanted": unwanted})
    return results


def cmd_eval(a):
    try:
        cases = json.loads(Path(a.cases).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"Can't read eval cases: {e}")
    if not isinstance(cases, list) or not all(isinstance(c, dict) and "id" in c and "request" in c for c in cases):
        raise SystemExit('Eval cases must be a JSON list of {"id", "request", "expect": [...], "forbid": [...]}')
    results = run_eval(a.web, cases)
    passed = sum(r["pass"] for r in results)
    for r in results:
        detail = "" if r["pass"] else f"  missing {r['missing']}" + (f", unwanted {r['unwanted']}" if r["unwanted"] else "")
        print(f"  {'PASS' if r['pass'] else 'FAIL'} {r['id']}{detail}")
    value, _ = stamp(a.web)
    print(f"{passed}/{len(results)} passed  (memory {value})")
    code = 0
    if a.baseline and Path(a.baseline).is_file():
        base = json.loads(Path(a.baseline).read_text(encoding="utf-8"))
        worse = [r["id"] for r in results if base.get(r["id"]) and not r["pass"]]
        if worse:
            print(f"Worse than baseline: {', '.join(worse)}")
            code = 1
    elif passed < len(results) and not a.write_baseline:
        code = 1
    if a.write_baseline:
        Path(a.write_baseline).write_text(json.dumps({r["id"]: r["pass"] for r in results}, indent=2) + "\n",
                                          encoding="utf-8")
        print(f"Baseline written to {a.write_baseline}")
    return code


# ---------- ci ----------

def cmd_ci(a):
    web = Path(a.web)
    failed = []
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = spider.main(["check", str(web)])
    print("check: " + out.getvalue().strip().splitlines()[-1])
    if rc:
        print(out.getvalue())
        failed.append("check")
    findings = scan(web)
    print(f"scan: {len(findings)} finding(s)")
    for f, n, labels in findings:
        print(f"  {f}:{n}: {', '.join(labels)}")
    if findings:
        failed.append("scan")
    cases = Path(a.cases) if a.cases else web / "evals.json"
    if cases.is_file():
        base = web / "evals-baseline.json"
        ns = type("A", (), {"web": str(web), "cases": str(cases), "baseline": str(base) if base.is_file() else None,
                            "write_baseline": None})
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = cmd_eval(ns)
        print("evals: " + buf.getvalue().strip().splitlines()[-1])
        if rc:
            print(buf.getvalue())
            failed.append("evals")
    else:
        print("evals: none (add spider/evals.json to test retrieval)")
    print(f"memory: {stamp(web)[0]}")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("OK")
    return 0
