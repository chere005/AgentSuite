#!/usr/bin/env python3
"""Check a repo's GitHub Actions workflows against the quiet-CI contract (AgentSuite/ci.md).

    python3 tools/check-workflows.py [REPO_DIR ...]      default: the current directory

GitHub mails a run's outcome to whoever triggered it. The contract keeps every run a person (or a person's agent)
triggers down to one tiny `handoff` job that re-dispatches the workflow as the repository's bot (GITHUB_TOKEN); the
bot's run does the real work, and every job is continue-on-error so even the bot's run stays green. Our own scripts
read job results; GitHub has nothing to mail about.

Exit 0 = every workflow complies, 1 = violations (listed), 2 = could not check (no YAML parser, unreadable file).
Needs PyYAML, or Ruby's bundled YAML (macOS ships it). Python 3.8+.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

BOT = "github-actions[bot]"
BOT_RUN = re.compile(r"github\.triggering_actor\s*==\s*'github-actions\[bot\]'")
HUMAN_RUN = re.compile(r"github\.triggering_actor\s*!=\s*'github-actions\[bot\]'")
STATUS_FN = re.compile(r"\b(always|failure|cancelled)\(\)")
ALLOWED_TRIGGERS = {"push", "workflow_dispatch", "workflow_call"}
SCRIPT_SUFFIXES = {".sh", ".mjs", ".js", ".cjs", ".ts", ".py", ".ps1", ""}
SKIP_DIRS = {".git", "node_modules", ".github", "dist", "build", "target", ".agents", ".claude", "vendor",
             "tests", "test", "e2e", "__tests__"}


def load_yaml(path):
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is not None:
        # BaseLoader keeps every scalar a string ("true", "on"), so YAML 1.1's on: -> True never happens.
        return yaml.load(text, Loader=yaml.BaseLoader)
    ruby = shutil.which("ruby")
    if ruby:
        out = subprocess.run([ruby, "-ryaml", "-rjson", "-e",
            "puts JSON.dump(YAML.safe_load(STDIN.read, aliases: true))"],
            input=text, capture_output=True, text=True)
        if out.returncode == 0:
            data = json.loads(out.stdout)
            return stringify(data)
        raise ValueError(out.stderr.strip() or "ruby could not parse it")
    raise RuntimeError("no YAML parser: install PyYAML (python3 -m pip install pyyaml) or Ruby")


def stringify(node):
    """Ruby's YAML is 1.1-ish too: normalise to BaseLoader's all-strings shape."""
    if isinstance(node, dict):
        return {("on" if k is True else str(k)): stringify(v) for k, v in node.items()}
    if isinstance(node, list):
        return [stringify(v) for v in node]
    if node is None:
        return ""
    if isinstance(node, bool):
        return "true" if node else "false"
    return str(node)


def triggers(doc):
    on = doc.get("on", doc.get("true", ""))
    if isinstance(on, str):
        return {on} if on else set()
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on)
    return set()


def check_workflow(path):
    errors = []
    say = lambda msg: errors.append(f"{path}: {msg}")
    try:
        doc = load_yaml(path)
    except RuntimeError:
        raise
    except Exception as exc:  # a file GitHub cannot parse fails its run on push, and mails
        say(f"is not valid YAML ({str(exc).splitlines()[0]})")
        return errors
    if not isinstance(doc, dict):
        say("is not a workflow (no mapping at the top)")
        return errors

    on = triggers(doc)
    bad = sorted(on - ALLOWED_TRIGGERS)
    if bad:
        say(f"triggers {', '.join(bad)}: only push, workflow_dispatch and workflow_call are allowed "
            "(a schedule mails its author, a pull_request run cannot hand off)")
    callable_only = on == {"workflow_call"}
    if not callable_only and "workflow_dispatch" not in on:
        say("has no workflow_dispatch trigger: the handoff job re-dispatches this workflow, so it needs one")

    def check_concurrency(where, conc, need_actor):
        if not conc:
            return
        if isinstance(conc, str):
            group, cancel = conc, "false"
        else:
            group, cancel = str(conc.get("group", "")), str(conc.get("cancel-in-progress", "false"))
        if cancel.strip().lower() != "false":
            say(f"{where}concurrency has cancel-in-progress: {cancel} - a cancelled run is mailed like a failed one; use false")
        if need_actor and "triggering_actor" not in group:
            say(f"{where}concurrency group does not depend on github.triggering_actor: a person's handoff run would "
                "queue behind (and can be cancelled by) the bot's run. Give handoff runs their own group, e.g. "
                "${{ github.triggering_actor != 'github-actions[bot]' && format('handoff-{0}', github.run_id) || ... }}")

    check_concurrency("", doc.get("concurrency"), need_actor=not callable_only)

    jobs = doc.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        say("has no jobs")
        return errors

    if not callable_only:
        handoff = jobs.get("handoff")
        if not isinstance(handoff, dict):
            say("has no `handoff` job (a person-triggered run must only hand the work to the bot; see AgentSuite/ci.md)")
        else:
            cond = str(handoff.get("if", ""))
            if not HUMAN_RUN.search(cond):
                say(f"job handoff: if must be github.triggering_actor != '{BOT}' (it is: {cond or 'unset'})")
            if handoff.get("needs"):
                say("job handoff: must not need other jobs")
            runs_on = str(handoff.get("runs-on", ""))
            if not runs_on.startswith("ubuntu-"):
                say(f"job handoff: runs-on must be an ubuntu runner (it is: {runs_on or 'unset'})")
            perms = handoff.get("permissions") or {}
            if not isinstance(perms, dict) or perms.get("actions") != "write":
                say("job handoff: needs permissions: actions: write (to dispatch the workflow as the bot)")
            steps = handoff.get("steps") or []
            if "gh workflow run" not in json.dumps(steps):
                say("job handoff: no step runs `gh workflow run` - it hands nothing off")

    for name, job in jobs.items():
        if not isinstance(job, dict):
            say(f"job {name}: not a mapping")
            continue
        where = f"job {name}: "
        if str(job.get("continue-on-error", "")).strip() != "true":
            say(where + "needs `continue-on-error: true` (literal): a failed job must not turn the run red")
        timeout = str(job.get("timeout-minutes", "")).strip()
        if not timeout.isdigit() and "uses" not in job:
            say(where + "needs timeout-minutes")
        check_concurrency(where, job.get("concurrency"), need_actor=False)
        if name == "handoff" or callable_only:
            continue
        cond = str(job.get("if", ""))
        needs = job.get("needs")
        if BOT_RUN.search(cond):
            continue
        if not needs:
            say(where + f"must run only in the bot's run: add `if: github.triggering_actor == '{BOT}'`")
        elif STATUS_FN.search(cond):
            say(where + f"uses {STATUS_FN.search(cond).group(0)}, which runs it even when what it needs was skipped "
                f"(a person's run): add `github.triggering_actor == '{BOT}' &&` to its if")

    text = path.read_text(encoding="utf-8")
    if re.search(r"uses:\s*['\"]?actions/(upload|download)-artifact", text):
        say("uses actions/upload-artifact or download-artifact: the account's artifact quota fills and then every run "
            "fails; attach to the release or write the run summary instead")
    return errors


def check_scripts(root):
    """`gh run rerun` re-runs as the person (the bot-only jobs then skip and nothing is rebuilt)."""
    errors = []
    try:
        listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True, check=True)
        files = [root / f for f in listed.stdout.split("\0") if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = [p for p in root.rglob("*") if p.is_file()]
    for path in files:
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]) or path.suffix not in SCRIPT_SUFFIXES:
            continue
        if path.suffix == "" and not str(rel).startswith(("tools/", "scripts/", "bin/", ".githooks/")):
            continue
        if rel.name == "check-workflows.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if re.search(r"\bgh\s+run\s+rerun\b", line):
                errors.append(f"{rel}:{n}: `gh run rerun` runs as you, so the bot-only jobs skip: re-dispatch instead "
                              "(gh workflow run <file> --ref <ref> -f ...; its handoff job passes it to the bot)")
    return errors


def check_repo(root):
    root = Path(root).resolve()
    flows = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    errors = []
    for flow in flows:
        errors += check_workflow(flow)
    errors += check_scripts(root)
    return [e.replace(str(root) + "/", "") for e in errors], len(flows)


def main(argv):
    roots = argv or ["."]
    failed = False
    for root in roots:
        try:
            errors, count = check_repo(root)
        except RuntimeError as exc:
            print(f"check-workflows: {exc}", file=sys.stderr)
            return 2
        name = Path(root).resolve().name
        if errors:
            failed = True
            print(f"check-workflows: {name}: {len(errors)} problem(s) - see AgentSuite/ci.md")
            for e in errors:
                print("  " + e)
        else:
            print(f"check-workflows: {name}: {count} workflow(s) follow the quiet-CI contract")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
