# Quiet CI

A GitHub Actions run that a person triggers and that ends red or cancelled sends that person an email. Every repo here
used to mail Sean for runner shortages, flaky smoke tests, timeouts and the odd real failure. Preflight could not stop
those mails. It checked the commit before the tag, but the tag's own run could still fail on anything nondeterministic:
the macOS runner GitHub never provided (ChefMind 1.32.0), Xvfb not ready in time (CalMind 1.49.0), a notarization staple
that lost its connection, a slow cold test. `continue-on-error` does not help either. It covers a failed job, not a
cancelled one, and a timeout or a runner that never arrives is a cancellation.

The contract therefore removes the person from the run that does the work:

1. **A person's run only hands off.** Every workflow has a `handoff` job (`if: github.triggering_actor !=
   'github-actions[bot]'`, ubuntu, about ten seconds). It re-dispatches the same workflow, at the same ref and with the
   same inputs, using `GITHUB_TOKEN`. That new run belongs to `github-actions[bot]`. GitHub mails a run's outcome to
   whoever triggered it, so whatever happens in the bot's run mails nobody. A tag push, `gh workflow run`, a preflight
   dispatch and a re-run all take this path.
2. **Every real job runs only in the bot's run.** It has `if: github.triggering_actor == 'github-actions[bot]'`, or it
   `needs` such a job and uses no `always()`, `failure()` or `cancelled()` without that check.
3. **Every job is `continue-on-error: true`**, literally. The bot's run stays green, and scripts read each job's and
   step's conclusion. A green run can contain failed jobs.
4. **Nothing is cancelled for us.** Never set `cancel-in-progress: true`, and never `gh run cancel` from a script. A handoff run gets a concurrency group of its
   own (`format('handoff-{0}', github.run_id)`) so it never waits behind, or gets cancelled by, the bot's run.
5. **Only `push`, `workflow_dispatch` and `workflow_call` triggers.** A `schedule` mails the workflow's author, and a
   `pull_request` run cannot hand off. Every workflow keeps `workflow_dispatch`, because the handoff needs it.
6. **Every job has `timeout-minutes`.** Never use `actions/upload-artifact` or `download-artifact`: the account's artifact
   quota fills and then every run fails.
7. **Retry by dispatching, never `gh run rerun`.** A re-run is triggered by you, so its bot-only jobs skip. Use
   `gh workflow run <file> --ref <ref> -f ...` instead; its handoff passes the run to the bot.

Release workflows also retry themselves. When `publish` finds a platform missing, it dispatches the workflow again for
the same tag with `attempt=N+1`, up to three runs. `prepare` builds only the platforms whose files are not on the draft.
After the third run the draft stays, and the lanes report it: tdtp follows the release to the end, and every lane run
starts with `tools/gh-bot.sh last-release`, which warns about an unpublished last release. No email is involved.

## Checking it

```sh
python3 ~/GIT/AgentSuite/tools/check-workflows.py .        # in a repo; exit 1 lists every violation
git config core.hooksPath ../AgentSuite/githooks           # once per checkout: pre-push runs the check
```

The check reads `.github/workflows/*.yml` with PyYAML or Ruby's YAML. It also flags `gh run rerun` and `gh run cancel` in tracked scripts.
A repo with hooks of its own, such as AgentTeam's `.githooks/pre-push`, calls the checker from that hook.

## Finding the bot's run

The run your dispatch or push creates is not the one that builds. Look up the bot's run of the same workflow at the same
commit and ref:

```sh
gh api "repos/OWNER/REPO/actions/workflows/release.yml/runs?head_sha=$SHA" \
  --jq '.workflow_runs[] | select(.triggering_actor.login == "github-actions[bot]") | [.id, .head_branch, .status] | @tsv'
```

The Mind-suite repos carry `tools/gh-bot.sh` (CoreMind canon) for this: `run` finds a preflight's bot run, `release <tag>`
follows a release until it is published or no run is left, and `last-release` gives the lane's start-of-run warning.
New pipelines start from the [make-deployment](skills/make-deployment/SKILL.md) templates, which already follow this
contract.
