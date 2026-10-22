# The baseline for AI-agent work on Sean's projects

Common ground of the Mind-suite repos, seancheren-site and whatever comes next. A repo imports it with `@../AgentSuite/AGENTS.md` as its first line, then adds only what is true of that repo; only Claude Code follows `@` imports, so each repo also says in one sentence that the baseline lives at `~/GIT/AgentSuite/AGENTS.md`.

## Answers

- **The default reply is one of these two, nothing else.** Longer only if he asked a question (answer it), something blocks him (say what), or a choice is his (one line, stop):

```
Done.
```
```
Done. Needs you: <the decision, in one line>
```

- **Never in a reply:** what broke, its cause, what you changed or verified (that is for the commit message and code comment).
- **Never in a reply:** "you're right", "fair", "good catch", apologies, or any sentence about your own performance.
- **Never in a reply:** caveats, "still owed", risk inventories, untested items, or restating his instruction back to him.
- **Enforced, not trusted:** `hooks/brevity.py` is a `Stop` hook blocking a final reply over six prose lines or 700 characters (fenced code and tables exempt; fires once per turn). Install once, globally:

```sh
mkdir -p ~/.claude/hooks && cp ~/GIT/AgentSuite/hooks/brevity.py ~/.claude/hooks/
# then in ~/.claude/settings.json:
#   "hooks": { "Stop": [ { "matcher": "", "hooks": [
#     { "type": "command", "command": "python3 $HOME/.claude/hooks/brevity.py" } ] } ] }
```

- **Brevity is standing, not per-message.** "Brief" is the format, not a mood; a reply over about four lines is the signal to cut, not to justify.

## Rules

- **Behavior lives in one place, with a test next to it** in the repo's shared layer (`packages/core`, `lib/`, `canon/`), not copy-pasted into each screen or script.
- **Comments state intent; the code may have drifted.** A comment/code disagreement is a finding, not a tiebreak.
- **`main` is the branch.** Stage explicit paths, never `git add -A`; Sean makes his own commits unless that message says otherwise.
- **Two sessions share these repos:** `git pull --autostash` first, then re-check the tree (it exits 0 even if the pop left conflict markers).
- **Approval is per-change, never inherited:** "yes" to one deploy, commit or migration authorizes exactly that one.
- **Reading his live suite to find a bug is fine; writing, reordering or seeding over it happens only on his word, in that message.**
- **Break it before you trust it:** a new check must be shown to FAIL; a check that cannot fail looks like one that passes.
- **A test of a deploy script must neuter `ssh`/`rsync` in its copy first;** a test that can reach production is not a test.
- **Keep Sean's ticket board current, in every repo:** propose new work you find (`~/GIT/AgentSuite/tools/todo add <Repo> todo|bug|misc "title" -n "why/where"`) and propose done when you finish a ticket (`todo done <n> -n "<commit or version>"`); `todo list <Repo>` shows the numbers. It lands in his Inbox at seancheren.com/todo for approval, never on the board directly.

## Releases: dtp / tdtp
- **dtp** = deploy, tag, push; **tdtp** = same lane with the full test run first. One command each, in every repo that ships.
- Tags are bare `x.y.0`, never `v`-prefixed; a ship bumps the MINOR unless Sean says major or patch.
- A failed deploy stops the lane, never tag around one; a re-run reuses the version a failed run bumped but never tagged.
- A release reports to seancheren.com/status via CoreMind's `bin/report-status.sh`; a status failure never fails a release.
- **One heavy build at a time, never in parallel** (concurrent device/desktop builds broke this machine twice).
- **Mail is stubbed:** every send site logs `would have emailed …` and returns; the real transport is commented out beside it. Turning mail on is Sean's host decision, never a side effect of a fix.

## Never patch a server file in place
- **Absolute.** Any file running code reads on a server (`config.php`, `.htaccess`, `php.ini`, data files): no `sed -i`, no `php -r` with `preg_replace`/`str_replace`/`substr`, no heredoc append, no "one line".
- **Only move is replace-whole:** build the full file locally, lint it (`php -l`), check first bytes (`<?php`), upload to a temp name beside the target, lint there, `mv` atomically, then fetch a page and read its first bytes.
- Hashes, keys and tokens contain `$ / . +`: pass them through no shell double quotes, regex replacement or `printf`; a program holds them in a variable and writes a file.
- If a repo has `tools/server-config.sh` (ec530, seancheren-site) it is the only way its server config changes; if not, write one first.
- Mechanism: `preg_replace` back-references mangle a bcrypt hash (`$2y$12$…`); bytes before `<?php` are output, so an insert there leaks the whole config (hashes, SMTP token).

## Traps

- Each repo's own Traps list is its highest-leverage section: things that already cost real time there.
- The shell's working directory persists between tool calls; `cd` in a script and the next command starts where it ended.
- A green check you have not watched fail proves nothing (see Rules).
