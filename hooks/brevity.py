#!/usr/bin/env python3
"""Claude Stop hook. Warn by default; AGENTSUITE_BREVITY_MODE=block opts into enforcement."""
import json
import os
from pathlib import Path
import re
import sys


def last_message(event):
    # Stop can arrive before the current response is flushed to the transcript.
    if isinstance(event.get("last_assistant_message"), str):
        return event["last_assistant_message"]
    last = ""
    try:
        with Path(event["transcript_path"]).open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                content = record.get("message", {}).get("content", "")
                if isinstance(content, list):
                    content = " ".join(block.get("text", "") for block in content
                        if isinstance(block, dict) and block.get("type") == "text")
                if isinstance(content, str) and content.strip():
                    last = content
    except (OSError, KeyError, TypeError):
        pass
    return last


def prose_lines(message):
    lines, fence = [], None
    for line in message.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if marker:
            token, suffix = marker.groups()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not suffix.strip():
                fence = None
            continue
        if fence is not None or not line.strip() or line.lstrip().startswith("|"):
            continue
        if re.fullmatch(r"(?:[A-Za-z]:[\\/]|/)[^\r\n]*", line.strip()):
            continue
        lines.append(line)
    return lines


def main():
    mode = os.environ.get("AGENTSUITE_BREVITY_MODE", "warn")
    if mode == "off":
        return
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict) or event.get("stop_hook_active"):
            return
        lines = prose_lines(last_message(event))
    except (ValueError, TypeError, AttributeError):
        return
    if len(lines) <= 6 and len("\n".join(lines)) <= 700:
        return
    reason = "Keep the reply concise. Retain requested detail, blockers, and material verification limits."
    result = {"decision": "block", "reason": reason} if mode == "block" else {"systemMessage": reason}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
