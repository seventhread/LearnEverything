"""Black-box integration tests for the LearnEverything v2 Vault CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "skills/learn-everything/scripts/learn-everything"


class VaultCliTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.temp = Path(self._temporary.name).resolve()
        self.vault = self.temp / "vault"
        self.env = os.environ.copy()
        test_home = self.temp / "home"
        self.env["HOME"] = str(test_home)
        if sys.platform == "darwin":
            self.config = test_home / "Library/Application Support/LearnEverything/config.json"
        elif os.name == "nt":
            app_data = self.temp / "appdata"
            self.env["APPDATA"] = str(app_data)
            self.config = app_data / "LearnEverything/config.json"
        else:
            config_home = self.temp / "config"
            self.env["XDG_CONFIG_HOME"] = str(config_home)
            self.config = config_home / "learn-everything/config.json"

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def run_cli(
        self,
        *arguments: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        completed = subprocess.run(
            [sys.executable, str(CLI), *arguments],
            cwd=str(cwd or REPO_ROOT),
            env=env or self.env,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        try:
            document = json.loads(completed.stdout)
        except json.JSONDecodeError:
            self.fail(
                f"CLI did not emit JSON.\nargs={arguments!r}\nexit={completed.returncode}"
                f"\nstdout={completed.stdout!r}\nstderr={completed.stderr!r}"
            )
        self.assertIsInstance(document, dict)
        return completed, document

    def success(self, *arguments: str, **kwargs: object) -> dict[str, object]:
        completed, document = self.run_cli(*arguments, **kwargs)  # type: ignore[arg-type]
        self.assertEqual(completed.returncode, 0, document)
        self.assertNotEqual(document.get("ok"), False)
        return document

    def error(self, code: str, *arguments: str, **kwargs: object) -> dict[str, object]:
        completed, document = self.run_cli(*arguments, **kwargs)  # type: ignore[arg-type]
        self.assertNotEqual(completed.returncode, 0, document)
        self.assertIs(document.get("ok"), False)
        error = document.get("error")
        self.assertIsInstance(error, dict)
        assert isinstance(error, dict)
        self.assertEqual(error.get("code"), code, document)
        return error

    def dry_run(
        self,
        root: Path | None = None,
        *options: str,
    ) -> dict[str, object]:
        return self.success(
            "vault",
            "init",
            "--root",
            str(root or self.vault),
            *options,
            "--dry-run",
            "--format",
            "json",
        )

    def initialize(
        self,
        root: Path | None = None,
        *options: str,
    ) -> dict[str, object]:
        target = root or self.vault
        plan = self.dry_run(target, *options)
        plan_hash = plan.get("plan_hash")
        self.assertIsInstance(plan_hash, str)
        return self.success(
            "vault",
            "init",
            "--root",
            str(target),
            *options,
            "--expect-plan",
            str(plan_hash),
            "--format",
            "json",
        )

    def lint(self, root: Path | None = None, *options: str) -> tuple[int, dict[str, object]]:
        arguments = ["vault", "lint"]
        if root is not None:
            arguments.extend(["--root", str(root)])
        arguments.extend(options)
        arguments.extend(["--format", "json"])
        completed, document = self.run_cli(*arguments)
        return completed.returncode, document

    @staticmethod
    def write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def git(path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(path), *arguments],
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )

    def concept(self, slug: str = "attention", title: str = "Attention") -> str:
        return f"""---
id: knowledge.{slug}
kind: concept
aliases: [注意力机制]
created: 2026-08-30
updated: 2026-08-30
---

# {title}

## 一句话

根据匹配程度汇总信息。
"""

    def record(self, concept_stem: str = "Attention") -> str:
        return f"""---
id: learning.2026-08-30.attention.01
kind: learning-record
completed_at: 2026-08-30T10:00:00+08:00
---

# Attention 学习

## 本次目标

理解注意力机制。

## 已完成内容

- 解释匹配与汇总。

## 本次沉淀

