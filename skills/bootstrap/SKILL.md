---
name: bootstrap
description: >-
  Bring a bare machine up to where Sean's repos can actually be worked on:
  the system packages and build toolchains a checkout needs, from whatever
  package manager the box has — on macOS that means Homebrew for everything,
  apps included — the Claude desktop app and the Claude Code CLI, the git
  commit identity, an
  ed25519 key for GitHub and a SECOND one for NearlyFreeSpeech, SSH clones of
  every repo the account owns, the gitignored deploy.conf that deploy.sh
  needs, and the global brevity Stop hook. Use on a new or reinstalled
  machine, when a clone or a deploy fails with Permission denied (publickey),
  when php/gh/node turns out not to be installed, or when any single piece of
  that setup has to be redone — the script is re-runnable and each step checks
  for its own result first.
---

# Bootstrap

`bootstrap.sh` beside this file. Eight steps, run in order by default, each one
named so a single piece can be redone on its own:

```sh
~/GIT/AgentSuite/skills/bootstrap/bootstrap.sh          # all of it
~/GIT/AgentSuite/skills/bootstrap/bootstrap.sh keys     # just the keys
~/GIT/AgentSuite/skills/bootstrap/bootstrap.sh -n       # say what would happen
```

| step | what it does |
|------|--------------|
| `packages` | `git python gh node rsync php` via brew / pacman / apt / dnf — plus, on macOS, the build toolchains (`rust`, `cocoapods`, `watchman`, `jq`, `openjdk`, `gradle`, `android-platform-tools`), a `JAVA_HOME` line in the shell profile, and the `firefox`, `sublime-text`, `sublime-merge` casks |
| `claude` | the `claude` desktop cask and the `claude-code` CLI cask; the official installer off macOS |
| `identity` | `git config --global` name and email, from the config below |
| `keys` | `~/.ssh/id_ed25519` for GitHub, `~/.ssh/id_nfsn` for the host, plus the `~/.ssh/config` blocks |
| `clone` | every non-fork repo the account owns — asked of `gh`, so private ones come too — over SSH into `$MIND_DIR` (default `~/GIT`) |
| `deploy` | `$SITE_REPO/deploy.conf` from `$SUITE_DEPLOY_HOST` |
| `hook` | `hooks/brevity.py` into `~/.claude/hooks/`, merged into `~/.claude/settings.json` |
| `verify` | runs the real auth, the real lint, the real test suite |

## Nothing about who this is for is in this repo

AgentSuite is public. A name, an address, a GitHub account and a deploy login
are each a disclosure, and **the name of a private repo is one too** — which is
why there is no repo list in the script: `clone` asks `gh` for every non-fork
repo the account owns, so the private ones are cloned without ever being named
in a public file.

All of it lives in `~/.config/agentsuite/bootstrap.conf` (chmod 600, outside
every checkout); `bootstrap.conf.sample` beside this file says what goes in it.
The environment overrides the file for a one-off run, and anything still
missing is **asked for and then written down**, so an empty config is a fine
starting point. Nothing is ever guessed: a wrong address on a commit or a wrong
host on a deploy is worse than a prompt.

## The two things a script cannot do

A public key has to be pasted into a web page by a human — twice, into two
different web pages. The script generates both keys, puts each on the
clipboard, prints the URL, and **exits 10**: "waiting on you", which a caller
can tell apart from 1, "broken". Re-running picks up from there, because every
step tests for its own result before doing anything.

- **GitHub** — <https://github.com/settings/ssh/new>. Detected by
  `ssh -T git@github.com` answering *successfully authenticated*.
- **NearlyFreeSpeech** — member panel, **Profile → Add SSH Key** (it may read
  *Manage SSH Keys*). A **profile** key, not a per-site one, and it can take a
  minute to take effect. Detected by an actual `ssh <host> true`.

## Why two keys

One key would work for both. A key is the unit you **revoke**, though, and a
laptop that has to be cut off from GitHub should not have to lose the ability
to deploy in the same gesture — so they are separate, and `~/.ssh/config`
decides which host gets which. That block is written between markers, so a
re-run rewrites its own lines and leaves every other `Host` on the machine
alone.

