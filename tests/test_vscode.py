"""Harvest, installer and MCP server tests. Run with: python -m unittest discover tests"""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "spider" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT))
import spider  # noqa: E402
import harvest  # noqa: E402
import install_vscode  # noqa: E402

SAMPLE = ROOT / "examples" / "sample-playwright-repo"


def quiet(fn, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fn([str(a) for a in args])
    return code, out.getvalue()


class HarvestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.web = Path(self.tmp.name) / "web"
        quiet(spider.main, "init", self.web, "--role", "test-automation-engineer")

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_sample(self):
        f = harvest.scan(SAMPLE)
        self.assertIn("Playwright", f["frameworks"])
        self.assertEqual(f["languages"][0], "TypeScript")
        self.assertEqual(len(f["tests"]), 2)
        self.assertIn("pages/LoginPage.ts", f["pages"])
        self.assertIn("utils/dataBuilder.ts", f["helpers"])
        self.assertIn("fixtures/auth.ts", f["fixtures"])
        self.assertEqual(f["tags"]["@regression"], 2)
        self.assertEqual(len(f["skips"]), 1)
        self.assertEqual(f["retries"][0][1], "2")
        self.assertIn(".github/workflows/e2e.yml", f["ci"])
        self.assertFalse(any("spider" in p for p in f["helpers"] + f["tests"]))

    def test_dry_run_writes_nothing(self):
        quiet(harvest.main, SAMPLE, self.web)
        self.assertEqual(list((self.web / "threads" / "framework").glob("*.md")), [])

    def test_write_is_idempotent_and_valid(self):
        quiet(harvest.main, SAMPLE, self.web, "--write")
        f = self.web / "threads" / "framework" / "sample-playwright-repo.md"
        first = f.read_text()
        _, out = quiet(harvest.main, SAMPLE, self.web, "--write")
        self.assertIn("Nothing new", out)
        self.assertEqual(first, f.read_text())
        code, out = quiet(spider.main, "check", self.web)
        self.assertEqual(code, 0, out)

    def test_java_and_python_detection(self):
        j = Path(self.tmp.name) / "java"
        (j / "src/test/java/pages").mkdir(parents=True)
        (j / "pom.xml").write_text("<artifactId>selenium-java</artifactId><artifactId>testng</artifactId>")
        (j / "src/test/java/LoginTest.java").write_text("@Test(enabled = false) public void x(){}")
        (j / "src/test/java/pages/HomePage.java").write_text("class HomePage {}")
        f = harvest.scan(j)
        self.assertEqual(f["frameworks"], ["Selenium", "TestNG"])
        self.assertEqual(len(f["skips"]), 1)
        self.assertIn("src/test/java/pages/HomePage.java", f["pages"])
        py = Path(self.tmp.name) / "py"
        (py / "tests").mkdir(parents=True)
        (py / "requirements.txt").write_text("pytest==8.0\nplaywright\n")
        (py / "tests" / "test_login.py").write_text("@pytest.mark.skip\ndef test_x(): pass\n")
        f = harvest.scan(py)
        self.assertEqual(f["frameworks"], ["pytest", "Playwright"])

    def test_refuses_non_automation_role(self):
        other = Path(self.tmp.name) / "web2"
        quiet(spider.main, "init", other, "--role", "account-manager")
        with self.assertRaises(SystemExit):
            quiet(harvest.main, SAMPLE, other)


class InstallerTest(unittest.TestCase):
    def test_install_and_reinstall(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            shutil.copytree(SAMPLE, repo, ignore=shutil.ignore_patterns("spider"))
            (repo / ".github" / "copilot-instructions.md").write_text("Our own rules.\n")
            (repo / ".vscode").mkdir()
            (repo / ".vscode" / "mcp.json").write_text('{"servers": {"other": {"command": "x"}}}')
            quiet(install_vscode.main, repo, "--python", "python")
            quiet(install_vscode.main, repo)
            gh = repo / ".github"
            self.assertTrue((gh / "skills" / "spider" / "SKILL.md").is_file())
            self.assertTrue((gh / "skills" / "spider-pack-builder" / "SKILL.md").is_file())
            self.assertTrue((gh / "prompts" / "new-pack.prompt.md").is_file())
            self.assertTrue((gh / "instructions" / "spider-tests.instructions.md").is_file())
            self.assertIn("Spindle memory updated", (gh / "pull_request_template.md").read_text())
            text = (gh / "copilot-instructions.md").read_text()
            self.assertTrue(text.startswith("Our own rules."))
            self.assertEqual(text.count("spider:start"), 1)
            mcp = json.loads((repo / ".vscode" / "mcp.json").read_text())
            self.assertIn("other", mcp["servers"])
            self.assertIn("spider_mcp.py", mcp["servers"]["spider"]["args"][0])
            self.assertTrue((repo / "spider" / "profile.md").is_file())

    def test_old_spider_web_is_moved(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            shutil.copytree(SAMPLE, repo, ignore=shutil.ignore_patterns("spider"))
            subprocess.run(["git", "init", "-q"], cwd=repo)
            quiet(spider.main, "init", repo / "spider-web", "--role", "test-automation-engineer")
            quiet(spider.main, "add", repo / "spider-web", "x", "insight", "keep me", "--type", "app")
            subprocess.run(["git", "add", "-A"], cwd=repo)
            (repo / ".gitattributes").write_text("spider-web/threads/**/*.md merge=union\n")
            _, out = quiet(install_vscode.main, repo, "--no-hook")
            self.assertIn("Moved your memory", out)
            self.assertFalse((repo / "spider-web").exists())
            self.assertIn("keep me", (repo / "spider" / "threads" / "app" / "x.md").read_text())
            self.assertIn("spider/threads", (repo / ".gitattributes").read_text())
            mcp = json.loads((repo / ".vscode" / "mcp.json").read_text())
            self.assertTrue(mcp["servers"]["spider"]["env"]["SPIDER_WEB"].endswith("/spider"))

    def test_refuses_clashing_folders(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "spider").mkdir()
            (repo / "spider" / "crawler.py").write_text("x = 1\n")
            with self.assertRaises(SystemExit):
                quiet(install_vscode.main, repo)
            self.assertFalse((repo / ".github").exists())
            quiet(spider.main, "init", repo / "spider-web", "--role", "test-automation-engineer")
            with self.assertRaises(SystemExit):
                quiet(install_vscode.main, repo)

    def test_harvest_skips_memory_only_at_root(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            quiet(spider.main, "init", repo / "spider", "--role", "test-automation-engineer")
            (repo / "src" / "spider" / "pages").mkdir(parents=True)
            (repo / "src" / "spider" / "pages" / "HomePage.ts").write_text("export class HomePage {}\n")
            f = harvest.scan(repo)
            self.assertIn("src/spider/pages/HomePage.ts", f["pages"])
            self.assertFalse(any(p.startswith("spider/") for p in sum([f[k] for k in ("pages", "helpers", "tests")], [])))

    def test_prompt_files_have_frontmatter(self):
        for p in (ROOT / "vscode" / "prompts").glob("*.prompt.md"):
            meta, body = spider.split_frontmatter(p.read_text())
            self.assertIn("description", meta, p.name)
            self.assertEqual(meta.get("agent"), "agent", p.name)
            self.assertIn("spider", body.lower(), p.name)

    def test_skill_frontmatter(self):
        for name in ("spider", "spider-pack-builder"):
            meta, _ = spider.split_frontmatter((ROOT / "skills" / name / "SKILL.md").read_text())
            self.assertEqual(meta.get("name"), name)
            self.assertTrue(meta.get("description"))


class McpTest(unittest.TestCase):
    def test_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            web = Path(d) / "web"
            quiet(spider.main, "init", web, "--role", "test-automation-engineer")
            msgs = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "spider_harvest",
                 "arguments": {"repo": str(SAMPLE), "write": True}}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "spider_find",
                 "arguments": {"kind": "asset"}}},
                {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "spider_add",
                 "arguments": {"thread": "x", "kind": "bogus", "text": "y"}}},
                {"jsonrpc": "2.0", "id": 6, "method": "nope"},
            ]
            stdin = "\n".join(json.dumps(m) for m in msgs) + "\n"
            r = subprocess.run([sys.executable, str(SCRIPTS / "spider_mcp.py")], input=stdin, text=True,
                               capture_output=True, env={"SPIDER_WEB": str(web), "PATH": ""}, timeout=60)
            out = [json.loads(l) for l in r.stdout.splitlines()]
            self.assertEqual([m["id"] for m in out], [1, 2, 3, 4, 5, 6])
            self.assertEqual(out[0]["result"]["serverInfo"]["name"], "spider")
            self.assertEqual(len(out[1]["result"]["tools"]), 15)
            self.assertFalse(out[2]["result"]["isError"])
            self.assertIn("pages/LoginPage.ts", out[3]["result"]["content"][0]["text"])
            self.assertTrue(out[4]["result"]["isError"])
            self.assertEqual(out[5]["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()


class PromptPortabilityTest(unittest.TestCase):
    def test_placeholders_are_plain(self):
        """Some repos sync Copilot prompts to Claude Code and only understand ${input:name}."""
        import re
        for p in (ROOT / "vscode" / "prompts").glob("*.prompt.md"):
            self.assertIsNone(re.search(r"\$\{input:[A-Za-z0-9_]+:", p.read_text()), p.name)


class HarvestSkipTest(unittest.TestCase):
    def test_skips_evals_specs_in_api_and_claude_folder(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            for f, text in {
                "src/api/ItemsApi.ts": "export class ItemsApi {}\n",
                "tests/api/items.api.spec.ts": "test('x', async () => {});\n",
                "evals/cases/a/candidates/bad/src/pages/BadPage.ts": "export class BadPage {}\n",
                ".claude/skills/spider/scripts/spider.py": "def x(): pass\n",
            }.items():
                (repo / f).parent.mkdir(parents=True, exist_ok=True)
                (repo / f).write_text(text)
            f = harvest.scan(repo)
            self.assertEqual(f["api"], ["src/api/ItemsApi.ts"])
            self.assertEqual(f["tests"], ["tests/api/items.api.spec.ts"])
            self.assertEqual(f["pages"], [])
            self.assertNotIn("Python", f["languages"])
