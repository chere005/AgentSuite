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
| [vercel-react-best-practices](vercel-react-best-practices/SKILL.md) | React performance | vercel-labs/agent-skills (MIT) |
| [frontend-design](frontend-design/SKILL.md) | Distinctive front-end visual design (HTML/CSS) | anthropics/skills (Apache-2.0) |
| [webapp-testing](webapp-testing/SKILL.md) | Playwright testing of web UIs | anthropics/skills (Apache-2.0) |

Promote a skill when more than one project needs it. Keep the description specific to its trigger, essential decisions in `SKILL.md`, and conditional detail in references. Delete stale instructions rather than preserving their history in the active guidance. See [OpenAI's guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

Use [the installer](../README.md#install-or-update-a-consumer) to distribute ordinary files to Claude and Codex. Each consumer can check for drift without requiring symlinks or loading all references for every task.

When managing a skill manually, a copied skill is maintained by the adopting project; a symlink continues to use the source here.
