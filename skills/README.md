# Shared skills

| Skill | Use for |
| --- | --- |
| [web-dev](web-dev/SKILL.md) | Plain PHP and browser JavaScript changes |
| [nearlyfreespeech](nearlyfreespeech/SKILL.md) | NearlyFreeSpeech deployment and host configuration |
| [bootstrap](bootstrap/SKILL.md) | Machine setup with the bundled bootstrap script |
| [make-deployment](make-deployment/SKILL.md) | GitHub Releases with installer builds, safe preflight, and release-lane integration |
| [electron-desktop](electron-desktop/SKILL.md) | Electron main/preload/renderer security, IPC, packaging and desktop tests (written here; no well-rated public Electron skill exists) |

Vendored from well-rated public sources, unchanged, each with `SOURCE.md` (repository and pinned commit) and its license. Re-vendor to update; do not edit in place.

| Skill | Use for | Source |
| --- | --- | --- |
| [typescript-pro](typescript-pro/SKILL.md) | TypeScript | Jeffallan/claude-skills (MIT) |
| [javascript-pro](javascript-pro/SKILL.md) | JavaScript | Jeffallan/claude-skills (MIT) |
| [react-expert](react-expert/SKILL.md) | React | Jeffallan/claude-skills (MIT) |
| [vercel-react-best-practices](vercel-react-best-practices/SKILL.md) | React performance | vercel-labs/agent-skills (MIT) |
| [ui-ux-pro-max](ui-ux-pro-max/SKILL.md) | UI/UX design, design systems, accessibility | nextlevelbuilder/ui-ux-pro-max-skill (MIT) |
| [frontend-design](frontend-design/SKILL.md) | Distinctive front-end visual design (HTML/CSS) | anthropics/skills (Apache-2.0) |
| [webapp-testing](webapp-testing/SKILL.md) | Playwright testing of web UIs | anthropics/skills (Apache-2.0) |
| [python-pro](python-pro/SKILL.md) | Python | Jeffallan/claude-skills (MIT) |
| [golang-pro](golang-pro/SKILL.md) | Go | Jeffallan/claude-skills (MIT) |
| [java-architect](java-architect/SKILL.md) | Java | Jeffallan/claude-skills (MIT) |
| [cpp-pro](cpp-pro/SKILL.md) | C and C++ (incl. CMake) | Jeffallan/claude-skills (MIT) |
| [rust-engineer](rust-engineer/SKILL.md) | Rust | Jeffallan/claude-skills (MIT) |
| [sql-pro](sql-pro/SKILL.md) | SQL | Jeffallan/claude-skills (MIT) |
| [csharp-developer](csharp-developer/SKILL.md) | C# / .NET | Jeffallan/claude-skills (MIT) |
| [devops-engineer](devops-engineer/SKILL.md) | Dockerfiles, CI, deployment | Jeffallan/claude-skills (MIT) |
| [code-documenter](code-documenter/SKILL.md) | Markdown docs, READMEs, API docs | Jeffallan/claude-skills (MIT) |
| [bash-defensive-patterns](bash-defensive-patterns/SKILL.md) | Shell scripts | wshobson/agents (MIT) |

No well-rated public skill was found for Verilog, Wolfram Language or CMake on its own; JSON, YAML, TOML and diffs need none.

Promote a skill when more than one project needs it. Keep the description specific to its trigger, essential decisions in `SKILL.md`, and conditional detail in references. Delete stale instructions rather than preserving their history in the active guidance. See [OpenAI's guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

Use [the installer](../README.md#install-or-update-a-consumer) to distribute ordinary files to Claude and Codex. Each consumer can check for drift without requiring symlinks or loading all references for every task.

When managing a skill manually, a copied skill is maintained by the adopting project; a symlink continues to use the source here.
