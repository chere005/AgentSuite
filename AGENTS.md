# Baseline conventions for AI-agent work on Sean's projects

This is a STUB. Everything below is a starting structure and a set of
suggestions pulled from what's actually worked in the Mind-suite
(CalMind/ChefMind/AcctMind/MyCalMind/CoreMind) — not finished doctrine.
Each section has a TODO marking what still needs Sean's own judgment.
Delete a section if it doesn't end up earning its keep; add sections
this stub didn't anticipate.

## How to use this file

A new project imports this wholesale (`@../AgentSuite/AGENTS.md` from
its own `CLAUDE.md`) or copies down what's relevant. Either way, this
file should only hold things true across MOST projects — anything
project-specific belongs in that project's own `AGENTS.md`, stacked on
top of this baseline.

> TODO: decide the propagation model. CoreMind's canon/consumers split
> (shared bytes copied down, a manifest tracking which files are exact
> vs. deliberately forked, a script that fails loudly on drift) is the
> proven pattern at 4-repo scale — is it overkill here, or does
> AgentSuite need the same discipline once enough projects import it?

## Answers are short

Outcome, decisions the user needs to make, anything blocking them.
Detail belongs in code comments and commit messages, which is where a
person goes looking for it when they actually need it — not in the
chat reply. Don't list what wasn't tested; a caveat inventory costs the
reader the time the brevity was supposed to save.

## Behavior lives in one place, with a test next to it

If a rule can be described in a sentence, it belongs in a shared/core
layer with a test, not copy-pasted into whichever screen or script
happens to need it first.

## Traps: the highest-leverage section in any AGENTS.md

A "Traps" section is a list of things that have ALREADY cost real time
— a footgun discovered the hard way, written down so the next session
(human or agent) doesn't rediscover it by falling in again. The
Mind-suite's own traps sections are the best-proven part of this whole
convention:

- A UI action that doesn't fail fast (waits out a full timeout instead)
- A check that can't fail looking exactly like one that passes (a grep
  for the empty string, an assertion on a container that was never
  there)
- A build/dependency quirk with a specific, non-obvious fix (wrong
  paths, stale caches, a flag that silently changes behavior)

Three general ones, earned on 2026-08-22 and worth keeping whatever the
project — each is a case of a tool being confidently wrong rather than
failing:

- **A fix that keeps reverting is not flaky; something is undoing it.**
  A CocoaPods script phase marked `alwaysOutOfDate` re-extracted a
  vendored framework on every build, silently undoing a repair applied
  beforehand. Fourteen attempts went on suspecting a race. The repair had
  to move INSIDE the step that was overwriting it. When the same fix fails
  the same way twice, stop improving the fix and go and find the writer.
- **A scratch volume is not a neutral disk.** exFAT has no extended
  attributes, so codesign silently produces unsigned bundles and macOS
  writes `._` AppleDouble files that then fail the signature; it has no
  atomic rename, so gradle's cache breaks on it. Both looked like build
  bugs. Check the FILESYSTEM before believing a toolchain has gone mad.
- **An allow-list of ports, hosts or versions goes stale the first time
  reality picks a different one.** A dev-server check listed two ports;
  running it on a third aimed the app at the wrong server and reported a
  server error. Match on the thing that is actually invariant.

> TODO: as more traps get discovered, they belong HERE if they're not
> project-specific — a filesystem quirk, a codesign gotcha, a tool's flag
> behaving differently than documented. "This specific repo's Podfile"
> traps stay local.

## Standing rules — the pattern, not the content

Each Mind-suite repo's AGENTS.md has a short list of non-obvious,
strongly-held rules stated once and referred back to (a data-ownership
rule, a deploy-ordering rule, a version-bumping convention). What makes
them work: they're SHORT, they're STATED WITH THE REASON ("web first,
always — because X"), and they're revisited when reality changes
instead of left to rot.

> TODO: does Sean want a genuinely cross-project standing rule here
> (e.g. "never commit without being asked", "prefer editing to
> creating") — the ones already living in Claude's own global
> instructions are a start, but a few are Mind-suite-specific enough
> that they might belong promoted here once they've proven true on a
> second and third project.

## Release/deploy conventions

The Mind-suite's `dtp`/`tdtp` gesture (deploy-tag-push / test-deploy-
tag-push, one command, bare `x.y.0` tags, minor-bump by default) is a
proven, low-friction release pattern for a solo developer shipping
often. Worth adopting wholesale for a new project rather than
reinventing a release flow each time.

> TODO: is this actually general, or is it coupled to NearlyFreeSpeech
> hosting + the specific rsync-based deploy.sh shape? Worth separating
> "the gesture" (one command, tag, push, minor-bump) from "the specific
> shell implementation" so future projects can adopt the former even on
> different hosting.

## Skills — see `skills/`

`skills/README.md` states the bar: a skill earns a place here once it has
been **useful twice**. Candidates worth promoting out of the Mind-suite,
based on what's already proven useful there:

- **cross-platform-architect** — keeping two platforms (web + native,
  or iOS + Android) as deliberate mirrors of each other without
  sharing code, so a change lands cheaply on both.
- **web-dev conventions** — a specific, opinionated take on
  server-rendered PHP + vanilla JS + SQL with no framework and no
  build step: escaping, CSRF, sessions, prepared statements,
  progressive-enhancement AJAX.
- **nearlyfreespeech** (or whatever the actual hosting target of a new
  project is) — the specific gotchas of a specific host, written down
  once so a deploy doesn't relearn them.
- **ios-watch-dev** style skills — per-platform native conventions
  (SwiftUI/Kotlin/whatever), written as a skill rather than scattered
  across an AGENTS.md, so they can be pulled into ANY project that
  touches that platform, not just the one that first needed it. Note the
  originals were deleted with the app they described (2026-08-22): the
  IDEA is the candidate, not that text.
- A **build-tooling-gotchas** skill might be worth splitting out of
  the Traps section above once it grows — Xcode/CocoaPods/Gradle
  quirks that recur across projects regardless of what each project
  actually does.

## What this file is deliberately NOT

Not a place for project-specific facts (a particular API's shape, a
particular deploy target, a particular data model) — those stay in the
project's own `AGENTS.md`, which imports this file as a baseline, not
the other way around.
