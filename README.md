# AgentSuite

Sean's shared home for how AI coding agents should work across every
project — not an app, not a library. A place to write something once
(a convention, a skill, a tool) instead of re-discovering it per repo.

Grew out of the Mind-suite (CalMind / ChefMind / AcctMind / MyCalMind /
CoreMind), where the same lessons — how to write an `AGENTS.md` that
actually gets read, which skills earn their keep, what a "traps" section
is for — kept getting re-learned independently in each repo. This is
where they live once, instead.

## What's here

- **`AGENTS.md`** — the baseline conventions and standing rules a new
  project should start from — and, since 2026-08-23, the imported baseline
  every Mind-suite repo's own AGENTS.md stacks on top of.
- **`skills/`** — reusable Claude Code skills worth having in more than
  one project. Each is a candidate to promote out of whichever repo
  first needed it.
  One of them, `bootstrap`, is about the machine rather than a project:
  it carries the script that takes a bare box to where all of this can be
  cloned, built and shipped.

## How another project uses this

Two levels, pick what fits:

1. **Full import** — a new project's own `CLAUDE.md` (or `AGENTS.md`)
   starts with an `@` import of this repo's baseline, the same way each
   Mind-suite app's `CLAUDE.md` is just `@AGENTS.md`:

   ```
   @../AgentSuite/AGENTS.md
   ```

   (adjust the relative path to wherever this checkout actually sits
   next to the project). The project's own `AGENTS.md` then only needs
   to state what's specific to it — the baseline comes along for free,
   and gets picked up in the SAME BYTES sense CoreMind uses for canon:
   edit it here, every importing project sees the update next session.

2. **Reference, don't import** — for a project that wants to adapt
   rather than inherit wholesale, just link to this repo in its own
   docs ("see AgentSuite's AGENTS.md for the baseline traps-section
   convention") and copy down whatever's actually relevant, same as
   CoreMind's `fork` rows: a deliberate, tracked divergence rather than
   a silent one.

Skills: symlink or copy the ones a project needs into its own
`.claude/skills/`. There's no propagation tooling yet — see the TODO in
`AGENTS.md` about whether this repo ever needs a CoreMind-style
drift-check, or whether "copy it, it's yours now" is good enough at
this scale.

## Status

Settled on 2026-08-23: the AGENTS.md here stopped being a stub when the
common rules were factored up out of the six repos that had been repeating
them, and the first two skills were promoted from seancheren-site.
