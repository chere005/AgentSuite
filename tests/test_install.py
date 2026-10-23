import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("suite_install", ROOT / "tools/install.py")
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "source"
        self.target = self.directory / "consumer's space"
        self.target.mkdir()
        (self.source / "skills/fixture").mkdir(parents=True)
        (self.source / "skills/fixture/SKILL.md").write_text("fixture skill", encoding="utf-8")
        (self.source / "hooks").mkdir()
        (self.source / "hooks/brevity.py").write_text("# fixture hook\n", encoding="utf-8")
        (self.source / "AGENTS.md").write_text("# Shared\nFixture baseline\n", encoding="utf-8")
        self.patch = patch.object(install, "SOURCE", self.source)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_installs_both_discovery_layouts_and_preserves_local_rules(self):
        (self.target / "AGENTS.md").write_text("@../source/AGENTS.md\nLocal rule\n", encoding="utf-8")
        (self.target / "CLAUDE.md").write_text("Claude local rule\n", encoding="utf-8")
        install.apply(install.repository_plan(self.target))
        agents = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Local rule", agents)
        self.assertEqual(agents.count("Fixture baseline"), 1)
        self.assertNotIn("@../source/AGENTS.md", agents)
        self.assertIn("@AGENTS.md", (self.target / "CLAUDE.md").read_text(encoding="utf-8"))
        for folder in (".agents", ".claude"):
            self.assertEqual((self.target / folder / "skills/fixture/SKILL.md").read_text(), "fixture skill")
        self.assertEqual(install.apply(install.repository_plan(self.target)), [])
        self.assertEqual(install.apply(install.repository_plan(self.target), check=True), [])

    def test_dry_run_and_missing_check_do_not_write(self):
        self.assertTrue(install.apply(install.repository_plan(self.target), dry_run=True))
        self.assertEqual(list(self.target.iterdir()), [])
        with self.assertRaises(ValueError):
            install.apply(install.repository_plan(self.target), check=True)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_legacy_import_migration_normalizes_source_path_aliases(self):
        (self.target / "AGENTS.md").write_text("@../source/AGENTS.md\nLocal rule\n", encoding="utf-8")
        with patch.object(install, "SOURCE", self.source / "../source"):
            install.apply(install.repository_plan(self.target))
        agents = (self.target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("@../source/AGENTS.md", agents)
        self.assertIn("Local rule", agents)

    def test_update_refuses_locally_modified_skills_before_writing(self):
        install.apply(install.repository_plan(self.target))
        edited = self.target / ".agents/skills/fixture/SKILL.md"
        edited.write_text("consumer modification", encoding="utf-8")
        before = (self.target / "AGENTS.md").read_bytes()
        (self.source / "AGENTS.md").write_text("new shared rule", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "modified or unowned"):
            install.repository_plan(self.target)
        self.assertEqual((self.target / "AGENTS.md").read_bytes(), before)
        self.assertEqual(edited.read_text(), "consumer modification")

    def test_source_updates_are_detected_and_can_be_applied(self):
        install.apply(install.repository_plan(self.target))
        (self.source / "skills/fixture/SKILL.md").write_text("updated fixture", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Missing or stale"):
            install.apply(install.repository_plan(self.target), check=True)
        install.apply(install.repository_plan(self.target))
        self.assertEqual((self.target / ".agents/skills/fixture/SKILL.md").read_text(), "updated fixture")

    def test_retired_skill_is_reported_without_deleting_it(self):
        install.apply(install.repository_plan(self.target))
        (self.source / "skills/fixture/SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "Retired managed"):
            install.repository_plan(self.target)
        self.assertTrue((self.target / ".agents/skills/fixture/SKILL.md").exists())

    def test_instruction_symlink_is_never_replaced(self):
        outside = self.directory / "external.md"
        outside.write_text("External instructions", encoding="utf-8")
        try:
            (self.target / "AGENTS.md").symlink_to(outside)
        except OSError:
            self.skipTest("Creating symlinks requires Windows privileges; enabled on Unix CI")
        with self.assertRaisesRegex(ValueError, "symlink"):
            install.apply(install.repository_plan(self.target))
        self.assertTrue((self.target / "AGENTS.md").is_symlink())
        self.assertEqual(outside.read_text(), "External instructions")

    def test_invalid_settings_cannot_partially_install_hook(self):
        (self.target / "settings.json").write_text("{invalid", encoding="utf-8")
        with self.assertRaises(ValueError):
            install.hook_plan(self.target)
        self.assertFalse((self.target / "hooks").exists())

    def test_hook_migration_preserves_other_hooks_and_is_idempotent(self):
        original = {"theme": "dark", "hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "python3 $HOME/.claude/hooks/brevity.py"},
            {"type": "command", "command": "unrelated-command"}]}]}}
        (self.target / "settings.json").write_text(json.dumps(original), encoding="utf-8")
        install.apply(install.hook_plan(self.target))
        actual = json.loads((self.target / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(actual["theme"], "dark")
        commands = [hook["command"] for group in actual["hooks"]["Stop"] for hook in group["hooks"]]
        self.assertIn("unrelated-command", commands)
        self.assertEqual(sum("brevity.py" in command for command in commands), 1)
        self.assertEqual(install.apply(install.hook_plan(self.target)), [])


if __name__ == "__main__":
    unittest.main()
