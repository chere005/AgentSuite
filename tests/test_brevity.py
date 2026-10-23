import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BrevityTests(unittest.TestCase):
    def hook(self, message, *, transcript_message="Done.", active=False, mode="block"):
        with tempfile.TemporaryDirectory() as directory:
            transcript = Path(directory) / "transcript.jsonl"
            transcript.write_text(json.dumps({"type": "assistant", "message": {
                "content": [{"type": "text", "text": transcript_message}]}}) + "\n",
                encoding="utf-8")
            payload = {"transcript_path": str(transcript), "stop_hook_active": active}
            if message is not None:
                payload["last_assistant_message"] = message
            result = subprocess.run([sys.executable, str(ROOT / "hooks/brevity.py")],
                input=json.dumps(payload), text=True, capture_output=True, timeout=10,
                env={**os.environ, "AGENTSUITE_BREVITY_MODE": mode})
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout) if result.stdout.strip() else {}

    def test_current_payload_wins_over_stale_transcript(self):
        self.assertEqual(self.hook("Long response. " * 100).get("decision"), "block")

    def test_short_current_response_wins_over_old_long_response(self):
        self.assertEqual(self.hook("Done.", transcript_message="Long. " * 200), {})

    def test_warning_preserves_requested_detail(self):
        response = self.hook("Explanation. " * 100, mode="warn")
        self.assertNotIn("decision", response)
        self.assertIn("systemMessage", response)

    def test_continuation_never_loops(self):
        self.assertEqual(self.hook("Long. " * 200, active=True), {})

    def test_code_tables_and_paths_are_exempt(self):
        response = "~~~text\n" + "code\n" * 20 + "~~~\n"
        response += "\n".join("| row | value |" for _ in range(10))
        response += "\n" + "\n".join("/fixture/file%d.txt" % n for n in range(10))
        self.assertEqual(self.hook(response, transcript_message=response), {})

    def test_older_payload_uses_transcript(self):
        self.assertEqual(self.hook(None, transcript_message="Long. " * 200).get("decision"), "block")

    def test_disabled_hook(self):
        self.assertEqual(self.hook("Long. " * 200, transcript_message="Long. " * 200, mode="off"), {})


if __name__ == "__main__":
    unittest.main()
