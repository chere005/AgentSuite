# Shared skills

| Skill | Use for |
| --- | --- |
| [web-dev](web-dev/SKILL.md) | Plain PHP and browser JavaScript changes |
| [nearlyfreespeech](nearlyfreespeech/SKILL.md) | NearlyFreeSpeech deployment and host configuration |
| [bootstrap](bootstrap/SKILL.md) | Machine setup with the bundled bootstrap script |

Promote a skill when more than one project needs it. Keep the description specific to its trigger, essential decisions in `SKILL.md`, and conditional detail in references. Delete stale instructions rather than preserving their history in the active guidance. See [OpenAI's guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

Use [the installer](../README.md#install-or-update-a-consumer) to distribute ordinary files to Claude and Codex. Each consumer can check for drift without requiring symlinks or loading all references for every task.

When managing a skill manually, a copied skill is maintained by the adopting project; a symlink continues to use the source here.