- 更新 [[{concept_stem}]]。
"""

    def test_root_requires_explicit_initialization(self) -> None:
        self.error("NOT_INITIALIZED", "vault", "root", "--format", "json")

    def test_dry_run_is_zero_write_then_off_mode_initializes(self) -> None:
        plan = self.dry_run(self.vault, "--git", "off")
        self.assertTrue(plan["dry_run"])
        self.assertFalse(self.vault.exists())
        self.assertFalse(self.config.exists())

        result = self.initialize(self.vault, "--git", "off")
        self.assertTrue(result["vault_valid"])
        self.assertEqual(result["git"]["status"], "disabled")  # type: ignore[index]
        self.assertTrue((self.vault / "Home.md").is_file())
        self.assertTrue((self.vault / ".learn-everything/vault.json").is_file())
        for directory in ("knowledge", "learning", "profile", "sources"):
            self.assertTrue((self.vault / directory).is_dir())
        self.assertFalse((self.vault / ".obsidian").exists())
        self.assertEqual(list((self.vault / "profile").iterdir()), [])
        self.assertEqual(list((self.vault / "learning").iterdir()), [])

        root = self.success("vault", "root", "--format", "json")
        self.assertEqual(root["root"], str(self.vault))
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 0, lint)
        self.assertEqual(lint["summary"]["errors"], 0)  # type: ignore[index]

    def test_new_default_creates_git_baseline_and_reruns_as_noop(self) -> None:
        result = self.initialize()
        self.assertEqual(result["config"]["git"], {"mode": "managed", "auto_commit": True})  # type: ignore[index]
        self.assertTrue((self.vault / ".git").is_dir())
        log = self.git(self.vault, "log", "-1", "--pretty=%s")
        self.assertEqual(log.returncode, 0, log.stderr)
        self.assertEqual(log.stdout.strip(), "vault: initialize")
        self.assertEqual(self.git(self.vault, "status", "--porcelain").stdout, "")

        repeat = self.dry_run()
        self.assertTrue(repeat["no_op"])
        self.assertEqual(repeat["actions"], [])
        self.assertEqual(repeat["locator"]["status"], "unchanged_active")  # type: ignore[index]

    def test_auto_commit_off_still_creates_managed_baseline(self) -> None:
        result = self.initialize(self.vault, "--auto-commit", "off")
        self.assertEqual(result["config"]["git"], {"mode": "managed", "auto_commit": False})  # type: ignore[index]
        self.assertTrue((self.vault / ".git").is_dir())
        self.assertEqual(self.git(self.vault, "rev-parse", "--verify", "HEAD").returncode, 0)

    def test_nonempty_directory_requires_existing_and_preserves_user_files(self) -> None:
        self.vault.mkdir()
        self.write(self.vault / "notes.md", "# Existing note\n")
        self.write(self.vault / ".gitignore", "user-rule\n")
        self.error(
            "EXISTING_REQUIRED",
            "vault",
            "init",
            "--root",
            str(self.vault),
            "--dry-run",
            "--format",
            "json",
        )
        result = self.initialize(self.vault, "--existing")
        self.assertEqual(result["config"]["git"], {"mode": "off", "auto_commit": False})  # type: ignore[index]
        self.assertEqual((self.vault / "notes.md").read_text(), "# Existing note\n")
        self.assertEqual((self.vault / ".gitignore").read_text(), "user-rule\n")
        self.assertFalse((self.vault / ".git").exists())

    def test_existing_registration_rejects_incompatible_home(self) -> None:
        self.vault.mkdir()
        self.write(self.vault / "Home.md", "# My existing home\n")
        self.error(
            "PATH_CONFLICT",
            "vault",
            "init",
            "--root",
            str(self.vault),
            "--existing",
            "--dry-run",
            "--format",
            "json",
        )

    def test_plan_hash_detects_unrelated_visible_file_change(self) -> None:
        self.initialize(self.vault, "--git", "off")
        plan = self.dry_run(self.vault)
        self.write(self.vault / "scratch.md", "# New visible note\n")
        self.error(
            "PLAN_MISMATCH",
            "vault",
            "init",
            "--root",
            str(self.vault),
            "--expect-plan",
            str(plan["plan_hash"]),
            "--format",
            "json",
        )

    def test_switch_changes_locator_without_moving_old_vault(self) -> None:
        first = self.vault
        second = self.temp / "second-vault"
        self.initialize(first, "--git", "off")
        self.initialize(second, "--git", "off")
        active = self.success("vault", "root", "--format", "json")
        self.assertEqual(active["root"], str(second))
        self.assertTrue((first / "Home.md").is_file())
        self.assertTrue((second / "Home.md").is_file())

    def test_nested_learn_everything_vault_is_rejected(self) -> None:
        self.initialize(self.vault, "--git", "off")
        child = self.vault / "child"
        self.error(
            "NESTED_VAULT",
            "vault",
            "init",
            "--root",
            str(child),
            "--git",
            "off",
            "--dry-run",
            "--format",
            "json",
        )

    def test_parent_git_repository_requires_git_off(self) -> None:
        parent = self.temp / "project"
        parent.mkdir()
        self.assertEqual(self.git(parent, "init", "-q").returncode, 0)
        nested = parent / "vault"
        self.error(
            "PARENT_GIT_REPOSITORY",
            "vault",
            "init",
            "--root",
            str(nested),
            "--dry-run",
            "--format",
            "json",
        )
        result = self.initialize(nested, "--git", "off")
        self.assertEqual(result["config"]["git"]["mode"], "off")  # type: ignore[index]
        self.assertFalse((nested / ".git").exists())

    def test_ignored_paths_can_be_set_and_cleared(self) -> None:
        self.vault.mkdir()
        self.write(self.vault / "vendor/duplicate.md", "# Vendor\n")
        result = self.initialize(self.vault, "--existing", "--ignored-path", "vendor")
        self.assertEqual(result["config"]["ignored_paths"], ["vendor"])  # type: ignore[index]
        cleared = self.initialize(self.vault, "--clear-ignored-paths")
        self.assertEqual(cleared["config"]["ignored_paths"], [])  # type: ignore[index]

    def test_invalid_ignored_paths_fail_before_write(self) -> None:
        for value in (".", "../outside", "knowledge/generated", "/absolute", "a//b"):
            with self.subTest(value=value):
                self.error(
                    "INVALID_CONFIG",
                    "vault",
                    "init",
                    "--root",
                    str(self.vault),
                    "--git",
                    "off",
                    "--ignored-path",
                    value,
                    "--dry-run",
                    "--format",
                    "json",
                )
        self.assertFalse(self.vault.exists())

    def test_managed_root_symlink_is_rejected(self) -> None:
        self.initialize(self.vault, "--git", "off")
        outside = self.temp / "outside"
        outside.mkdir()
        (self.vault / "knowledge").rmdir()
        (self.vault / "knowledge").symlink_to(outside, target_is_directory=True)

        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("MANAGED_ROOT_INVALID", codes)
        self.error(
            "PATH_CONFLICT",
            "vault",
            "init",
            "--root",
            str(self.vault),
            "--dry-run",
            "--format",
            "json",
        )

    def test_visible_file_symlink_cannot_escape_vault(self) -> None:
        self.initialize(self.vault, "--git", "off")
        outside = self.temp / "outside.png"
        self.write(outside, "outside\n")
        (self.vault / "assets").mkdir()
        (self.vault / "assets/outside.png").symlink_to(outside)
        self.write(
            self.vault / "knowledge/Attention.md",
            self.concept() + "\n![[assets/outside.png]]\n",
        )

        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("PATH_ESCAPE", codes)

    def test_valid_concept_and_learning_record_pass_lint(self) -> None:
        self.initialize(self.vault, "--git", "off")
        self.write(self.vault / "knowledge/Attention.md", self.concept())
        self.write(
            self.vault / "learning/2026/2026-08-30 01 Attention.md",
            self.record(),
        )
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 0, lint)
        self.assertEqual(lint["summary"]["errors"], 0)  # type: ignore[index]
        self.assertEqual(lint["summary"]["warnings"], 0)  # type: ignore[index]

    def test_learning_sequence_is_unique_per_day(self) -> None:
        self.initialize(self.vault, "--git", "off")
        self.write(self.vault / "knowledge/Attention.md", self.concept())
        self.write(
            self.vault / "learning/2026/2026-08-30 01 Attention.md",
            self.record(),
        )
        second = self.record().replace(
            "learning.2026-08-30.attention.01",
            "learning.2026-08-30.transformer.01",
        ).replace("# Attention 学习", "# Transformer 学习")
        self.write(
            self.vault / "learning/2026/2026-08-30 01 Transformer.md",
            second,
        )
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("DAILY_SEQUENCE_COLLISION", codes)

    def test_unknown_nested_frontmatter_is_allowed(self) -> None:
        self.initialize(self.vault, "--git", "off")
        concept = self.concept().replace(
            "updated: 2026-08-30",
            "updated: 2026-08-30\ncustom:\n  nested: value",
        )
        self.write(self.vault / "knowledge/Attention.md", concept)
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 0, lint)

    def test_attachment_paths_are_casefolded_and_unmanaged_headings_resolve(self) -> None:
        self.initialize(self.vault, "--git", "off")
        concept = (
            self.concept()
            + "\n- [[Reference#Details]]\n- [[Reference.v1]]\n- ![[Assets/Diagram.PNG]]\n"
        )
        self.write(self.vault / "knowledge/Attention.md", concept)
        self.write(self.vault / "notes/Reference.md", "# Reference\n\n## Details\n\nText.\n")
        self.write(self.vault / "notes/Reference.v1.md", "# Reference v1\n")
        self.write(self.vault / "assets/diagram.png", "not-a-real-image\n")
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 0, lint)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertNotIn("ATTACHMENT_LINK_ERROR", codes)
        self.assertNotIn("MISSING_HEADING", codes)

    def test_lint_detects_duplicate_identity_and_broken_link(self) -> None:
        self.initialize(self.vault, "--git", "off")
        first = self.concept("attention", "Attention") + "\n- 相关：[[Missing]]\n"
        second = self.concept("attention", "Other")
        self.write(self.vault / "knowledge/Attention.md", first)
        self.write(self.vault / "knowledge/Other.md", second)
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("DUPLICATE_ID", codes)
        self.assertIn("KNOWLEDGE_IDENTITY_COLLISION", codes)
        self.assertIn("NOTE_LINK_ERROR", codes)

    def test_managed_stem_collision_with_unmanaged_note_is_error(self) -> None:
        self.initialize(self.vault, "--git", "off")
        self.write(self.vault / "knowledge/Attention.md", self.concept())
        self.write(self.vault / "archive/attention.md", "# Old note\n")
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("STEM_COLLISION", codes)

    def test_links_in_code_and_unmanaged_broken_links_do_not_fail(self) -> None:
        self.initialize(self.vault, "--git", "off")
        concept = self.concept() + "\n```text\n[[Not A Link]]\n```\n"
        self.write(self.vault / "knowledge/Attention.md", concept)
        self.write(self.vault / "scratch.md", "# Scratch\n\n[[Missing]]\n")
        self.write(
            self.vault / "learning/2026/2026-08-30 01 Attention.md",
            self.record(),
        )
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 0, lint)

    def test_profile_requires_fixed_sections(self) -> None:
        self.initialize(self.vault, "--git", "off")
        self.write(
            self.vault / "profile/Learning Guidance.md",
            """---
