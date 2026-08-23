# skills/

Claude Code skills worth having in more than one project.

## What belongs here

A skill earns a place here once it has been **useful twice**. Written for one
project and never needed again, it belongs in that project's own
`.claude/skills/`; written once and reached for on the next project too, it
belongs here and the project keeps a copy or a symlink.

That bar is deliberate. A shared directory nobody prunes becomes a directory
nobody reads.

## What's here

- **`web-dev`** — plain PHP + vanilla JS + SQL, no framework, no build step:
  escaping, CSRF, sessions, prepared statements, POST→redirect→GET,
  progressive-enhancement AJAX. Promoted from seancheren-site on 2026-08-23,
  generalised on the way up.
- **`nearlyfreespeech`** — the specific gotchas of one host: the
  `/home/{public,protected,private}` layout, the `web` user and the file
  permissions it causes, custom php.ini, TLS, rsync deploys, scheduled tasks.
  General to the HOST rather than to any project.

The projects that use them keep a relative symlink in their own
`.claude/skills/` (seancheren-site does); a clone without AgentSuite beside it
gets dangling links, which is the honest failure.

Two skills that used to live beside them — `ios-watch-dev` and
`cross-platform-architect` — were **deleted** on 2026-08-22 with the app they
described. They are not candidates: the ideas in them are worth having again,
but the text was about a specific Xcode project that no longer exists, and
promoting stale doctrine is worse than writing it fresh.

## How a project uses one

Copy or symlink it into that project's `.claude/skills/`. There is no
propagation tooling and there may never need to be — see the TODO in
`../AGENTS.md` about whether this repo ever wants CoreMind's drift-check
discipline, or whether "copy it, it's yours now" is good enough at this scale.

A skill is a directory with a `SKILL.md` whose frontmatter carries `name` and
`description`. The description is what Claude reads to decide whether the skill
is relevant, so it is the part worth most of the effort: say when to reach for
it, not what it contains.
