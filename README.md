# AgentSuite

The `AGENTS.md`, skills and tools shared by Sean's repos.

## Disclaimer

Feel free to copy the instructions, skills and tools into your own projects, etc.

**This is a personal project to have some fun with claude code, which generated essentially all of the code, and the rest of this readme:**

## Quick start / Install

```sh
python3 tools/install.py repo ../CalMind     # --dry-run first, --check later
```

Writes a managed block into the repo's `AGENTS.md`, adds `@AGENTS.md` to its `CLAUDE.md`, and copies the skills to `.agents/skills` and `.claude/skills`.

## Platforms

- Any machine with Python 3.10+. Checks also need Bash and Node; CI runs them on Windows, macOS and Linux.

## Usage

```sh
python3 tools/install.py hook ~/.claude      # Claude Code hook that asks for shorter replies
python3 tools/todo list AgentSuite           # read Sean's ticket board; add / done propose tickets
python3 -B tools/check.py                    # offline checks
```

## Notes

- Four skills: PHP web work, NearlyFreeSpeech hosting, machine bootstrap, GitHub Releases deployment. See [skills/](skills/README.md).
- The hook warns past six prose lines or 700 characters; `AGENTSUITE_BREVITY_MODE=block` refuses, `off` disables.
- `tools/todo` needs `TODO_TOKEN` or `~/.config/seancheren/todo-token`; it only proposes, Sean approves in the Inbox.
- Release shorthand: **`tdtp`** = test, deploy, tag, push (full tests first); **`dtp`** = deploy, tag, push (only the tests the change needs). Both end with the new version installed on Sean's machine. Typing either authorizes that repo's release only.

## Building

Nothing to build. `python3 -B tools/check.py` validates the skills, lints `bootstrap.sh` and runs the unit tests.

## Documentation

- [AGENTS.md](AGENTS.md): the working agreements.
- [skills/README.md](skills/README.md): the skills.

## Contributing

Issues and pull requests are welcome. `python3 -B tools/check.py` must pass. No licence file yet.
