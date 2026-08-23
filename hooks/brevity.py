#!/usr/bin/env python3
"""Stop hook: refuse an over-long final reply once, and say what the shape is.

Prose only — fenced code, tables and file paths are exempt, because the rule is
about narration, not about showing him a command he asked for. Blocks at most
once per turn (stop_hook_active), so it can never loop.
"""
import json, re, sys

MAX_LINES = 6
MAX_CHARS = 700

try:
    ev = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if ev.get("stop_hook_active"):        # already nudged this turn
    sys.exit(0)

path = ev.get("transcript_path")
if not path:
    sys.exit(0)

last = ""
try:
    for line in open(path, errors="ignore"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") != "assistant":
            continue
        c = d.get("message", {}).get("content")
        if isinstance(c, list):
            t = " ".join(b.get("text", "") for b in c
                         if isinstance(b, dict) and b.get("type") == "text")
        else:
            t = c if isinstance(c, str) else ""
        if t.strip():
            last = t
except Exception:
    sys.exit(0)

if not last:
    sys.exit(0)

prose = re.sub(r"```.*?```", "", last, flags=re.S)          # code blocks are free
prose = "\n".join(l for l in prose.splitlines() if not l.lstrip().startswith("|"))
lines = [l for l in prose.splitlines() if l.strip()]

if len(lines) <= MAX_LINES and len(prose) <= MAX_CHARS:
    sys.exit(0)

print(json.dumps({
    "decision": "block",
    "reason": (
        f"That reply is {len(lines)} lines / {len(prose)} chars of prose. "
        f"The standing format is:\n\n"
        f"    Done.\n"
        f"    Done. Needs you: <one line>\n\n"
        "Cut it to that. Do not explain what broke, what you changed, or what "
        "you verified — that belongs in the commit message. Do not apologise "
        "or comment on your own performance. Keep only: an answer he asked "
        "for, something blocking him, or a decision that is his."
    ),
}))
sys.exit(0)
