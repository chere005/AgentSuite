import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("suite_todo", str(ROOT / "tools/todo"))
spec = importlib.util.spec_from_loader(loader.name, loader)
todo = importlib.util.module_from_spec(spec)
loader.exec_module(todo)


class TodoTests(unittest.TestCase):
    def request(self, reply=None, error=None):
        with patch.object(todo, "token", return_value="fixture-secret") as token:
            with patch.object(todo.urllib.request, "build_opener") as build:
                opened = build.return_value.open
                if error:
                    opened.side_effect = error
                else:
                    opened.return_value = io.BytesIO(json.dumps(reply).encode())
                result = todo.call("POST", {}, {"op": "propose"})
                self.assertEqual(token.call_count, 1)
                self.assertEqual(opened.call_count, 1)
                request = opened.call_args.args[0]
                self.assertEqual(request.get_header("Authorization"), "Bearer fixture-secret")
                self.assertEqual(json.loads(request.data), {"op": "propose"})
                return result

    def test_confirmed_success(self):
        self.assertEqual(self.request({"ok": True, "queued": 1}), {"ok": True, "queued": 1})

    def test_unconfirmed_success_is_an_error(self):
        with self.assertRaisesRegex(SystemExit, "did not confirm"):
            self.request({"ok": False})

    def test_transport_failures_are_not_retried_or_leaked(self):
        with patch.object(todo, "token", return_value="fixture-secret"):
            with patch.object(todo.urllib.request, "build_opener") as build:
                build.return_value.open.side_effect = urllib.error.URLError("fixture-secret")
                with self.assertRaises(SystemExit) as failure:
                    todo.call("POST", {}, {"op": "propose"})
                self.assertEqual(build.return_value.open.call_count, 1)
                self.assertNotIn("fixture-secret", str(failure.exception))

    def test_malformed_json_has_clear_error(self):
        with patch.object(todo, "token", return_value="fixture-secret"):
            with patch.object(todo.urllib.request, "build_opener") as build:
                build.return_value.open.return_value = io.BytesIO(b"not json")
                with self.assertRaisesRegex(SystemExit, "invalid JSON"):
                    todo.call("GET", {})

    def test_http_error_does_not_expose_error_body_or_token(self):
        error = urllib.error.HTTPError("https://fixture.invalid", 401, "fixture-secret", {}, None)
        with self.assertRaises(SystemExit) as failure:
            self.request(error=error)
        self.assertIn("401", str(failure.exception))
        self.assertNotIn("fixture-secret", str(failure.exception))

    def test_credentials_cannot_follow_redirects(self):
        handler = todo.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "moved", {}, "https://other.invalid"))

    def test_remote_plaintext_endpoint_is_rejected_before_reading_token(self):
        with patch.object(todo, "API", "http://remote.invalid/api"):
            with patch.object(todo, "token") as token:
                with self.assertRaisesRegex(SystemExit, "HTTPS"):
                    todo.call("GET", {})
                token.assert_not_called()

    def test_malformed_token_is_rejected_without_displaying_it(self):
        with patch.dict(os.environ, {"TODO_TOKEN": "fixture\r\nsecret"}):
            with self.assertRaises(SystemExit) as failure:
                todo.token()
            self.assertNotIn("secret", str(failure.exception))

    def test_cli_refusal_is_not_reported_as_queued(self):
        with patch.object(todo, "call", return_value={"ok": True, "results": ["!invalid ticket"], "queued": 0}):
            with patch("sys.argv", ["todo", "done", "12"]):
                with self.assertRaisesRegex(SystemExit, "refused"):
                    todo.main()

    def status(self, reply, number="12", status="doing"):
        with patch.object(todo, "call", return_value=reply) as call:
            with patch.object(todo, "source", return_value="fixture agent"):
                with patch("sys.argv", ["todo", "status", number, status, "-n", "fixture evidence"]):
                    with patch("sys.stdout", new_callable=io.StringIO) as output:
                        todo.main()
                        return call, output.getvalue()

    def test_lifecycle_updates_are_explicit_and_confirmed(self):
        for status, label in todo.STATUSES.items():
            with self.subTest(status=status):
                call, output = self.status({"ok": True, "n": 12, "status": status, "changed": True}, status=status)
                call.assert_called_once_with("POST", {}, {"op": "status", "n": 12, "status": status,
                    "from": "fixture agent", "note": "fixture evidence"})
                self.assertEqual(output, f"#12 {label}\n")

    def test_noop_lifecycle_update_is_not_reported_as_a_change(self):
        _, output = self.status({"ok": True, "n": 12, "status": "doing", "changed": False})
        self.assertIn("already current", output)

    def test_status_requires_matching_server_receipt(self):
        for reply in ({"n": 13, "status": "doing", "changed": True},
                      {"n": 12, "status": "done", "changed": True},
                      {"n": 12, "status": "doing", "changed": 1},
                      {"queued": 1}):
            with self.subTest(reply=reply), self.assertRaisesRegex(SystemExit, "invalid status confirmation"):
                self.status({"ok": True, **reply})

    def test_invalid_ticket_number_never_reaches_api(self):
        with patch.object(todo, "call") as call:
            with patch("sys.argv", ["todo", "status", "0", "doing"]):
                with self.assertRaisesRegex(SystemExit, "positive"):
                    todo.main()
            call.assert_not_called()

    def test_expected_status_is_sent_without_automatic_retry(self):
        with patch.object(todo, "call", return_value={"ok": True, "n": 12, "status": "doing", "changed": True}) as call:
            with patch("sys.argv", ["todo", "status", "12", "doing", "--expect", "todo"]):
                with patch("sys.stdout", new_callable=io.StringIO):
                    todo.main()
            self.assertEqual(call.call_count, 1)
            self.assertEqual(call.call_args.args[2]["expect"], "todo")

    def test_list_requests_lifecycle_and_handles_legacy_open(self):
        reply = {"ok": True, "tickets": [
            {"n": 12, "kind": "bug", "title": "Example", "priority": "normal", "status": "open"},
            {"n": 13, "kind": "todo", "title": "Paused progress", "priority": "normal", "status": "review"}]}
        with patch.object(todo, "call", return_value=reply) as call:
            with patch("sys.argv", ["todo", "list", "AgentSuite"]):
                with patch("sys.stdout", new_callable=io.StringIO) as output:
                    todo.main()
            call.assert_called_once_with("GET", {"op": "list", "repo": "AgentSuite", "lifecycle": 1})
            self.assertIn("[To do]", output.getvalue())
            self.assertIn("[On Hold]", output.getvalue())


if __name__ == "__main__":
    unittest.main()
