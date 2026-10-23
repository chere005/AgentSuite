import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".bootstrap-test-", dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.config = self.directory / "bootstrap.conf"
        self.config.write_text("", encoding="utf-8")
        self.environment = {**os.environ, "BOOTSTRAP_HOME": self.directory.as_posix(),
            "BOOTSTRAP_CONF": self.config.as_posix(), "TMPDIR": self.directory.as_posix(),
            "GIT_NAME": "Fixture Name", "GIT_EMAIL": "fixture@example.invalid", "GH_OWNER": "fixture",
            "REPOS": "Fixture", "SITE_REPO": "", "SUITE_DEPLOY_HOST": "", "GIT_PROTOCOL": "https",
            "MIND_DIR": (self.directory / "repos").as_posix()}

    def bash(self, body, **environment):
        script = (ROOT / "skills/bootstrap/bootstrap.sh").as_posix()
        # These commands cannot reach the network, a package manager or production.
        stubs = "\n".join(f'{name}() {{ echo FORBIDDEN_{name} >&2; return 95; }}'
            for name in ("ssh", "curl", "rsync", "sudo", "brew", "gh", "ssh-keygen", "ssh-add"))
        return subprocess.run([os.environ["BASH_EXE"], "--noprofile", "--norc", "-c",
            stubs + f'\nsource "{script}"\nload_config\n' + body],
            env={**self.environment, **environment}, capture_output=True, text=True, timeout=15)

    def test_environment_overrides_config_including_empty_values(self):
        self.config.write_text('GIT_NAME="File value"\nSUITE_DEPLOY_HOST="file-host"\n', encoding="utf-8")
        result = self.bash('printf "%s|%s" "$GIT_NAME" "$SUITE_DEPLOY_HOST"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Fixture Name|")

    def test_complete_dry_run_does_not_write_or_probe_authentication(self):
        before = {path.relative_to(self.directory) for path in self.directory.rglob("*")}
        result = self.bash('detect_pm(){ PM=apt; }; main -n', SITE_REPO="Fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("FORBIDDEN", result.stderr)
        self.assertEqual(before, {path.relative_to(self.directory) for path in self.directory.rglob("*")})

    def test_arguments_remain_literal(self):
        name = "O'Brien; $(should-never-run)"
        result = self.bash('git(){ printf "<%s>\\n" "$@"; }; step_identity', GIT_NAME=name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<" + name + ">", result.stdout)

    def test_clone_failure_is_nonzero_and_not_reported_as_cloned(self):
        result = self.bash('git(){ return 1; }; step_clone')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clone failed", result.stderr)
        self.assertNotIn("Fixture: cloned", result.stdout)

    def test_pull_failure_is_nonzero(self):
        (self.directory / "repos/Fixture/.git").mkdir(parents=True)
        result = self.bash('git(){ case "$*" in *pull*) return 1;; *) return 0;; esac; }; step_clone')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pull failed", result.stderr)
        self.assertNotIn("Fixture: updated", result.stdout)

    def test_dirty_checkout_is_never_pulled_or_stashed(self):
        (self.directory / "repos/Fixture/.git").mkdir(parents=True)
        result = self.bash('git(){ case "$*" in *status*) echo " M work.txt";; *pull*|*stash*) echo FORBIDDEN >&2; return 95;; esac; }; step_clone')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local changes", result.stderr)
        self.assertNotIn("FORBIDDEN", result.stderr)

    def test_failed_site_test_cannot_report_ready(self):
        site = self.directory / "repos/Fixture/tools"
        site.mkdir(parents=True)
        (site / "test.php").write_text("<?php exit(1);", encoding="utf-8")
        result = self.bash('PM=apt; command(){ return 0; }; gh(){ return 0; }; php(){ return 1; }; step_verify',
            SITE_REPO="Fixture", REPOS="")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Site tests failed", result.stderr)
        self.assertNotIn("selected checks passed", result.stdout)

    def test_linux_verification_does_not_require_apple_toolchains(self):
        result = self.bash('PM=apt; command(){ case "$*" in *pod*|*adb*|*cargo*) return 1;; *) return 0;; esac; }; gh(){ return 0; }; step_verify', REPOS="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("selected checks passed", result.stdout)

    def test_github_shell_exit_one_can_mean_successful_authentication(self):
        result = self.bash('ssh(){ echo "Hi fixture! You have successfully authenticated" >&2; return 1; }; github_ok')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_discovery_uses_authenticated_private_repository_endpoint(self):
        result = self.bash('gh(){ if [ "$1" = api ]; then printf "%s\\n" "$@" >&2; echo Fixture; fi; }; git(){ return 0; }; step_clone', REPOS="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("user/repos?", result.stderr)
        self.assertIn("--paginate", result.stderr)
        self.assertNotIn("users/fixture/repos", result.stderr)

    def test_repository_globs_are_rejected_as_literal_names(self):
        result = self.bash('git(){ echo FORBIDDEN >&2; return 95; }; step_clone', REPOS="*")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid repository name: *", result.stderr)
        self.assertNotIn("FORBIDDEN", result.stderr)

    def test_failed_conflict_inspection_is_not_success(self):
        (self.directory / "repos/Fixture/.git").mkdir(parents=True)
        result = self.bash('git(){ case "$*" in *ls-files*) return 1;; *) return 0;; esac; }; step_clone')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Fixture: updated", result.stdout)


if __name__ == "__main__":
    unittest.main()
