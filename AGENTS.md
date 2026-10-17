# The baseline for AI-agent work on Sean's projects

This is the settled common ground of the Mind-suite repos
(CalMind / ChefMind / AcctMind / MyCalMind / CoreMind), seancheren-site, and
whatever comes next. Everything here earned its place by being written — in
almost the same words — in three or more of those repos' own AGENTS.md files;
on 2026-08-23 Sean had it factored up ("consolidate all common AGENTS and
relevant documentation from all the MindSuite repos in AgentSuite").

A repo stacks its own AGENTS.md on top of this one: `@../AgentSuite/AGENTS.md`
as the first line, then only what is true of that repo alone. Only Claude Code
follows `@` imports — any other agent sees the literal line — so each repo also
says in one plain sentence that the baseline lives at
`~/GIT/AgentSuite/AGENTS.md`. Nothing here is copied bytes and nothing is
checked for drift: prose propagates by being imported, not by manifest.

## Answers

**The default reply is one of these two, and nothing else:**

```
Done.
```
```
Done. Needs you: <the decision, in one line>
```

Anything longer needs a reason that is not "I did work and want credit for
it". The three that qualify: he asked a question (answer it), something is
blocking him (say what), or a choice is genuinely his (state it in one line
and stop).

**Never in a reply, ever:**

- what broke, what caused it, what you changed, what you verified — that is
  what the commit message and the code comment are for, and it is where he
  looks
- "you're right", "fair", "good catch", apologies, or any sentence about your
  own performance
- caveats, "still owed", risk inventories, or anything not yet tested — he
  will say if something is wrong
- restating his instruction back to him

**IT IS ENFORCED, not trusted.** `hooks/brevity.py` in this repo is a Claude
Code `Stop` hook: it reads the turn's final reply and blocks anything over six
prose lines or 700 characters, handing back the format above. Fenced code and
tables are exempt — the rule is about narration, not about showing him a
command he asked for — and it fires at most once per turn, so it cannot loop.
Install it once, globally, for every project:

```sh
mkdir -p ~/.claude/hooks && cp ~/GIT/AgentSuite/hooks/brevity.py ~/.claude/hooks/
# then in ~/.claude/settings.json:
#   "hooks": { "Stop": [ { "matcher": "", "hooks": [
#     { "type": "command", "command": "python3 $HOME/.claude/hooks/brevity.py" } ] } ] }
```

Prose asking for brevity has failed for as long as it has existed here. A hook
is the version that cannot be read past.

**BREVITY IS STANDING, NOT PER-MESSAGE.** This is the rule that actually
fails. He says "brief", the next reply is short, and the one after it is a
wall again — measured on 2026-08-23: eleven separate demands in one session,
and the drift came back within two replies every time. It is not a mood he
sets; it is the format. If a reply is over about four lines, that is the
signal to cut, not to justify.

## Code

- **Behavior lives in one place, with a test next to it.** If a rule can be
  said in a sentence, it belongs in the shared layer (each repo's AGENTS.md
  names its own — `packages/core`, `lib/`, `canon/`) with a test, not
  copy-pasted into whichever screen or script needed it first.
- **Comments state intent; the code may have drifted.** When a comment and
  the code disagree, that is a finding, not a tiebreak.

## Git

- **`main` is the branch.** Stage explicit paths — never `git add -A`. Sean
  makes his own commits unless he says otherwise in that message.
- **Two sessions share these repos.** `git pull --autostash` first, so another
  agent's half-finished work does not ride along on your commit — and check the
  tree again afterwards, because that pull exits 0 even when the autostash pop
  left conflict markers behind.
- **Approval is per-change, never inherited.** "Yes" to one deploy, one
  commit, one migration authorizes exactly that one.

## Sean's data

- **Sean's data is his.** Reading his live suite to find a bug is fine and
  has found real ones. Writing to it, reordering it, or seeding over his
  account is not — a write to live data happens on his word, in that message.

## Tests

- **Break it before you trust it.** A new check must be shown to FAIL —
  a check that cannot fail looks exactly like one that passes.
- **Anything that tests a deploy script must neuter `ssh`/`rsync` in its
  copy first.** The same near-miss is on record in two repos; a test that
  can reach production is not a test.

## Releases: the dtp / tdtp gesture

Sean's shorthand, suite-wide since 2026-08-22: **dtp** = deploy, tag, push;
**tdtp** = the same lane with the full test run in front. Two lanes, one
command each, in every repo that ships.

- Tags are bare `x.y.0` — never `v`-prefixed.
- A ship bumps the MINOR version unless Sean says major or patch.
- A failed deploy stops the lane — never tag around one. A re-run reuses the
  version a failed run bumped-but-never-tagged rather than burning a number.
- A release reports itself to seancheren.com/status via CoreMind's
  `bin/report-status.sh`; a status failure never fails a release.
- **One heavy build at a time, never in parallel** — two concurrent
  device/desktop builds have broken this machine twice.

## Mail

- **Mail is stubbed, deliberately.** Every send site logs
  `would have emailed …` and returns without sending; the real transport sits
  commented out beside the stub, one uncomment away. Turning mail on is a
  host's decision made by Sean, never a side effect of a fix.

## A file on a server is never patched in place

**This is absolute.** On 2026-10-17 an agent inserted one user into
`/home/protected/lib/config.php` on ec530.com with a regex over SSH. The
insert landed before `<?php`, which turned the open tag into text, and a
second "repair" stripped the tag entirely. Everything before `<?php` in a
`.php` file is OUTPUT: for about a minute every page on the site began with the
whole config — every username, every password hash, and the live SMTP
token. Sean saw it on a screen share. On a work site that is a breach.

So, on any server, for any file that running code reads — `config.php`,
`.htaccess`, `php.ini`, a data file, anything:

- **Never edit it in place.** No `sed -i`, no `php -r` with `preg_replace`,
  `str_replace` or `substr` over the file, no heredoc appending, no "just add
  one line". Not once, not for a one-liner, not because it worked last time.
- **The only move is replace-whole:** build the complete new file locally,
  **lint it** (`php -l` for PHP), confirm its first bytes are what the format
  requires (`<?php`), upload it to a temp name beside the target, lint it
  there too, then `mv` it over — one atomic rename. Then **fetch a page and
  read its first bytes** before saying it is done.
- A password hash, an API key, a token: these contain `$`, `/`, `.` and `+`.
  They pass through **no** shell double quotes, no regex replacement string,
  no `printf` format. A program holds them in a variable and writes a file.
- If a repo has `tools/server-config.sh` (ec530, seancheren-site), that is the
  only way its server config changes. If it does not, write one first.

The mechanism, so nobody re-derives it the hard way: `preg_replace` reads `$2`
and `$12` in a replacement string as back-references, so a bcrypt hash
(`$2y$12$…`) comes out mangled; a `strpos` for `[` that finds nothing returns
`false`, and `substr($s, 0, false + 1)` is "the first byte". Each edit looked
like a one-liner. Each was a deploy of a config file with no lint and no check.

## Traps

The highest-leverage section in any repo's AGENTS.md is its own Traps list —
things that ALREADY cost real time there. Two that cost time everywhere:

- The shell's working directory persists between tool calls. `cd` in a
  script, and the next command starts where the last one ended.
- A green check you have not watched fail proves nothing (see Tests).