id: profile.learning-guidance
kind: profile
created: 2026-08-30
updated: 2026-08-30
---

# Learning Guidance

## 明确偏好

- 先举例。

```markdown
## 教学反馈
```
""",
        )
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("PROFILE_SECTION_COUNT", codes)

    def test_learning_record_requires_valid_path_sections_and_deposit(self) -> None:
        self.initialize(self.vault, "--git", "off")
        self.write(self.vault / "learning/wrong.md", """---
id: learning.2026-02-30.bad.1
kind: learning-record
completed_at: 2026-02-30T10:00:00Z
status: done
---

# Bad record
""")
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("INVALID_DATETIME", codes)
        self.assertIn("LEARNING_PATH_MISMATCH", codes)
        self.assertIn("LEGACY_SESSION_FIELD", codes)
        self.assertIn("MISSING_SECTION", codes)
        self.assertIn("LEARNING_DEPOSIT_MISSING", codes)

    def test_source_requires_http_url_and_dates(self) -> None:
        self.initialize(self.vault, "--git", "off")
        self.write(self.vault / "sources/Bad.md", """---
id: source.bad
kind: source
url: file:///tmp/source
accessed_at: yesterday
created: 2026-08-30
updated: 2026-08-30
---

# Bad source
""")
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 1)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("INVALID_URL", codes)
        self.assertIn("INVALID_DATE", codes)

    def test_source_list_items_warn_without_access_date(self) -> None:
        self.initialize(self.vault, "--git", "off")
        concept = self.concept() + "\n## 来源\n\n- [Paper](https://example.com/paper)\n"
        self.write(self.vault / "knowledge/Attention.md", concept)
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 0, lint)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("SOURCE_ACCESS_DATE_MISSING", codes)

    def test_existing_vault_can_enable_external_git_after_manual_baseline(self) -> None:
        self.vault.mkdir()
        self.write(self.vault / "notes.md", "# Existing\n")
        self.initialize(self.vault, "--existing")
        self.assertEqual(self.git(self.vault, "init", "-q").returncode, 0)
        self.assertEqual(self.git(self.vault, "add", "Home.md", ".learn-everything/vault.json").returncode, 0)
        commit = self.git(
            self.vault,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "baseline",
        )
        self.assertEqual(commit.returncode, 0, commit.stderr)
        result = self.initialize(
            self.vault,
            "--git",
            "external",
            "--auto-commit",
            "on",
        )
        self.assertEqual(result["config"]["git"], {"mode": "external", "auto_commit": True})  # type: ignore[index]
        exit_code, lint = self.lint()
        self.assertEqual(exit_code, 0, lint)

    def test_history_base_warns_when_learning_record_changes(self) -> None:
        self.initialize()
        self.write(self.vault / "knowledge/Attention.md", self.concept())
        record_path = self.vault / "learning/2026/2026-08-30 01 Attention.md"
        self.write(record_path, self.record())
        self.assertEqual(self.git(self.vault, "add", "knowledge", "learning").returncode, 0)
        commit = self.git(
            self.vault,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "learn",
        )
        self.assertEqual(commit.returncode, 0, commit.stderr)
        base = self.git(self.vault, "rev-parse", "HEAD").stdout.strip()
        self.write(record_path, self.record() + "\nChanged.\n")
        exit_code, lint = self.lint(None, "--base", base)
        self.assertEqual(exit_code, 0, lint)
        codes = {item["code"] for item in lint["diagnostics"]}  # type: ignore[index]
        self.assertIn("LEARNING_HISTORY_CHANGED", codes)

    def test_managed_baseline_repair_preserves_existing_staged_changes(self) -> None:
        self.initialize()
        self.write(self.vault / "scratch.md", "# User work\n")
        self.assertEqual(self.git(self.vault, "add", "scratch.md").returncode, 0)
        self.assertEqual(self.git(self.vault, "rm", "--cached", "Home.md").returncode, 0)
        before = self.git(self.vault, "diff", "--cached", "--name-status").stdout
        commit_before = self.git(self.vault, "rev-parse", "HEAD").stdout.strip()

        result = self.initialize()

        self.assertTrue(result["degraded"])
        self.assertEqual(result["git"]["status"], "degraded")  # type: ignore[index]
        self.assertEqual(self.git(self.vault, "diff", "--cached", "--name-status").stdout, before)
        self.assertEqual(self.git(self.vault, "rev-parse", "HEAD").stdout.strip(), commit_before)

    def test_legacy_session_commands_are_removed(self) -> None:
        self.error("INVALID_ARGUMENT", "session", "get", "--format", "json")


if __name__ == "__main__":
    unittest.main()