## Order is not arbitrary

`packages` before `claude` (the installers need curl and node), `identity`
before `keys` (both keys are labelled with that address) and before any commit
at all (git refuses one without an identity, and a freshly bootstrapped machine
is precisely the one that has none), `keys` before
`clone` (the private repos in the list have no HTTPS path, and a tree cloned
over HTTPS cannot push without a token either), `clone` before `deploy`
(`deploy.conf` is written *into* the checkout). `CoreMind` clones early because
every other repo's release lane calls its `bin/report-status.sh`, and
`AgentSuite` because every repo's `CLAUDE.md` imports `../AgentSuite/AGENTS.md`
— a missing one is not an error, it is a silently half-briefed agent.

## On macOS, everything is a brew

Formulae and casks both — Sean, 2026-09-21: *"on mac use homebrew to install
everything"*. A machine where half the tools arrived as downloaded `.dmg` files
has no single command that says what is installed or updates it, and the
hand-installed half is the half that quietly goes stale. Casks auto-update
themselves, so re-running the step is a no-op, not a reinstall.

## What it will not do

- **It never runs the Homebrew installer.** That one wants sudo and a password;
  it is a gate with the command printed, not something to run unattended.
- **It never overwrites `~/.claude/settings.json`.** The Stop hook is merged
  into whatever is there, and skipped if an entry with the same command exists.
  Invalid JSON there stops the step rather than replacing the file.
- **It never writes `deploy.conf` from a guess.** No `$SUITE_DEPLOY_HOST`, no
  file — both halves of that login are on the NFSN Site Information page, and a
  wrong one fails at the worst moment.
- **It does not run a deploy.** Bootstrap ends at `verify`; shipping is
  `tdtp`'s job (see `../../AGENTS.md`).

## Traps

- **An installed JDK that `java` cannot find.** brew's `openjdk` is keg-only,
  so `java` resolves to the macOS stub that offers to send you to java.com and
  gradle fails for want of a JDK sitting right there. The documented cure is a
  symlink into `/Library/Java`, which wants sudo; `packages` writes `JAVA_HOME`
  into the shell profile instead, between markers. The `temurin` cask is not
  used for the same reason — **its installer prompts for a sudo password**, so
  it cannot run unattended, and it failed exactly that way on 2026-09-21.
- **The desktop bundle is a `cargo` build wearing a different name.** Each
  app's `desktop/` is Tauri, so `npm run build` there fails with nothing about
  Rust in the message if `cargo` is missing — and `cargo` is missing on a fresh
  Mac. `packages` installs `rust` and `cocoapods` (the iOS prebuild
  wants pods) for exactly this reason; both were found one failed build at a
  time on 2026-09-21.
- **`php` is not on a fresh macOS.** It was missing on 2026-09-21 and took the
  site's lint gate and its whole 90-case suite down with it — the failure reads
  as `command not found: php` from inside `deploy.sh`, several layers from the
  cause. `packages` installs it; `verify` proves it by running the suite.
- **`deploy.conf` is gitignored, so no clone ever carries one.** A fresh
  checkout of the site repo cannot deploy until this runs, and `deploy.sh`
  exits 2 saying so.
- **`deploy.sh` uses `ssh -o BatchMode=yes`.** There is no password fallback:
  until the NFSN key is on the profile, every deploy fails, and it fails
  *after* the lint has passed.
- **A key check that goes through `~/.ssh/config` is not a key check.** On
  macOS, `ssh` resolves that file from the passwd entry rather than `$HOME`, and
  `UseKeychain yes` then serves the login Keychain's key even under
  `IdentitiesOnly` — so on 2026-09-21 a brand-new, unauthorised key tested as
  working and the gate waved it through. Every check here runs `-F /dev/null`
  with an explicit `-i`, which is the only form of the question that is about
  the key file. Related: `ssh -T git@github.com` exits **1** when it succeeds,
  so under `pipefail` a piped check reads a working key as a broken one.
- **A dangling `.claude/skills/` symlink is the honest failure** (see
  `../README.md`) — a repo cloned without `AgentSuite` beside it. Cloning the
  whole list, not one repo, is what avoids it.
