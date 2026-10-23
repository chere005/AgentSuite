import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("suite_check", ROOT / "tools/check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class ExampleTests(unittest.TestCase):
    def test_form_write_is_not_repeated_after_an_error_response(self):
        text = (ROOT / "skills/web-dev/references/javascript.md").read_text(encoding="utf-8")
        example = re.search(r"```js\n(.*?)```", text, re.S)[1]
        fixture = """
let handler, writes = 0, rendered = 0, notices = [];
const form = {action: 'https://fixture.invalid', dataset: {},
  addEventListener: (_, callback) => { handler = callback; }, submit: () => { writes++; }};
globalThis.FormData = class { append() {} };
let fail = true;
globalThis.fetch = async () => { writes++; return {ok: !fail, json: async () => ({value: 1})}; };
const render = () => { rendered++; };
const showStatus = message => notices.push(message);
""" + example + """
const button = {name:'action', value:'save', disabled:false};
await handler({preventDefault(){}, submitter:button});
if (writes !== 1 || rendered !== 0 || button.disabled || form.dataset.saving) throw Error('Uncertain write replayed or locked form');
if (!notices[0].includes('not confirmed')) throw Error('Failure was hidden');
fail = false;
await handler({preventDefault(){}, submitter:button});
if (writes !== 2 || rendered !== 1 || button.disabled || form.dataset.saving) throw Error('Success handling failed');
globalThis.fetch = async () => { throw Error('network failure'); };
await handler({preventDefault(){}, submitter:button});
if (writes !== 2 || button.disabled || form.dataset.saving) throw Error('Network failure replayed or locked form');
"""
        result = subprocess.run([os.environ["NODE_EXE"], "--input-type=module", "-e", fixture],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_validator_detects_a_broken_reference_and_invalid_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "skills/fixture").mkdir(parents=True)
            skill = root / "skills/fixture/SKILL.md"
            skill.write_text("---\nname: wrong-name\ndescription: Useful trigger\n---\n[missing](missing.md)\n", encoding="utf-8")
            errors = check.validate_material(root)
            self.assertTrue(any("invalid name" in error for error in errors))
            self.assertTrue(any("broken reference" in error for error in errors))
            (skill.parent / "missing.md").write_text("Supporting material", encoding="utf-8")
            skill.write_text("---\nname: fixture\ndescription: Useful trigger\n---\n[reference](missing.md)\n", encoding="utf-8")
            self.assertEqual(check.validate_material(root), [])


if __name__ == "__main__":
    unittest.main()
