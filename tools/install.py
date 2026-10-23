#!/usr/bin/env python3
"""Install AgentSuite into one checkout, or install the optional Claude brevity hook."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
BEGIN = "<!-- AgentSuite:begin -->"
END = "<!-- AgentSuite:end -->"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    descriptor, name = tempfile.mkstemp(prefix=".agentsuite-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def managed_text(text, body):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError("AGENTS.md has incomplete or duplicate AgentSuite markers")
    block = BEGIN + "\n" + body.rstrip() + "\n" + END
    if BEGIN in text:
        start, finish = text.index(BEGIN), text.index(END)
        if finish < start:
            raise ValueError("AGENTS.md has reversed AgentSuite markers")
        return text[:start] + block + text[finish + len(END):]
    return block + "\n\n" + text


def repository_plan(target):
    target = target.resolve()
    source_root = SOURCE.resolve()
    if target == source_root or source_root.is_relative_to(target):
        raise ValueError("Choose a consumer checkout, not AgentSuite or its parent")
    manifest = target / ".agentsuite/install.json"
    previous = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    if not isinstance(previous, dict) or not isinstance(previous.get("files", {}), dict):
        raise ValueError("Invalid AgentSuite install manifest")
    agents = target / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.exists() else ""
    # Migrate the old Claude-only sibling import to the shared managed block.
    text = "".join(line for line in text.splitlines(keepends=True)
        if not (line.strip().startswith("@") and
            (target / line.strip()[1:]).resolve() == source_root / "AGENTS.md"))
    plan = {agents: managed_text(text, (SOURCE / "AGENTS.md").read_text(encoding="utf-8")).encode()}
    claude = target / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8") if claude.exists() else ""
    if "@AGENTS.md" not in [line.strip() for line in text.splitlines()]:
        plan[claude] = ("@AGENTS.md\n\n" + text).encode()
    owned = {}
    for source in sorted((SOURCE / "skills").rglob("*")):
        if not source.is_file() or source.name == "README.md" or "__pycache__" in source.parts:
            continue
        relative = source.relative_to(SOURCE / "skills")
        for directory in (".agents/skills", ".claude/skills"):
            destination = target / directory / relative
            key, data = destination.relative_to(target).as_posix(), source.read_bytes()
            if destination.is_symlink() or any(parent.is_symlink() for parent in destination.parents if parent != target):
                raise ValueError(f"Refusing to write through a skill symlink: {destination}")
            if destination.exists():
                current = destination.read_bytes()
                if current != data and digest(current) != previous.get("files", {}).get(key):
                    raise ValueError(f"Locally modified or unowned skill: {destination}")
            plan[destination] = data
            owned[key] = digest(data)
    plan[manifest] = (json.dumps({"version": 1, "files": owned}, indent=2, sort_keys=True) + "\n").encode()
    retired = [name for name in previous.get("files", {}) if name not in owned and (target / name).exists()]
    if retired:
        raise ValueError("Retired managed skill files; review and remove explicitly: " + ", ".join(retired))
    return plan


def hook_plan(directory):
    directory = directory.resolve()
    settings = directory / "settings.json"
    text = settings.read_text(encoding="utf-8") if settings.exists() else "{}"
    document = json.loads(text)
    if not isinstance(document, dict):
        raise ValueError("Claude settings must be a JSON object")
    hooks = document.setdefault("hooks", {})
    if not isinstance(hooks, dict) or not isinstance(hooks.get("Stop", []), list):
        raise ValueError("Claude hooks.Stop must be a list")
    script = directory / "hooks/brevity.py"
    executable, filename = Path(sys.executable).as_posix(), script.as_posix()
    command = (f'"{executable}" "{filename}"' if os.name == "nt"
        else shlex.join([executable, filename]))
    groups = []
    for group in hooks.get("Stop", []):
        if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
            raise ValueError("Invalid Claude Stop hook group")
        remaining = []
        for handler in group.get("hooks", []):
            if not isinstance(handler, dict):
                raise ValueError("Invalid Claude Stop hook handler")
            existing = handler.get("command", "")
            if not isinstance(existing, str):
                raise ValueError("Claude hook command must be a string")
            existing = existing.replace("\\", "/")
            if "hooks/brevity.py" not in existing:
                remaining.append(handler)
        if remaining:
            groups.append({**group, "hooks": remaining})
    groups.append({"hooks": [{"type": "command", "command": command}]})
    hooks["Stop"] = groups
    return {script: (SOURCE / "hooks/brevity.py").read_bytes(),
        settings: (json.dumps(document, indent=2) + "\n").encode()}


def apply(plan, *, check=False, dry_run=False):
    for path in plan:
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError(f"Refusing to replace or write through a symlink: {path}")
    changes = [path for path, data in plan.items() if not path.exists() or path.read_bytes() != data]
    if check and changes:
        raise ValueError("Missing or stale: " + ", ".join(str(path) for path in changes))
    for path in changes:
        if not dry_run and not check:
            atomic_write(path, plan[path])
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["repo", "hook"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--check", action="store_true", help="Read-only verification")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        plan = repository_plan(args.path) if args.kind == "repo" else hook_plan(args.path)
        changes = apply(plan, check=args.check, dry_run=args.dry_run)
    except (OSError, ValueError) as error:
        parser.exit(1, f"install: {error}\n")
    print(f"{'Would update' if args.dry_run else 'Checked' if args.check else 'Updated'} {len(changes)} files")


if __name__ == "__main__":
    main()
