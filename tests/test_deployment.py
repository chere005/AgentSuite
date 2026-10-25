import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "skills/make-deployment/templates/preflight.sh"


class DeploymentTests(unittest.TestCase):
    def run_preflight(self, scenario):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            (fixture / "git").write_text("""#!/usr/bin/env bash
printf 'git %s\\n' "$*" >> "$FIXTURE_LOG"
case "$1" in
  status) ;;
  rev-parse) if [ "${2:-}" = --short=7 ]; then echo abc1234; else printf '%040d\\n' 1; fi ;;
  ls-remote) if [ "$SCENARIO" = collision ]; then echo 'existing-ref'; fi ;;
  push) if [ "$SCENARIO" = push-failure ]; then exit 1; fi ;;
  *) exit 90 ;;
esac
exit 0
""", encoding="utf-8", newline="\n")
            (fixture / "gh").write_text("""#!/usr/bin/env bash
printf 'gh %s\\n' "$*" >> "$FIXTURE_LOG"
case "$1 $2" in
  'workflow run') if [ "$SCENARIO" = dispatch-failure ]; then exit 1; fi ;;
  'run list') echo 9001 ;;
  'run watch') ;;
  'run view')
    if [[ "$*" == *'.steps[]'* ]]; then
      if [ "$SCENARIO" = failed-step ]; then echo 'failed: windows > test'; fi
    elif [ "$SCENARIO" != empty-jobs ]; then
      printf 'prepare\\tsuccess\\nmacos\\tsuccess\\n'
      if [ "$SCENARIO" = skipped-build ]; then printf 'windows\\tskipped\\n'; elif [ "$SCENARIO" != missing-build ]; then printf 'windows\\tsuccess\\n'; fi
      printf 'publish\\tskipped\\nsummary\\tsuccess\\n'
    fi ;;
  *) exit 91 ;;
esac
exit 0
""", encoding="utf-8", newline="\n")
            for executable in (fixture / "git", fixture / "gh"):
                executable.chmod(0o755)
            log = fixture / "commands.log"
            expected = fixture / "expected-jobs.txt"
            expected.write_text("prepare\nmacos\nwindows\nsummary\n", encoding="utf-8")
            environment = {**os.environ, "SCENARIO": scenario,
                "FIXTURE_LOG": str(log), "RELEASE_REPO": "fixture/project",
                "RELEASE_EXPECTED_JOBS_FILE": str(expected)}
            # Set PATH inside Bash: native Windows path lists use another separator.
            command = 'export PATH="$(cygpath -u "$1" 2>/dev/null || printf "%s" "$1"):$PATH"; bash "$2"'
            result = subprocess.run([os.environ["BASH_EXE"], "--noprofile", "--norc",
                "-c", command, "fixture", str(fixture), str(PREFLIGHT)],
                env=environment, capture_output=True, text=True, timeout=15)
            return result, log.read_text(encoding="utf-8") if log.exists() else ""

    def test_all_installers_must_pass_and_owned_ref_is_removed(self):
        result, commands = self.run_preflight("pass")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("PASS", result.stdout)
        self.assertIn("--delete preflight/abc1234-", commands)
        self.assertNotIn(" --force ", commands)
        self.assertIn("--force-with-lease=refs/heads/preflight/abc1234-", commands)

    def test_green_job_with_failed_step_is_rejected(self):
        result, commands = self.run_preflight("failed-step")
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn("windows > test", result.stdout)
        self.assertIn("--delete", commands)

    def test_unexpected_skipped_installer_is_rejected(self):
        result, _ = self.run_preflight("skipped-build")
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn("windows (skipped)", result.stdout)

    def test_empty_job_response_is_rejected(self):
        result, _ = self.run_preflight("empty-jobs")
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)

    def test_missing_expected_installer_is_rejected(self):
        result, _ = self.run_preflight("missing-build")
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn("missing expected job: windows", result.stdout)

    def test_preexisting_ref_is_not_changed_or_deleted(self):
        result, commands = self.run_preflight("collision")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertNotIn("git push", commands)
        self.assertNotIn("gh workflow", commands)

    def test_dispatch_failure_removes_only_created_ref(self):
        result, commands = self.run_preflight("dispatch-failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--delete preflight/abc1234-", commands)


if __name__ == "__main__":
    unittest.main()
