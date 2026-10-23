# AgentSuite

Shared instructions, three reusable skills and setup tools for Sean's projects.

| Material | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Durable working agreements |
| [skills](skills/README.md) | PHP web work, NearlyFreeSpeech hosting and machine bootstrap |
| [tools/install.py](tools/install.py) | Install the baseline and skills into a consumer checkout |
| [hooks/brevity.py](hooks/brevity.py) | Optional Claude response-length reminder |
| [tools/todo](tools/todo) | Read tickets and propose changes to the Inbox |

## Install or update a consumer

Python 3.10+ is required. Run from the AgentSuite checkout:

```sh
python3 tools/install.py repo ../CalMind --dry-run
python3 tools/install.py repo ../CalMind
python3 tools/install.py repo ../CalMind --check
```

On Windows use a working Python interpreter (`py -3` if configured). Installation uses ordinary files and works without symlink privileges. It:

- Adds a managed block to the consumer's `AGENTS.md`, leaving local instructions outside it intact. Codex loads the contents directly; a sibling `@` import is not sufficient.
- Adds `@AGENTS.md` to `CLAUDE.md` if missing.
- Copies skills into `.agents/skills` for Codex and `.claude/skills` for Claude. `.agentsuite/install.json` records the installed hashes. Updates refuse to overwrite a locally modified skill; `--check` reports missing or stale files.

Keep these generated files with the consumer if its agents need to work without a sibling AgentSuite checkout. Edit shared material here and rerun the installer. Use local instructions for deliberate project differences. Existing skill symlinks are left alone with an error; migrate them explicitly instead of writing through them.

Discovery rules verified against [OpenAI Docs: instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [skills](https://learn.chatgpt.com/docs/build-skills) and [Claude memory](https://code.claude.com/docs/en/memory), 2026-10-22. The offline tests check the installed layout and contents; they do not launch paid agent sessions. After installing, use Claude `/context` or ask a fresh Codex session to list its loaded instruction sources to confirm live discovery in your installed version.

## Optional brevity hook

```sh
python3 tools/install.py hook ~/.claude --dry-run
python3 tools/install.py hook ~/.claude
python3 tools/install.py hook ~/.claude --check
```

This preserves other settings and hooks, replaces the previous AgentSuite hook entry and uses the current Python executable. Default mode is an advisory warning so a requested explanation is not suppressed. Set `AGENTSUITE_BREVITY_MODE=block` for a strict six-line/700-character limit, or `off` to disable it. Fenced code, table rows and standalone absolute paths do not count. The hook reads `last_assistant_message` before falling back to older transcripts; continuations are never blocked twice. See [Claude Stop input](https://code.claude.com/docs/en/hooks#stop-input), checked 2026-10-22.

## Ticket client

```sh
python3 tools/todo list AgentSuite
python3 tools/todo add AgentSuite bug "Title" -n "Evidence and completion criteria"
python3 tools/todo done 123 -n "Verified result"
```

Provide `TODO_TOKEN` or `~/.config/seancheren/todo-token`. `TODO_API` can override the endpoint. HTTPS is required except for loopback test servers. Requests are not automatically retried: after an ambiguous proposal failure, check the Inbox before retrying.

## Checks

```sh
python3 -B tools/check.py
```

Uses Python 3.10+, Bash and Node.js. On Windows Git Bash is detected automatically, or set `BASH_EXE` to its executable. All checks are offline and use temporary fixtures and command stubs. CI runs the same command on Windows, macOS and Linux. The package-manager recipes are not executed by these checks; validate a real machine's setup before calling that platform ready.

## Suite releases

For projects using the Mind-suite lane, `dtp` means deploy, tag, push; `tdtp` includes the full test run. Defaults: target `main`, bare `x.y.0` tags and a minor bump. A project's explicit release conventions override these defaults (PrivateApp uses `v` tags). Never tag around a failed deploy; reuse a bumped but untagged version. Report through CoreMind's `bin/report-status.sh` when that project uses it; reporting failure must not hide release failure.

Keep mail stubs disabled until Sean authorizes enabling delivery for the affected host. These are suite release conventions, not requirements for unrelated repositories.
