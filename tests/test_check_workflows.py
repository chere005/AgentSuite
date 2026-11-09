import importlib.util
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_workflows", ROOT / "tools/check-workflows.py")
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)

HANDOFF = """
  handoff:
    if: github.triggering_actor != 'github-actions[bot]'
    runs-on: ubuntu-latest
    timeout-minutes: 5
    continue-on-error: true
    permissions:
      actions: write
    steps:
      - run: gh workflow run x.yml --ref "$GITHUB_REF_NAME"
"""

GOOD = """
name: Release
on:
  push:
    tags: ["v*"]
  workflow_dispatch:
concurrency:
  group: ${{ github.triggering_actor != 'github-actions[bot]' && format('handoff-{0}', github.run_id) || 'release' }}
  cancel-in-progress: false
jobs:""" + HANDOFF + """
  prepare:
    if: github.triggering_actor == 'github-actions[bot]'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    continue-on-error: true
    steps: [{run: "true"}]
  build:
    needs: prepare
    if: needs.prepare.outputs.need == 'true'
    runs-on: macos-15
    timeout-minutes: 60
    continue-on-error: true
    steps: [{run: "true"}]
  publish:
    needs: [prepare, build]
    if: ${{ always() && github.triggering_actor == 'github-actions[bot]' }}
    runs-on: ubuntu-latest
    timeout-minutes: 10
    continue-on-error: true
    steps: [{run: "true"}]
"""


class CheckWorkflowsTests(unittest.TestCase):
    def check(self, workflow, scripts=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/w.yml").write_text(textwrap.dedent(workflow), encoding="utf-8")
            for name, text in (scripts or {}).items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(text, encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
            errors, _ = cw.check_repo(root)
            return "\n".join(errors)

    def test_compliant_workflow_passes(self):
        self.assertEqual(self.check(GOOD), "")

    def test_job_without_continue_on_error(self):
        self.assertIn("job build: needs `continue-on-error: true`",
            self.check(GOOD.replace("timeout-minutes: 60\n    continue-on-error: true", "timeout-minutes: 60")))

    def test_preflight_only_continue_on_error_is_not_enough(self):
        out = self.check(GOOD.replace("timeout-minutes: 60\n    continue-on-error: true",
            "timeout-minutes: 60\n    continue-on-error: ${{ inputs.preflight == true }}"))
        self.assertIn("job build: needs `continue-on-error: true`", out)

    def test_missing_handoff(self):
        self.assertIn("has no `handoff` job", self.check(GOOD.replace("  handoff:", "  handoff_gone:")))

    def test_cancel_in_progress(self):
        self.assertIn("cancel-in-progress: true", self.check(GOOD.replace("cancel-in-progress: false", "cancel-in-progress: true")))

    def test_schedule_and_pull_request(self):
        out = self.check(GOOD.replace("  workflow_dispatch:", "  workflow_dispatch:\n  schedule:\n    - cron: '0 0 * * *'\n  pull_request:"))
        self.assertIn("triggers pull_request, schedule", out)

    def test_always_without_bot_check(self):
        out = self.check(GOOD.replace("if: ${{ always() && github.triggering_actor == 'github-actions[bot]' }}", "if: always()"))
        self.assertIn("job publish: uses always()", out)

    def test_root_job_without_bot_check(self):
        out = self.check(GOOD.replace("  prepare:\n    if: github.triggering_actor == 'github-actions[bot]'\n", "  prepare:\n"))
        self.assertIn("job prepare: must run only in the bot's run", out)

    def test_needs_workflow_dispatch(self):
        self.assertIn("no workflow_dispatch trigger", self.check(GOOD.replace("  workflow_dispatch:\n", "")))

    def test_handoff_group_shared_with_bot(self):
        out = self.check(GOOD.replace("${{ github.triggering_actor != 'github-actions[bot]' && format('handoff-{0}', github.run_id) || 'release' }}", "release"))
        self.assertIn("concurrency group does not depend on github.triggering_actor", out)

    def test_artifact_upload(self):
        out = self.check(GOOD.replace('steps: [{run: "true"}]\n  publish:', 'steps:\n      - uses: actions/upload-artifact@v4\n  publish:'))
        self.assertIn("upload-artifact", out)

    def test_invalid_yaml(self):
        self.assertIn("is not valid YAML", self.check("on: [push\njobs: {"))

    def test_gh_run_rerun_in_a_script(self):
        out = self.check(GOOD, {"tools/lane.sh": "echo retry\ngh run rerun 123 --failed\n"})
        self.assertIn("tools/lane.sh:2: `gh run rerun`", out)

    def test_this_repository_complies(self):
        errors, count = cw.check_repo(ROOT)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
