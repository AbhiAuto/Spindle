"""Capability catalogue: what each reusable file in an automation repo can do.

Built from the code itself (exported functions, classes, methods, fixtures and
their doc comments), so complex helpers are found even if nobody logged them.
Regenerated on every harvest; never edited by hand.

Line format, one capability per line:
  - pages/LoginPage.ts :: LoginPage.login(user, password) :: Signs in through the login form
"""
import re
from pathlib import Path

MAX_PER_FILE = 40
MAX_PARAMS = 60
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "function", "constructor", "super", "else",
            "new", "await", "typeof", "with", "elif", "try"}
LINE_RE = re.compile(r"^- (.+?) :: (.+?)(?: :: (.*))?$")

TS_PATTERNS = [
    ("fn", re.compile(r"^export\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)")),
    ("fn", re.compile(r"^export\s+const\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?\(([^)]*)\)\s*(?::[^=]+)?=>")),
    ("fn", re.compile(r"^export\s+const\s+(\w+)\s*=\s*(?:async\s*)?(\w+)\s*=>")),
    ("class", re.compile(r"^export\s+(?:default\s+)?(?:abstract\s+)?class\s+(\w+)")),
    ("class", re.compile(r"^class\s+(\w+)")),
]
TS_METHOD = re.compile(r"^\s+(?:public\s+|static\s+|async\s+|readonly\s+)*(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)\s*(?::\s*[^{]+)?\{")
TS_FIXTURE = re.compile(r"^\s+(\w+)\s*:\s*async\s*\(")
PY_DEF = re.compile(r"^def\s+(\w+)\s*\(([^)]*)\)")
PY_CLASS = re.compile(r"^class\s+(\w+)")
PY_METHOD = re.compile(r"^\s+def\s+(\w+)\s*\(\s*self\s*,?\s*([^)]*)\)")
JV_CLASS = re.compile(r"^\s*public\s+(?:abstract\s+|final\s+|static\s+|partial\s+)*class\s+(\w+)")
JV_METHOD = re.compile(r"^\s*public\s+(?:static\s+|async\s+|override\s+|virtual\s+|final\s+|synchronized\s+)*[\w<>\[\],.? ]+\s+(\w+)\s*\(([^)]*)\)")
ROBOT_KW = re.compile(r"^(\S.*\S|\S)\s*$")


def clean_params(p):
    p = re.sub(r"\s+", " ", p.strip())
    p = re.sub(r":\s*[^,=]+", "", p)  # drop TS/Python type hints
    p = re.sub(r"\b(final|String|int|boolean|bool|string|var|double|long)\s+", "", p)
    return (p[:MAX_PARAMS] + "...") if len(p) > MAX_PARAMS else p


def doc_above(lines, i):
    """First meaningful line of the comment block right above line i."""
    j = i - 1
    while j >= 0 and lines[j].strip().startswith("@") and not lines[j].strip().startswith("@param"):
        j -= 1  # skip decorators / annotations
    if j < 0:
        return ""
    s = lines[j].strip()
    if s.endswith("*/"):
        block = []
        while j >= 0:
            block.insert(0, lines[j].strip())
            if lines[j].strip().startswith("/*"):
                break
            j -= 1
        for b in block:
            b = re.sub(r"^/\*\*?|\*/$|^\*", "", b).strip()
            if b and not b.startswith("@"):
                return b
        return ""
    comments = []
    while j >= 0 and re.match(r"^\s*(//+|#)(?!!)", lines[j]):
        comments.insert(0, re.sub(r"^\s*(//+|#)\s?", "", lines[j]).strip())
        j -= 1
    for c in comments:
        c = re.sub(r"</?summary>", "", c).strip()
        if c:
            return c
    return ""


def py_docstring(lines, i):
    for k in range(i + 1, min(i + 4, len(lines))):
        s = lines[k].strip()
        if s.startswith(('"""', "'''")):
            s = s.strip("\"' ")
            if s:
                return s
            return lines[k + 1].strip() if k + 1 < len(lines) else ""
        if s:
            return ""
    return ""


