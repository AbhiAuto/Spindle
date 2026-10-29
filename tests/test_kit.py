"""Memory kit export/import tests. Run with: python -m unittest discover tests"""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "spider" / "scripts"))
import spider  # noqa: E402

SAMPLE_WEB = ROOT / "examples" / "sample-playwright-repo" / "spider"


def quiet(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = spider.main([str(a) for a in args])
    return code, out.getvalue()


class KitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.src = self.d / "src" / "spider"
        shutil.copytree(SAMPLE_WEB, self.src)
        quiet("add", self.src, "otp-login", "gotcha", "Stub lags at https://mail.acme-internal.com, ask ops@acme.com or 10.1.2.3",
              "--src", "JIRA ACME-42")
        quiet("add", self.src, "otp-login", "commitment", "Raise ticket with Acme ops")
        self.dst = self.d / "dst" / "spider"
        quiet("init", self.dst, "--role", "test-automation-engineer")

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, *extra):
        kit = self.d / "kit.zip"
        code, out = quiet("export", self.src, kit, "--name", "pw-kit", "--redact", "Acme", *extra)
        return kit, out

    def kit_text(self, kit):
        with zipfile.ZipFile(kit) as z:
            return {n: z.read(n).decode() for n in z.namelist()}

    def test_export_scrubs_and_selects(self):
        kit, _ = self.export()
        files = self.kit_text(kit)
        self.assertIn("kit.md", files)
        self.assertIn("threads/framework/pw-kit-framework.md", files)
        self.assertIn("threads/pattern/otp-login.md", files)
        self.assertFalse(any("/app/" in n or "/pack/" in n for n in files))
        blob = "\n".join(files.values())
        for leak in ("acme-internal", "ops@acme.com", "10.1.2.3", "ACME-42", "Raise ticket", "PR 214",
                     "Claims portal", "claims-portal", "sample-playwright-repo", "Demo team"):
            self.assertNotIn(leak, blob, leak)
        self.assertIn("[url removed]", blob)
        self.assertIn("[client]", blob)
        self.assertNotIn("skipped, fixme", blob)  # harvest inventory stays behind

    def test_dry_run_writes_nothing(self):
        kit = self.d / "kit.zip"
        _, out = quiet("export", self.src, kit, "--dry-run")
        self.assertFalse(kit.exists())
        self.assertIn("Preview of", out)

    def test_folder_kit_and_threads_filter(self):
        out = self.d / "kitdir"
        quiet("export", self.src, out, "--threads", "otp-login")
        self.assertTrue((out / "kit.md").is_file())
        self.assertEqual([p.name for p in (out / "threads").rglob("*.md")], ["otp-login.md"])
        with self.assertRaises(SystemExit):
            quiet("export", self.src, out)  # won't overwrite a non-empty folder

    def test_import_new_then_idempotent(self):
        kit, _ = self.export()
        quiet("import", self.dst, kit)
        t = spider.Thread(self.dst / "threads" / "pattern" / "otp-login.md")
        self.assertIn("pw-kit", t.listv("imported_from"))
        self.assertTrue(all("src:kit-pw-kit" in s["text"] for s in t.strands))
        self.assertIn("otp", t.listv("use_when"))
        _, out = quiet("import", self.dst, kit)
        self.assertIn("Nothing new", out)
        code, out = quiet("check", self.dst)
        self.assertEqual(code, 0, out)
        _, out = quiet("match", self.dst, "two-step login")
        self.assertIn("otp-login", out)

    def test_import_merges_into_existing_thread(self):
        quiet("add", self.dst, "otp-login", "pattern", "Our own OTP note", "--type", "pattern", "--use-when", "otp, sms code")
        kit, _ = self.export()
        quiet("import", self.dst, kit)
        t = spider.Thread(self.dst / "threads" / "pattern" / "otp-login.md")
        self.assertIn("Our own OTP note", t.path.read_text())
        self.assertIn("loginWithOtp", t.path.read_text())
        self.assertEqual(t.listv("use_when")[:2], ["otp", "sms code"])
        self.assertIn("two-step", t.listv("use_when"))

    def test_import_dry_run_and_role_mismatch(self):
        kit, _ = self.export()
        _, out = quiet("import", self.dst, kit, "--dry-run")
        self.assertIn("Dry run", out)
        self.assertFalse((self.dst / "threads" / "pattern" / "otp-login.md").exists())
        other = self.d / "sales" / "spider"
        quiet("init", other, "--role", "account-manager")
        _, out = quiet("import", other, kit)
        self.assertIn("skipped", out)
        self.assertEqual(list((other / "threads").rglob("*.md")), [])

    def test_import_ignores_unsafe_zip_entries(self):
        bad = self.d / "bad.zip"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("kit.md", "---\nkit: bad\n---\n")
            z.writestr("../../evil.md", "x")
            z.writestr("threads/pattern/../../../evil2.md", "x")
            z.writestr("threads/pattern/ok.md", "---\nid: ok\ntype: pattern\nname: OK\n---\n- 2026-01-01 [pattern] fine\n")
        quiet("import", self.dst, bad)
        self.assertFalse((self.d / "evil.md").exists())
        self.assertFalse(any(p.name.startswith("evil") for p in self.d.rglob("*")))
        self.assertTrue((self.dst / "threads" / "pattern" / "ok.md").is_file())

    def test_not_a_kit(self):
        with self.assertRaises(SystemExit):
            quiet("import", self.dst, self.d)


if __name__ == "__main__":
    unittest.main()
