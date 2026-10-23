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


if __name__ == "__main__":
    unittest.main()
