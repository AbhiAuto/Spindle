#!/usr/bin/env python3
"""Harvest an existing test automation repo into a Spindle web.

Static scan only: no code is executed and no code is copied into memory.
It records the stack, layout, reusable assets (as paths), tags, retries,
skipped tests and CI, so the memory isn't empty on day one.

  harvest.py <repo> <web>            dry run, prints what it would add
  harvest.py <repo> <web> --write    adds the strands to the web
  harvest.py <repo> <web> --name "Claims UI automation"

Run again any time; strands already in the web are skipped.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spider  # noqa: E402
import catalogue  # noqa: E402

SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", ".venv", "venv", "__pycache__",
             "bin", "obj", ".idea", ".vscode", "test-results", "playwright-report", "allure-results",
             "reports"}
MEMORY_DIRS = {"spider", "spider-web"}  # skipped at the repo root only
SKIP_PREFIXES = (".github/skills/", ".github/prompts/", ".github/instructions/", ".github/agents/", ".claude/")
# agent eval cases hold deliberately good and bad sample code: never learn from them
SKIP_ANYWHERE = {"evals", "eval-cases", "__snapshots__"}
MAX_FILES = 5000
MAX_LIST = 12

FRAMEWORK_MARKERS = {
    # package.json dependency -> label
    "@playwright/test": "Playwright", "playwright": "Playwright", "cypress": "Cypress",
    "webdriverio": "WebdriverIO", "@wdio/cli": "WebdriverIO", "selenium-webdriver": "Selenium",
    "@cucumber/cucumber": "Cucumber", "jest": "Jest", "mocha": "Mocha", "testcafe": "TestCafe",
    "puppeteer": "Puppeteer", "appium": "Appium", "k6": "k6", "supertest": "Supertest",
    "newman": "Postman/Newman",
}
JAVA_MARKERS = {
    "selenium-java": "Selenium", "testng": "TestNG", "junit-jupiter": "JUnit 5", "junit": "JUnit",
    "cucumber-java": "Cucumber", "rest-assured": "REST Assured", "playwright": "Playwright",
    "appium": "Appium", "serenity": "Serenity", "karate": "Karate", "selenide": "Selenide",
}
PY_MARKERS = {
    "pytest": "pytest", "playwright": "Playwright", "selenium": "Selenium", "robotframework": "Robot Framework",
    "behave": "Behave", "pytest-bdd": "pytest-bdd", "requests": "requests", "appium": "Appium",
    "locust": "Locust",
}
DOTNET_MARKERS = {
    "Microsoft.Playwright": "Playwright", "Selenium.WebDriver": "Selenium", "NUnit": "NUnit",
    "xunit": "xUnit", "SpecFlow": "SpecFlow", "Reqnroll": "Reqnroll", "RestSharp": "RestSharp",
    "MSTest": "MSTest",
}
CONFIG_FILES = ["playwright.config.ts", "playwright.config.js", "cypress.config.ts", "cypress.config.js",
                "wdio.conf.ts", "wdio.conf.js", "pytest.ini", "conftest.py", "testng.xml", "pom.xml",
                "build.gradle", "jest.config.js", "jest.config.ts", "cucumber.js", "behave.ini",
                "karate-config.js", "tsconfig.json", "package.json", "requirements.txt", "pyproject.toml"]
EXT_LANG = {".ts": "TypeScript", ".js": "JavaScript", ".py": "Python", ".java": "Java", ".cs": "C#",
            ".robot": "Robot Framework", ".feature": "Gherkin", ".kt": "Kotlin"}
TEST_NAME_RE = re.compile(r"(\.(spec|test|cy)\.(ts|js|tsx|jsx|mjs|cjs)$|_test\.py$|^test_.*\.py$|Test\.java$|Tests?\.cs$|\.feature$|\.robot$)")
PAGE_RE = re.compile(r"(page|screen)s?$|page[-_]?objects?$", re.I)
PAGE_FILE_RE = re.compile(r"(Page|Screen|_page|-page|\.page)\.(ts|js|py|java|cs|kt)$")
HELPER_DIR_RE = re.compile(r"^(utils?|helpers?|support|lib|common|core|shared|commands)$", re.I)
FIXTURE_DIR_RE = re.compile(r"^fixtures?$", re.I)
DATA_DIR_RE = re.compile(r"^(test[-_]?data|data|testdata|resources|datasets?)$", re.I)
API_DIR_RE = re.compile(r"^(api|apis|clients?|services)$", re.I)
STEP_DIR_RE = re.compile(r"^(steps?|step[-_]?definitions|stepdefs)$", re.I)
TAG_RE = re.compile(r"(?<![\w@])@(smoke|regression|sanity|e2e|critical|p[0-3]|wip|flaky|slow|api|ui)\b", re.I)
SKIP_RE = re.compile(r"\b(test\.fixme|test\.skip|it\.skip|describe\.skip|xit\(|xdescribe\(|@pytest\.mark\.skip|"
                     r"@pytest\.mark\.xfail|@Disabled|@Ignore|enabled\s*=\s*false|\[Ignore|@skip|@wip)")
RETRY_RES = [re.compile(r"retries\s*:\s*(?:process\.env\.CI\s*\?\s*)?(\d+)"),
             re.compile(r"retryAnalyzer"), re.compile(r"--reruns[= ](\d+)"), re.compile(r"\"retries\"\s*:\s*(\d+)")]


def walk(repo):
    files = []
    for p in repo.rglob("*"):
        rel = p.relative_to(repo)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]) or (p.is_dir() and p.name in SKIP_DIRS):
            continue
        if rel.parts and rel.parts[0] in MEMORY_DIRS and (repo / rel.parts[0] / "profile.md").is_file():
            continue
        if any(part in SKIP_ANYWHERE for part in rel.parts[:-1]):
            continue
        if rel.as_posix().startswith(SKIP_PREFIXES):
            continue
        if p.is_file():
            files.append(rel)
            if len(files) >= MAX_FILES:
                break
    return files


def read(path, limit=200_000):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def short_list(items):
    items = sorted(set(str(i).replace("\\", "/") for i in items))
    more = len(items) - MAX_LIST
    return ", ".join(items[:MAX_LIST]) + (f" (+{more} more)" if more > 0 else "")


def scan(repo):
    repo = Path(repo).resolve()
    files = walk(repo)
    names = {f.as_posix() for f in files}
    found = {"repo": repo.name, "frameworks": [], "languages": [], "configs": [], "tests": [], "pages": [],
             "helpers": [], "fixtures": [], "api": [], "steps": [], "data_dirs": set(), "ci": [],
             "tags": Counter(), "skips": [], "retries": [], "features": 0}

    def add_fw(label):
        if label not in found["frameworks"]:
            found["frameworks"].append(label)

    pkg = repo / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(read(pkg))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for d in deps:
                if d in FRAMEWORK_MARKERS:
                    add_fw(FRAMEWORK_MARKERS[d])
        except ValueError:
            pass
    for build in ("pom.xml", "build.gradle", "build.gradle.kts"):
        text = read(repo / build).lower()
        for k, v in JAVA_MARKERS.items():
            if k in text:
                add_fw(v)
    for req in ("requirements.txt", "pyproject.toml", "Pipfile"):
        text = read(repo / req).lower()
        for k, v in PY_MARKERS.items():
            if re.search(rf"(^|[\s\"'\[]){re.escape(k)}([\s=<>~\[\"',]|$)", text, re.M):
                add_fw(v)
    for f in files:
        if f.suffix == ".csproj":
            text = read(repo / f)
            for k, v in DOTNET_MARKERS.items():
                if k.lower() in text.lower():
                    add_fw(v)

    langs = Counter()
    for f in files:
        posix = f.as_posix()
        if f.name in CONFIG_FILES:
            found["configs"].append(posix)
        if posix.startswith(".github/workflows/") or f.name in ("Jenkinsfile", ".gitlab-ci.yml",
                                                                  "azure-pipelines.yml", "bitbucket-pipelines.yml"):
            found["ci"].append(posix)
        if f.suffix in EXT_LANG and f.suffix != ".feature":
            langs[EXT_LANG[f.suffix]] += 1
        if f.suffix == ".feature":
            found["features"] += 1
        parents = [p.lower() for p in f.parts[:-1]]
        if TEST_NAME_RE.search(f.name):
            found["tests"].append(posix)
        if PAGE_FILE_RE.search(f.name) or any(PAGE_RE.search(p) for p in parents):
            if f.suffix in EXT_LANG:
                found["pages"].append(posix)
        elif any(HELPER_DIR_RE.match(p) for p in parents) and f.suffix in EXT_LANG:
            found["helpers"].append(posix)
        if any(FIXTURE_DIR_RE.match(p) for p in parents) and f.suffix in EXT_LANG:
            found["fixtures"].append(posix)
        if any(API_DIR_RE.match(p) for p in parents) and f.suffix in EXT_LANG:
            found["api"].append(posix)
        if any(STEP_DIR_RE.match(p) for p in parents) and f.suffix in EXT_LANG:
            found["steps"].append(posix)
        for i, p in enumerate(f.parts[:-1]):
            if DATA_DIR_RE.match(p):
                found["data_dirs"].add("/".join(f.parts[:i + 1]))
        if f.suffix in EXT_LANG or f.name in CONFIG_FILES:
            text = read(repo / f)
            if TEST_NAME_RE.search(f.name):
                for m in TAG_RE.finditer(text):
                    found["tags"]["@" + m.group(1).lower()] += 1
                for n, line in enumerate(text.splitlines(), start=1):
                    if SKIP_RE.search(line):
                        found["skips"].append(f"{posix}:{n}")
            if f.name in CONFIG_FILES or "conf" in f.name.lower():
                for rx in RETRY_RES:
                    m = rx.search(text)
                    if m:
                        found["retries"].append((posix, m.group(1) if m.groups() else "yes"))
                        break
    found["languages"] = [l for l, _ in langs.most_common(3)]
    found["data_dirs"] = sorted(found["data_dirs"])
    # a test file is never a reusable asset, whatever folder it sits in (tests/api/x.api.spec.ts)
    tests = set(found["tests"])
    for key in ("pages", "helpers", "fixtures", "api", "steps"):
        found[key] = [p for p in found[key] if p not in tests]
    return found


def to_strands(found):
    """Turn scan results into (kind, text) pairs for the framework thread."""
    s = []
    stack = ", ".join(found["frameworks"]) or "not detected"
    lang = ", ".join(found["languages"]) or "unknown"
    s.append(("convention", f"Stack: {stack}. Main language: {lang}"))
    if found["configs"]:
        s.append(("convention", f"Config files: {short_list(found['configs'])}"))
    if found["tests"]:
        dirs = Counter(str(Path(t).parent).replace("\\", "/") for t in found["tests"])
        top = ", ".join(f"{d} ({c})" for d, c in dirs.most_common(5))
        exts = Counter(re.sub(r"^[^.]*", "", Path(t).name) or Path(t).suffix for t in found["tests"])
        naming = ", ".join(f"*{e}" for e, _ in exts.most_common(3))
        s.append(("convention", f"{len(found['tests'])} test files. Main folders: {top}. Naming: {naming}"))
    if found["features"]:
        s.append(("convention", f"BDD: {found['features']} .feature files"))
    if found["pages"]:
        s.append(("asset", f"Page objects ({len(found['pages'])}): {short_list(found['pages'])}"))
    if found["helpers"]:
        s.append(("asset", f"Helpers ({len(found['helpers'])}): {short_list(found['helpers'])}"))
    if found["fixtures"]:
        s.append(("asset", f"Fixtures ({len(found['fixtures'])}): {short_list(found['fixtures'])}"))
    if found["api"]:
        s.append(("asset", f"API clients ({len(found['api'])}): {short_list(found['api'])}"))
    if found["steps"]:
        s.append(("asset", f"Step definitions ({len(found['steps'])}): {short_list(found['steps'])}"))
    if found["data_dirs"]:
        s.append(("data", f"Test data folders: {short_list(found['data_dirs'])}"))
    if found["tags"]:
        tags = ", ".join(f"{t} ({c})" for t, c in found["tags"].most_common(8))
        s.append(("convention", f"Tags in use: {tags}"))
    for path, val in found["retries"][:3]:
        s.append(("decision", f"Retries configured in {path}: {val}"))
    if found["skips"]:
        s.append(("gotcha", f"{len(found['skips'])} skipped, fixme or disabled test(s), check why: {short_list(found['skips'])}"))
    if found["ci"]:
        s.append(("env", f"CI: {short_list(found['ci'])}"))
    return s


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo"); p.add_argument("web")
    p.add_argument("--name", help="display name for the framework thread")
    p.add_argument("--write", action="store_true", help="add strands to the web (default is a dry run)")
    a = p.parse_args(argv)
    repo = Path(a.repo)
    if not repo.is_dir():
        raise SystemExit(f"Not a folder: {repo}")
    found = scan(repo)
    strands = to_strands(found)
    tid = spider.slugify(found["repo"])
    name = a.name or f"{found['repo']} automation framework"
    web = Path(a.web)
    _, role, threads = spider.load_web(web)
    kinds = set(role.get("strand_kinds") or [])
    types = set(role.get("thread_types") or [])
    if types and "framework" not in types:
        raise SystemExit("This web's role has no 'framework' thread type. Use the test-automation-engineer role.")
    existing = spider.find_thread(threads, tid)
    existing_text = existing.path.read_text(encoding="utf-8") if existing else ""
    if existing and not a.name:
        name = existing.meta.get("name", name)
    new = [(k, t) for k, t in strands if f"] {t} src:harvest" not in existing_text and (not kinds or k in kinds)]

    cat_files = found["pages"] + found["helpers"] + found["fixtures"] + found["api"] + found["steps"]
    cat_text, n_caps = catalogue.build(repo, cat_files, spider.today())
    cat_path = web / "catalogue.md"
    old_cat = cat_path.read_text(encoding="utf-8") if cat_path.is_file() else ""
    cat_changed = catalogue.parse(old_cat) != catalogue.parse(cat_text)

    print(f"Harvest of {repo} -> thread '{tid}' ({name})")
    for k, t in strands:
        mark = "+" if (k, t) in new else "="
        print(f"  {mark} [{k}] {t}")
    print(f"  {'+' if cat_changed else '='} catalogue: {n_caps} reusable functions, classes and fixtures")
    if not new and not cat_changed:
        print("Nothing new to add.")
        return 0
    if not a.write:
        print(f"\nDry run. {len(new)} new strand(s){', catalogue changes' if cat_changed else ''}. Add --write to save.")
        return 0
    if cat_changed:
        cat_path.write_text(cat_text, encoding="utf-8")
    if existing is not None and new:
        supersede(existing.path, [t for _, t in new])
    for i, (k, t) in enumerate(new):
        args = ["add", str(web), tid, k, t, "--src", "harvest"]
        if i == 0 and existing is None:
            args += ["--type", "framework", "--name", name]
        with open_quiet():
            spider.main(args)
    if not new:
        with open_quiet():
            spider.write_index(web)
    print(f"\nWrote {len(new)} strand(s) to {web}/threads/framework/{tid}.md"
          + (f" and {n_caps} capabilities to {cat_path}" if cat_changed else ""))
    return 0


def strand_key(text):
    """Lines that describe the same thing share a key, e.g. 'Helpers (1): a' and 'Helpers (3): a, b, c'."""
    head = text.split(":", 1)[0].split(".", 1)[0]
    return re.sub(r"\d+", "#", head).strip().lower()


def supersede(path, new_texts):
    """Mark older harvest lines superseded when a new harvest line describes the same thing."""
    keys = {strand_key(t) for t in new_texts}
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = spider.parse_strand(line)
        if (s and "src:harvest" in s["text"] and "superseded" not in s["flags"]
                and strand_key(s["text"].replace(" src:harvest", "")) in keys):
            line = line.replace(f"[{s['kind']}", f"[{s['kind']} superseded", 1)
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


class open_quiet:
    def __enter__(self):
        import io
        self._old = sys.stdout
        sys.stdout = io.StringIO()

    def __exit__(self, *exc):
        sys.stdout = self._old
        return False


if __name__ == "__main__":
    sys.exit(main())
