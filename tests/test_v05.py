"""Version 0.5: safety, shortcuts, error signatures, ranking, governance, efficacy, stamp, evals, CI, kits."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "spindle" / "scripts"))
import redact  # noqa: E402
import shortcuts  # noqa: E402
import spindle  # noqa: E402

SAMPLE_WEB = ROOT / "examples" / "sample-playwright-repo" / "spindle"


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = spindle.main([str(a) for a in args])
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            out.write(str(e.code))
    return code, out.getvalue()


class RedactTest(unittest.TestCase):
    CASES = {
        "password=Hunter2xyz": "Hunter2xyz",
        "token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB here": "ghp_",
        "Authorization: Bearer abcdefghijklmnop1234": "abcdefghijklmnop1234",
        "AKIAABCDEFGHIJKLMNOP": "AKIA",
        "Server=x;User ID=sa;Password=P@ssw0rd;": "P@ssw0rd",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4": "SflKx",
        "mail ops@acme.com": "ops@acme.com",
        "db at 10.2.3.4 and api.acme.internal": "10.2.3.4",
        "https://user:pw@git.acme.com/repo": "user:pw",
        "OTP is 123456": "123456",
    }

    def test_removes_known_shapes(self):
        for text, secret in self.CASES.items():
            with self.subTest(text=text):
                clean, labels = redact.redact(text)
                self.assertNotIn(secret, clean)
                self.assertTrue(labels)

    def test_leaves_ordinary_text(self):
        for text in ("see vault path secret/qa/app", "loginWithOtp() in fixtures/auth.ts",
                     "commit 3f2a9c1e5b7d4e8a9c217d4e5f6a8b90aabbccdd", "retries: 2 in CI"):
            with self.subTest(text=text):
                self.assertEqual(redact.redact(text), (text, []))

    def test_keep_urls_option(self):
        self.assertIn("https://docs.example.com", redact.redact("see https://docs.example.com", keep_urls=True)[0])


class ShortcutTest(unittest.TestCase):
    def test_flags_shortcuts(self):
        for text in ("Fix: add waitForTimeout(5000)", "Increased the timeout to 60s", "used force: true on the click",
                     "removed the assertion on the toast", "waited 5 seconds before clicking",
                     "retries: 4 in config", "wrapped it in try/catch and ignored the error",
                     "Upload hangs with [email removed]. Fix: add waitForTimeout(8000)"):
            with self.subTest(text=text):
                self.assertTrue(shortcuts.find(text))

    def test_ignores_rejections_and_causes(self):
        for text in ("wait for the scan-complete event, not a fixed timeout",
                     "Fix: replaced waitForTimeout with waitForResponse",
                     "Cause: a sleep in the helper. Fix: wait for the response instead",
                     "never remove the assertion", "use getByRole; avoid networkidle",
                     "Wait for the response, then assert the status",
                     "Proper fix: wait for the scan text; the waitForTimeout was removed"):
            with self.subTest(text=text):
                self.assertEqual(shortcuts.find(text), [])


class WebCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.web = Path(self.tmp.name) / "spindle"
        shutil.copytree(SAMPLE_WEB, self.web)

    def tearDown(self):
        self.tmp.cleanup()

    def thread_text(self, tid, folder="app"):
        return (self.web / "threads" / folder / f"{tid}.md").read_text()


class AddTest(WebCase):
    def test_secrets_removed_on_write(self):
        code, out = run("add", self.web, "claims-portal", "env", "UAT login qa@acme.com password=Secret123")
        self.assertEqual(code, 0)
        text = self.thread_text("claims-portal")
        self.assertNotIn("Secret123", text)
        self.assertNotIn("qa@acme.com", text)
        self.assertIn("Removed what looked like", out)

    def test_shortcut_stored_as_avoid(self):
        _, out = run("add", self.web, "claims-portal", "gotcha", "Upload flaky. Fix: add waitForTimeout(5000)")
        self.assertIn("Stored as 'avoid'", out)
        self.assertIn("[gotcha avoid]", self.thread_text("claims-portal"))
        run("add", self.web, "claims-portal", "decision", "We pause 2 seconds for the vendor iframe",
            "--not-shortcut")
        self.assertIn("[decision] We pause", self.thread_text("claims-portal"))

    def test_error_and_by(self):
        run("add", self.web, "claims-portal", "gotcha", "Upload stalls. Fix: wait for scan-complete",
            "--error", 'locator.setInputFiles: Timeout 30000ms exceeded "x"', "--by", "Ravi K")
        line = self.thread_text("claims-portal").strip().splitlines()[-1]
        self.assertIn("by:ravi-k", line)
        self.assertIn("error:\"locator.setInputFiles: Timeout 30000ms exceeded 'x'\"", line)
        code, out = run("check", self.web)
        self.assertEqual(code, 0, out)


class MatchTest(WebCase):
    def test_known_error_found_with_different_numbers(self):
        run("add", self.web, "claims-portal", "gotcha", "Upload stalls. Fix: wait for scan-complete",
            "--error", "locator.setInputFiles: Timeout 30000ms exceeded")
        _, out = run("match", self.web, "Error: locator.setInputFiles: Timeout 45000ms exceeded.")
        self.assertTrue(out.startswith("Known errors:"))
        self.assertIn("wait for scan-complete", out.split("Memory that applies:")[0])

    def test_avoid_shown_separately_never_as_guidance(self):
        run("add", self.web, "claims-portal", "gotcha", "Upload flaky. Fix: add waitForTimeout(5000)")
        _, out = run("match", self.web, "upload evidence in claims portal")
        memory, rest = out.split("Memory that applies:")[1].split("Avoid", 1)
        self.assertNotIn("add waitForTimeout(5000)", memory)
        self.assertIn("add waitForTimeout(5000)", rest.split("Code you can reuse:")[0])

    def test_reasons_and_ranking(self):
        _, out = run("match", self.web, "user with two-step login")
        first = out.split("Memory that applies:")[1].strip().splitlines()[0]
        self.assertIn("otp-login", first)
        self.assertIn("use when 'two-step'", first)
        res = spindle.compute_match(self.web, "user with two-step login")
        self.assertEqual(res["memory"][0][0].id, "otp-login")
        self.assertIn("loginWithOtp", " ".join(r["symbol"] for r, _, _ in res["code"][:3]))


class GovernanceTest(WebCase):
    def setUp(self):
        super().setUp()
        self.gweb = Path(self.tmp.name) / "gov"
        run("init", self.gweb, "--role", "test-automation-engineer", "--governed")
        run("add", self.gweb, "otp-login", "pattern", "Use loginWithOtp() in fixtures/auth.ts", "--type", "pattern",
            "--use-when", "otp, two-step", "--by", "Ravi")

    def test_candidate_then_approve_with_evidence(self):
        t = spindle.Thread(self.gweb / "threads" / "pattern" / "otp-login.md")
        self.assertEqual(t.meta["review"], "candidate")
        code, out = run("approve", self.gweb, "otp-login", "--by", "Abhi")
        self.assertNotEqual(code, 0)
        self.assertIn("Not enough evidence", out)
        run("add", self.gweb, "otp-login", "pattern", "Mail stub lags; see utils/mailStub.ts", "--by", "Meera")
        run("add", self.gweb, "otp-login", "gotcha", "Service accounts have no OTP", "--by", "Ravi")
        _, out = run("candidates", self.gweb)
        self.assertIn("READY", out)
        code, out = run("approve", self.gweb, "otp-login", "--by", "Abhi")
        self.assertEqual(code, 0, out)
        t = spindle.Thread(self.gweb / "threads" / "pattern" / "otp-login.md")
        self.assertEqual((t.meta["review"], t.meta["approved_by"]), ("approved", "Abhi"))

    def test_override_and_retire(self):
        code, _ = run("approve", self.gweb, "otp-login", "--by", "Abhi", "--override", "agreed in the guild call")
        self.assertEqual(code, 0)
        run("retire", self.gweb, "otp-login", "--by", "Abhi", "--why", "SSO replaced OTP")
        _, out = run("match", self.gweb, "two-step login")
        self.assertNotIn("otp-login", out.split("Code you can reuse:")[0])

    def test_candidate_label_and_governed_export(self):
        _, out = run("match", self.gweb, "two-step login")
        self.assertIn("(candidate)", out)
        code, out = run("export", self.gweb, Path(self.tmp.name) / "k.zip", "--dry-run")
        self.assertNotEqual(code, 0)  # nothing approved to export
        _, out = run("export", self.gweb, Path(self.tmp.name) / "k.zip", "--dry-run", "--include-candidates")
        self.assertIn("otp-login", out)

    def test_feedback_efficacy_prune(self):
        run("feedback", self.gweb, "otp-login", "--used", "--by", "Ravi")
        code, out = run("feedback", self.gweb, "otp-login", "--wrong")
        self.assertNotEqual(code, 0)  # wrong needs a reason
        run("feedback", self.gweb, "otp-login", "--wrong", "--why", "service account has no OTP")
        run("feedback", self.gweb, "otp-login", "--wrong", "--why", "SSO user")
        _, out = run("efficacy", self.gweb, "--json")
        row = json.loads(out)[0]
        self.assertEqual((row["status"], row["used"], row["wrong"]), ("disputed", 1, 2))
        _, out = run("prune", self.gweb)
        self.assertIn("disputed", out)
        self.assertIn("otp-login", out)

    def test_stamp_changes_with_memory(self):
        _, a = run("stamp", self.gweb)
        _, b = run("stamp", self.gweb)
        self.assertEqual(a, b)
        run("add", self.gweb, "otp-login", "pattern", "another line")
        _, c = run("stamp", self.gweb)
        self.assertNotEqual(a.split()[0], c.split()[0])


class ScanEvalCiTest(WebCase):
    def test_scan_and_fix(self):
        f = self.web / "threads" / "app" / "claims-portal.md"
        f.write_text(f.read_text() + "- 2026-10-01 [env] token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB\n")
        code, out = run("scan", self.web)
        self.assertEqual(code, 1)
        self.assertIn("GitHub token", out)
        run("scan", self.web, "--fix")
        self.assertNotIn("ghp_", f.read_text())
        self.assertEqual(run("scan", self.web)[0], 0)

    def test_eval_and_baseline(self):
        cases = Path(self.tmp.name) / "cases.json"
        cases.write_text(json.dumps([{"id": "otp", "request": "two-step login", "expect": ["otp-login", "loginWithOtp"]},
                                     {"id": "none", "request": "bottle of water", "forbid": ["otp-login"]}]))
        base = Path(self.tmp.name) / "base.json"
        code, out = run("eval", self.web, cases, "--write-baseline", base)
        self.assertEqual(code, 0, out)
        self.assertIn("2/2 passed", out)
        f = self.web / "threads" / "pattern" / "otp-login.md"
        f.write_text(f.read_text().replace("use_when: [", "use_when_old: ["))  # break the trigger
        f.write_text(f.read_text().replace("name: OTP login", "name: Code by mail"))
        code, out = run("eval", self.web, cases, "--baseline", base)
        self.assertEqual(code, 1, out)
        self.assertIn("Worse than baseline: otp", out)

    def test_ci(self):
        (self.web / "evals.json").write_text(json.dumps([{"id": "otp", "request": "two-step login", "expect": ["otp-login"]}]))
        code, out = run("ci", self.web)
        self.assertEqual(code, 0, out)
        self.assertIn("evals: 1/1 passed", out)
        f = self.web / "threads" / "app" / "claims-portal.md"
        f.write_text(f.read_text() + "- 2026-10-01 [env] password=Hunter2xyz\n")
        code, out = run("ci", self.web)
        self.assertEqual(code, 1)
        self.assertIn("FAILED: scan", out)


class KitHardeningTest(WebCase):
    def setUp(self):
        super().setUp()
        self.dst = Path(self.tmp.name) / "dst"
        run("init", self.dst, "--role", "test-automation-engineer")

    def zip_kit(self, files):
        kit = Path(self.tmp.name) / "k.zip"
        with zipfile.ZipFile(kit, "w") as z:
            z.writestr("kit.md", "---\nkit: evil\n---\n")
            for n, data in files.items():
                z.writestr(n, data)
        return kit

    def test_untrusted_content_is_cleaned(self):
        kit = self.zip_kit({"threads/pattern/p.md":
                            "---\nid: p\ntype: pattern\nname: P <script>alert(1)</script>\nstatus: paused\n"
                            "evil_key: x\nuse_when: [otp]\n---\n"
                            "- 2026-01-01 [pattern] token ghp_abcdefghijklmnopqrstuvwxyz0123456789AB\n"
                            "- 2026-01-01 [pattern] Fix: add waitForTimeout(9000)\n"
                            "- 2026-01-01 [pattern] " + "x" * 900 + "\n"})
        run("import", self.dst, kit)
        text = (self.dst / "threads" / "pattern" / "p.md").read_text()
        self.assertNotIn("ghp_", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("evil_key", text)
        self.assertIn("status: active", text)
        self.assertIn("[pattern avoid] Fix: add waitForTimeout", text)
        self.assertNotIn("x" * 900, text)

    def test_size_limits_and_bad_encoding(self):
        kit = self.zip_kit({"threads/pattern/big.md": "a" * (300 * 1024),
                            "threads/pattern/bin.md": b"\xff\xfe\x00bad"})
        _, out = run("import", self.dst, kit)
        self.assertIn("too large", out)
        self.assertIn("not UTF-8", out)
        self.assertFalse((self.dst / "threads" / "pattern" / "big.md").exists())

    def test_export_drops_people_and_redacts(self):
        run("add", self.web, "otp-login", "pattern", "Ask Ravi; stub at mail.acme.internal", "--by", "Ravi K")
        kit = Path(self.tmp.name) / "out.zip"
        run("export", self.web, kit, "--name", "k")
        with zipfile.ZipFile(kit) as z:
            blob = "\n".join(z.read(n).decode() for n in z.namelist())
        self.assertNotIn("by:ravi-k", blob)
        self.assertNotIn("acme.internal", blob)

    def test_governed_import_resets_to_candidate(self):
        gov = Path(self.tmp.name) / "gov"
        run("init", gov, "--role", "test-automation-engineer", "--governed")
        kit = self.zip_kit({"threads/pattern/p.md": "---\nid: p\ntype: pattern\nname: P\nreview: approved\n---\n"
                                                    "- 2026-01-01 [pattern] use the stub\n"})
        run("import", gov, kit)
        t = spindle.Thread(gov / "threads" / "pattern" / "p.md")
        self.assertEqual((t.meta["review"], t.meta["kit_review"]), ("candidate", "approved"))


if __name__ == "__main__":
    unittest.main()
