"""Catalogue, triggers, match and hook tests. Run with: python -m unittest discover tests"""
import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "spindle" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import catalogue  # noqa: E402
import harvest  # noqa: E402
import spindle  # noqa: E402
import spindle_hook  # noqa: E402

SAMPLE = ROOT / "examples" / "sample-playwright-repo"


def quiet(fn, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fn([str(a) for a in args])
    return code, out.getvalue()


class SymbolTest(unittest.TestCase):
    def test_typescript(self):
        src = ("import x from 'y';\n\n/** Logs in with OTP. */\nexport async function loginWithOtp(page: Page, user: string) {\n}\n"
               "/** Login screen. */\nexport class LoginPage {\n  constructor(private page: Page) {}\n\n"
               "  /** Fills the form. */\n  async login(user: string, password: string) {\n    if (x) {}\n  }\n\n"
               "  private _hidden() {}\n}\n"
               "export const buildClaim = (overrides = {}) => ({});\n"
               "export const test = base.extend<{ loggedIn: Page }>({\n  /** Signed-in page. */\n  loggedIn: async ({ page }, use) => {\n  },\n});\n")
        syms = dict(catalogue.symbols_in(Path("a.ts"), src))
        self.assertEqual(syms["loginWithOtp(page, user)"], "Logs in with OTP.")
        self.assertEqual(syms["LoginPage"], "Login screen.")
        self.assertEqual(syms["LoginPage.login(user, password)"], "Fills the form.")
        self.assertIn("buildClaim(overrides = {})", syms)
        self.assertEqual(syms["fixture loggedIn"], "Signed-in page.")
        self.assertFalse(any("constructor" in k or "_hidden" in k or k.startswith("if") for k in syms))

    def test_python(self):
        src = ('import pytest\n\n@pytest.fixture\ndef admin_session():\n    """Admin signed in."""\n\n'
               'def get_otp(inbox: str):\n    """Reads the OTP."""\n\nclass CartPage:\n    """Cart."""\n'
               '    def add_item(self, sku: str):\n        """Adds one item."""\n    def _private(self):\n        pass\n')
        syms = dict(catalogue.symbols_in(Path("a.py"), src))
        self.assertEqual(syms["fixture admin_session"], "Admin signed in.")
        self.assertEqual(syms["get_otp(inbox)"], "Reads the OTP.")
        self.assertEqual(syms["CartPage.add_item(sku)"], "Adds one item.")
        self.assertNotIn("CartPage._private()", syms)

    def test_java_and_csharp(self):
        src = ("public class LoginPage {\n    /** Signs in. */\n    public void login(String user, String pass) {\n    }\n}\n")
        syms = dict(catalogue.symbols_in(Path("LoginPage.java"), src))
        self.assertEqual(syms["LoginPage.login(user, pass)"], "Signs in.")
        cs = "public class Cart\n{\n    /// <summary>Adds an item.</summary>\n    public async Task AddItem(string sku)\n    {\n    }\n}\n"
        syms = dict(catalogue.symbols_in(Path("Cart.cs"), cs))
        self.assertEqual(syms["Cart.AddItem(sku)"], "Adds an item.")

    def test_robot(self):
        src = "*** Keywords ***\nLogin With OTP\n    [Documentation]    Signs in including the OTP\n    Log    x\n"
        syms = dict(catalogue.symbols_in(Path("auth.robot"), src))
        self.assertEqual(syms["keyword Login With OTP"], "Signs in including the OTP")

    def test_parse_roundtrip(self):
        text, n = catalogue.build(SAMPLE, ["pages/ClaimsPage.ts", "fixtures/auth.ts"], "2026-01-01")
        rows = catalogue.parse(text)
        self.assertEqual(len(rows), n)
        self.assertIn("ClaimsPage.uploadEvidence(filePath)", [r["symbol"] for r in rows])


class MatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.web = Path(self.tmp.name) / "web"
        shutil.copytree(SAMPLE / "spindle", self.web)

    def tearDown(self):
        self.tmp.cleanup()

    def test_triggers_and_catalogue(self):
        _, out = quiet(spindle.main, "match", self.web, "Withdraw a claim for a user with two-step login and attach a document")
        self.assertIn("otp-login", out)
        self.assertIn("file-upload", out)
        code_part = out.split("Code you can reuse:")[1]
        self.assertIn("loginWithOtp", code_part)
        self.assertIn("uploadEvidence", code_part)

    def test_no_false_trigger_inside_words(self):
        _, out = quiet(spindle.main, "match", self.web, "bottle of water")
        self.assertNotIn("otp-login", out.split("Code you can reuse:")[0])

    def test_use_when_added_and_validated(self):
        quiet(spindle.main, "add", self.web, "iframe-handling", "pattern", "Use frameLocator", "--type", "pattern",
              "--use-when", "iframe, embedded frame")
        quiet(spindle.main, "add", self.web, "iframe-handling", "pattern", "Second line", "--use-when", "IFRAME, frame")
        t = spindle.Thread(self.web / "threads" / "pattern" / "iframe-handling.md")
        self.assertEqual(t.listv("use_when"), ["iframe", "embedded frame", "frame"])
        self.assertIn("[use when: iframe, embedded frame, frame]", (self.web / "index.md").read_text())
        code, out = quiet(spindle.main, "check", self.web)
        self.assertEqual(code, 0, out)

    def test_index_mentions_catalogue(self):
        quiet(spindle.main, "index", self.web)
        self.assertIn("Capability catalogue:", (self.web / "index.md").read_text())


class HarvestCatalogueTest(unittest.TestCase):
    def test_catalogue_written_and_stale_lines_superseded(self):
        with tempfile.TemporaryDirectory() as d:
            repo, web = Path(d) / "repo", Path(d) / "web"
            shutil.copytree(SAMPLE, repo, ignore=shutil.ignore_patterns("spindle"))
            quiet(spindle.main, "init", web, "--role", "test-automation-engineer")
            quiet(harvest.main, repo, web, "--write")
            self.assertTrue((web / "catalogue.md").is_file())
            (repo / "utils" / "dates.ts").write_text("/** Today as ISO. */\nexport function isoToday() {}\n")
            _, out = quiet(harvest.main, repo, web, "--write")
            self.assertIn("capabilities", out)
            self.assertIn("isoToday", (web / "catalogue.md").read_text())
            thread = (web / "threads" / "framework" / "repo.md").read_text()
            self.assertIn("[asset superseded] Helpers (2)", thread)
            self.assertIn("[asset] Helpers (3)", thread)
            code, out = quiet(spindle.main, "check", web)
            self.assertEqual(code, 0, out)
            _, out = quiet(harvest.main, repo, web, "--write")
            self.assertIn("Nothing new", out)


class HookTest(unittest.TestCase):
    def test_reminder_logic(self):
        self.assertIsNotNone(spindle_hook.reminder(["fixtures/auth.ts"]))
        self.assertIsNotNone(spindle_hook.reminder(["src/test/java/pages/HomePage.java"]))
        self.assertIsNone(spindle_hook.reminder(["fixtures/auth.ts", "spindle/threads/app/x.md"]))
        self.assertIsNone(spindle_hook.reminder(["tests/claims/new-claim.spec.ts"]))
        self.assertIsNone(spindle_hook.reminder(["README.md", "package.json"]))

    def test_hook_never_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True)
            run("git", "init", "-q")
            (repo / ".github" / "skills" / "spindle" / "scripts").mkdir(parents=True)
            shutil.copy(SCRIPTS / "spindle_hook.py", repo / ".github" / "skills" / "spindle" / "scripts")
            self.assertIn("added", run(sys.executable, ".github/skills/spindle/scripts/spindle_hook.py", "--install").stdout)
            self.assertIn("already", run(sys.executable, ".github/skills/spindle/scripts/spindle_hook.py", "--install").stdout)
            (repo / "pages").mkdir()
            (repo / "pages" / "Cart.ts").write_text("export class Cart {}\n")
            run("git", "add", "-A")
            r = run("git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "x")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Spindle: you changed reusable test code", r.stderr)


if __name__ == "__main__":
    unittest.main()
