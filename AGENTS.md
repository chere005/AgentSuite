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

- **Answers are SHORT, and only what Sean has to act on.** Outcome, decisions
  he needs to make, anything blocking him. Detail belongs in comments and
  commit messages, which is where he goes looking for it.
- **Do not list what has not been tested.** No caveat sections, no "still
  owed", no unprompted risk inventories — he will say so if something is
  wrong. Say what a check actually proved and stop.

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

## Traps

The highest-leverage section in any repo's AGENTS.md is its own Traps list —
things that ALREADY cost real time there. Two that cost time everywhere:

- The shell's working directory persists between tool calls. `cd` in a
  script, and the next command starts where the last one ended.
- A green check you have not watched fail proves nothing (see Tests).
