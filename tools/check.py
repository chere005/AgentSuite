#!/usr/bin/env python3
"""Run AgentSuite's offline validation. Requires Python 3.10+, Bash and Node.js."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate_material(root):
    errors = []
    for skill in (root / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8")
        header = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        if not header:
            errors.append(f"{skill}: missing frontmatter")
            continue
        # The maintained manifests deliberately use one-line name/description fields.
        values = dict(re.findall(r"^(name|description): (.+)$", header[1], re.M))
        if values.get("name") != skill.parent.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", values.get("name", "")):
            errors.append(f"{skill}: invalid name")
        if not values.get("description") or len(values["description"]) > 1024:
            errors.append(f"{skill}: missing or oversized description")
    # Vendored skills (a SOURCE.md beside SKILL.md) are upstream copies kept unchanged; their
    # code samples look like links, so only AgentSuite's own Markdown is link-checked.
    vendored = {skill.parent for skill in (root / "skills").glob("*/SOURCE.md")}
    for path in root.rglob("*.md"):
        if ".git" in path.relative_to(root).parts or any(v in path.parents for v in vendored):
            continue
        text = path.read_text(encoding="utf-8")
        for raw in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", text):
            link = raw.strip().strip("<>").split("#", 1)[0]
            if not link or urlsplit(link).scheme:
                continue
            if not (path.parent / unquote(link)).exists():
                errors.append(f"{path}: broken reference {link}")
    return errors


def bash_executable():
    candidates = [os.environ.get("BASH_EXE"), shutil.which("bash")]
    if os.name == "nt":
        candidates = [os.environ.get("BASH_EXE"),
            str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"),
            shutil.which("bash")]
    return next((candidate for candidate in candidates if candidate and Path(candidate).is_file()), None)


def main():
    errors = validate_material(ROOT)
    bash = bash_executable()
    node = os.environ.get("NODE_EXE") or shutil.which("node")
    if not bash:
        errors.append("Bash is required; set BASH_EXE to its executable")
    if not node:
        errors.append("Node.js is required; set NODE_EXE to its executable")
    if errors:
        sys.exit("\n".join(errors))
    subprocess.run([bash, "--noprofile", "--norc", "-n",
        str(ROOT / "skills/bootstrap/bootstrap.sh")], check=True)
    environment = {**os.environ, "BASH_EXE": bash, "NODE_EXE": node, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT, env=environment)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
