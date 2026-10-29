"""Run with: python -m unittest discover tests"""
import contextlib
import datetime as dt
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "spindle" / "scripts"))
import spindle  # noqa: E402

ROLES = ROOT / "skills" / "spindle" / "roles"


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = spindle.main([str(a) for a in args])
    return code, out.getvalue()


class SpindleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.web = Path(self.tmp.name) / "web"
        run("init", self.web, "--role", "qi-practice-head", "--name", "Test User")

    def tearDown(self):
        self.tmp.cleanup()

    # --- roles ---
    def test_every_role_file_is_valid(self):
        for p in ROLES.glob("*.md"):
            with self.subTest(role=p.name):
                code, out = run("check-role", p)
                self.assertEqual(code, 0, out)

    def test_bad_role_is_rejected(self):
        bad = Path(self.tmp.name) / "bad.md"
        bad.write_text("---\ntitle: Bad\nthread_types: [Has Spaces]\n---\n")
        code, out = run("check-role", bad)
        self.assertEqual(code, 1)
        self.assertIn("strand_kinds", out)
        self.assertIn("Never store", out)

    # --- init ---
    def test_init_creates_layout(self):
        for t in ("account", "bid", "person", "offering", "asset", "_archive"):
            self.assertTrue((self.web / "threads" / t).is_dir(), t)
        self.assertTrue((self.web / "role.md").is_file())
        self.assertIn("capture_mode: confirm", (self.web / "profile.md").read_text())

    def test_init_refuses_to_overwrite(self):
        with self.assertRaises(SystemExit):
            run("init", self.web, "--role", "software-engineer")

    def test_unknown_role(self):
        with self.assertRaises(SystemExit):
            run("init", Path(self.tmp.name) / "w2", "--role", "astronaut")

    # --- add ---
    def test_add_creates_thread_and_index(self):
        code, _ = run("add", self.web, "Acme Corp", "insight", "Wants faster releases", "--type", "account")
        self.assertEqual(code, 0)
        f = self.web / "threads" / "account" / "acme-corp.md"
        self.assertTrue(f.is_file())
        self.assertIn("[insight] Wants faster releases", f.read_text())
        self.assertIn("acme-corp: Acme Corp, 1 strand,", (self.web / "index.md").read_text())

    def test_add_finds_thread_by_alias(self):
        run("add", self.web, "acme", "insight", "one", "--type", "account", "--name", "Acme Corp")
        f = self.web / "threads" / "account" / "acme.md"
        f.write_text(f.read_text().replace("aliases: []", "aliases: [ACME Ltd]"))
        run("add", self.web, "acme ltd", "insight", "two")
        self.assertIn("two", f.read_text())
        self.assertEqual(len(list((self.web / "threads" / "account").glob("*.md"))), 1)

    def test_add_rejects_unknown_kind_and_type(self):
        with self.assertRaises(SystemExit):
            run("add", self.web, "acme", "gossip", "x", "--type", "account")
        with self.assertRaises(SystemExit):
            run("add", self.web, "acme", "insight", "x", "--type", "spaceship")

    def test_add_needs_type_for_new_thread(self):
        with self.assertRaises(SystemExit):
            run("add", self.web, "acme", "insight", "x")

    def test_commitment_is_open_with_due(self):
        run("add", self.web, "acme", "commitment", "Send deck", "--type", "account", "--due", "2030-01-01")
        self.assertIn("[commitment open due:2030-01-01] Send deck",
                      (self.web / "threads" / "account" / "acme.md").read_text())

    def test_links_sync_to_frontmatter(self):
        run("add", self.web, "jane", "contact", "Head of QA", "--type", "person")
        run("add", self.web, "acme", "contact", "Met [[jane]]", "--type", "account")
        t = spindle.Thread(self.web / "threads" / "account" / "acme.md")
        self.assertEqual(t.listv("links"), ["jane"])

    # --- check ---
    def test_check_clean_web(self):
        run("add", self.web, "acme", "insight", "ok", "--type", "account")
        code, out = run("check", self.web)
        self.assertEqual(code, 0, out)
        self.assertIn("0 errors", out)

    def test_check_catches_problems(self):
        f = self.web / "threads" / "person" / "bob.md"
        f.write_text("---\nid: robert\ntype: account\nname: Bob\nstatus: gone\n---\n"
                     "- 2026-13-45 [insight] bad date\n"
                     "- 2026-01-01 [gossip] bad kind\n"
                     "- 2026-01-01 [commitment open done] both\n"
                     "- 2026-01-01 broken line\n"
                     "- 2026-01-01 [insight] see [[nobody]]\n")
        code, out = run("check", self.web)
        self.assertEqual(code, 1)
        for needle in ("doesn't match file name", "doesn't match folder", "status 'gone'",
                       "bad date", "kind 'gossip'", "both open and done", "strand doesn't match",
                       "missing thread 'nobody'"):
            self.assertIn(needle, out)

    def test_check_flags_duplicate_names(self):
        run("add", self.web, "acme", "insight", "a", "--type", "account", "--name", "Acme")
        run("add", self.web, "acme-2", "insight", "b", "--type", "account", "--name", "Acme")
        _, out = run("check", self.web)
        self.assertIn("duplicate thread", out)

    def test_check_flags_stale(self):
        run("add", self.web, "acme", "insight", "old", "--type", "account", "--date", "2000-01-01")
        _, out = run("check", self.web)
        self.assertIn("stale after", out)

    # --- find / due / done ---
    def test_find_filters(self):
        run("add", self.web, "acme", "pitch", "Test impact analysis", "--type", "account")
        run("add", self.web, "acme", "insight", "Slow regression")
        _, out = run("find", self.web, "--kind", "pitch")
        self.assertIn("Test impact", out)
        self.assertNotIn("Slow regression", out)
        _, out = run("find", self.web, "regression")
        self.assertIn("Slow regression", out)
        _, out = run("find", self.web, "nothing-matches-this")
        self.assertIn("Nothing found", out)

    def test_find_hides_superseded(self):
        run("add", self.web, "acme", "status", "old status", "--type", "account")
        f = self.web / "threads" / "account" / "acme.md"
        f.write_text(f.read_text().replace("[status]", "[status superseded]"))
        _, out = run("find", self.web, "old status")
        self.assertIn("Nothing found", out)
        _, out = run("find", self.web, "old status", "--all")
        self.assertIn("old status", out)

    def test_due_and_done(self):
        past = (dt.date.today() - dt.timedelta(days=2)).isoformat()
        soon = (dt.date.today() + dt.timedelta(days=3)).isoformat()
        far = (dt.date.today() + dt.timedelta(days=60)).isoformat()
        run("add", self.web, "acme", "commitment", "Late thing", "--type", "account", "--due", past)
        run("add", self.web, "acme", "commitment", "Soon thing", "--due", soon)
        run("add", self.web, "acme", "commitment", "Far thing", "--due", far)
        _, out = run("due", self.web, "--days", "7")
        self.assertIn("OVERDUE", out)
        self.assertIn("Soon thing", out)
        self.assertNotIn("Far thing", out)
        code, _ = run("done", self.web, "acme", "late")
        self.assertEqual(code, 0)
        _, out = run("due", self.web)
        self.assertNotIn("Late thing", out)
        self.assertIn("[commitment done", (self.web / "threads" / "account" / "acme.md").read_text())

    def test_done_ambiguous(self):
        run("add", self.web, "acme", "commitment", "Send deck A", "--type", "account")
        run("add", self.web, "acme", "commitment", "Send deck B")
        code, out = run("done", self.web, "acme", "send deck")
        self.assertEqual(code, 1)
        self.assertIn("More than one match", out)

    def test_example_web_is_valid(self):
        code, out = run("check", ROOT / "examples" / "qi-practice-head-web")
        self.assertIn("0 errors", out)


if __name__ == "__main__":
    unittest.main()
