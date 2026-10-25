# AgentSuite

Feel free to copy the instructions, skills and tools into your own projects, etc.

**This is a personal project to have some fun with claude code, which generated essentially all of the code, and the rest of this readme:**

What all of Sean's repos share: one `AGENTS.md`, four skills, and the tools to install them.

| | |
| --- | --- |
| [AGENTS.md](AGENTS.md) | The working agreements |
| [skills/](skills/README.md) | PHP web work, NearlyFreeSpeech hosting, machine bootstrap, GitHub Releases deployment |
| [tools/install.py](tools/install.py) | Copies the above into a repo, or installs the hook |
| [hooks/brevity.py](hooks/brevity.py) | Claude Code hook that asks for shorter replies |
| [tools/todo](tools/todo) | Proposes tickets to Sean's board |

## Use

```sh
python3 tools/install.py repo ../CalMind     # --dry-run / --check
python3 tools/install.py hook ~/.claude
python3 tools/todo list AgentSuite
python3 -B tools/check.py                    # offline checks; CI runs them on 3 OSes
```

Install writes a managed block into the repo's `AGENTS.md`, adds `@AGENTS.md` to `CLAUDE.md`, and copies the skills to `.agents/skills` and `.claude/skills`. Python 3.10+.

## Suite releases

- **`tdtp`** = test, deploy, tag, push. Full tests first.
- **`dtp`** = deploy, tag, push. Only the tests the change needs.

Both end with the new version installed on Sean's machine. Defaults: `main`, bare `x.y.0` tags, minor bump (PrivateApp uses `v` tags). Never tag around a failure. Typing `dtp` or `tdtp` authorizes that repo's release only.