def symbols_in(path, text):
    ext = path.suffix
    lines = text.splitlines()
    out = []
    cls = None
    if ext in (".ts", ".js", ".tsx", ".jsx", ".mjs"):
        in_extend = False
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith((" ", "\t")):
                cls = None
            matched = False
            for kind, rx in TS_PATTERNS:
                m = rx.match(line)
                if m:
                    matched = True
                    if kind == "class":
                        cls = m.group(1)
                        out.append((cls, doc_above(lines, i)))
                    else:
                        out.append((f"{m.group(1)}({clean_params(m.group(2))})", doc_above(lines, i)))
                    break
            if matched:
                in_extend = ".extend" in line
                continue
            if ".extend" in line and ("test" in line or "base" in line):
                in_extend = True
                continue
            if in_extend:
                m = TS_FIXTURE.match(line)
                if m:
                    out.append((f"fixture {m.group(1)}", doc_above(lines, i)))
                continue
            if cls:
                m = TS_METHOD.match(line)
                if m and m.group(1) not in KEYWORDS and not m.group(1).startswith("_"):
                    out.append((f"{cls}.{m.group(1)}({clean_params(m.group(2))})", doc_above(lines, i)))
    elif ext == ".py":
        fixture_next = False
        for i, line in enumerate(lines):
            if line.startswith("@pytest.fixture"):
                fixture_next = True
                continue
            m = PY_CLASS.match(line)
            if m:
                cls = m.group(1)
                out.append((cls, py_docstring(lines, i)))
                continue
            m = PY_DEF.match(line)
            if m:
                cls = None
                if not m.group(1).startswith("_"):
                    label = f"fixture {m.group(1)}" if fixture_next else f"{m.group(1)}({clean_params(m.group(2))})"
                    out.append((label, py_docstring(lines, i)))
                fixture_next = False
                continue
            fixture_next = fixture_next and line.startswith("@")
            m = PY_METHOD.match(line)
            if m and cls and not m.group(1).startswith("_"):
                out.append((f"{cls}.{m.group(1)}({clean_params(m.group(2))})", py_docstring(lines, i)))
    elif ext in (".java", ".cs", ".kt"):
        for i, line in enumerate(lines):
            m = JV_CLASS.match(line)
            if m:
                cls = m.group(1)
                out.append((cls, doc_above(lines, i)))
                continue
            m = JV_METHOD.match(line)
            if m and m.group(1) not in KEYWORDS and m.group(1) != cls:
                out.append((f"{cls + '.' if cls else ''}{m.group(1)}({clean_params(m.group(2))})", doc_above(lines, i)))
    elif ext == ".robot":
        in_kw = False
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("*** keywords"):
                in_kw = True
                continue
            if line.startswith("***"):
                in_kw = False
            if in_kw and line and not line[0].isspace() and not line.startswith("#"):
                doc = ""
                if i + 1 < len(lines) and "[documentation]" in lines[i + 1].lower():
                    doc = re.split(r"\[documentation\]", lines[i + 1], flags=re.I)[1].strip()
                out.append((f"keyword {line.strip()}", doc))
    return out[:MAX_PER_FILE]


def build(repo, files, date):
    repo = Path(repo)
    sections, total, nfiles = [], 0, 0
    for rel in sorted(set(files)):
        p = repo / rel
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        syms = symbols_in(p, text)
        if not syms:
            continue
        nfiles += 1
        sections.append(f"\n## {rel}\n")
        for name, doc in syms:
            doc = doc.replace("::", ":").strip()
            sections.append(f"- {rel} :: {name}" + (f" :: {doc}" if doc else ""))
            total += 1
    head = ["# Capability catalogue", "",
            f"Generated {date} from the code by harvest. {total} capabilities in {nfiles} files.",
            "Don't edit by hand: add doc comments in the code and re-run harvest. Search it with `spider.py match`."]
    return "\n".join(head + sections) + "\n", total


def parse(text):
    rows = []
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if m:
            rows.append({"path": m.group(1), "symbol": m.group(2), "doc": m.group(3) or ""})
    return rows


def words_of(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    return set(re.findall(r"[a-z0-9]+", s.lower()))
