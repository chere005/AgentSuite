#!/usr/bin/env bash
# Preflight: run the Release workflow in preflight mode against the commit about to be tagged, BEFORE tagging.
# Nothing it starts mails anyone (ci.md): the run it dispatches is OURS and only hands off to github-actions[bot]; the bot's
# run does the builds, with every job continue-on-error. This script waits for the bot's run and reads the real results.
#
#   tools/preflight.sh [tag]     tag is optional: blank = the workflow derives it from the version files
#
# Edit the two defaults, or set RELEASE_REPO (owner/name) and RELEASE_WORKFLOW (the workflow's FILE name, e.g. release.yml).
# Needs a clean tree and an authenticated gh. Works in Git Bash, macOS and Linux. Exit 0 PASS, 1 FAIL, 2 usage.
set -euo pipefail

REPO="${RELEASE_REPO:-OWNER/REPO}"
WORKFLOW="${RELEASE_WORKFLOW:-release.yml}"
EXPECTED_JOBS="${RELEASE_EXPECTED_JOBS_FILE:-.github/release-preflight-jobs.txt}"
tag="${1:-}"

if [ ! -s "$EXPECTED_JOBS" ]; then
  echo "preflight: missing expected-job manifest: $EXPECTED_JOBS" >&2
  exit 2
fi
if ! grep -Eq '^[^#[:space:]]' "$EXPECTED_JOBS"; then
  echo "preflight: expected-job manifest contains no job names" >&2
  exit 2
fi

if [ "$REPO" = "OWNER/REPO" ]; then
  REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "preflight: commit first, the commit is what gets checked" >&2
  exit 2
fi
sha="$(git rev-parse HEAD)"
short="$(git rev-parse --short=7 HEAD)"
branch="preflight/${short}-$(date -u +%Y%m%d%H%M%S)-${RANDOM}"
owned=false

# A branch push triggers nothing (the workflows react to tags and dispatch only). Always delete it, pass or fail.
cleanup() {
  if [ "$owned" = true ]; then
    git push -q "--force-with-lease=refs/heads/${branch}:${sha}" origin --delete "$branch" > /dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "preflight: pushing ${short} to ${branch}"
if [ -n "$(git ls-remote --heads origin "refs/heads/${branch}")" ]; then
  echo "preflight: temporary branch already exists; refusing to replace it" >&2
  exit 2
fi
git push -q "--force-with-lease=refs/heads/${branch}:" origin "HEAD:refs/heads/${branch}"
owned=true

# 120 s of slack: a local clock is rarely GitHub's (one ran 17 s ahead and the run just started was taken for an old one).
# The run is still this branch, this sha and a manual dispatch. GNU date first, BSD date as the fallback.
before="$(date -u -d '-120 seconds' +%Y-%m-%dT%H:%M:%SZ 2> /dev/null || date -u -v-120S +%Y-%m-%dT%H:%M:%SZ)"
args=(-f preflight=true)
[ -n "$tag" ] && args+=(-f "tag=${tag}")
gh workflow run "$WORKFLOW" --repo "$REPO" --ref "$branch" "${args[@]}" > /dev/null

# The dispatch above is OUR run and it only hands the work to github-actions[bot]. Wait for the bot's run of the same
# workflow file on this branch and commit. The API wants the workflow FILE name (or id), not its display name.
run=""
for _ in $(seq 1 45); do
  run="$(gh api "repos/${REPO}/actions/workflows/${WORKFLOW}/runs?head_sha=${sha}&per_page=20" \
    --jq "[.workflow_runs[] | select(.triggering_actor.login == \"github-actions[bot]\" and .head_branch == \"${branch}\" and .created_at >= \"${before}\")][0].id // empty")"
  [ -n "$run" ] && break
  sleep 4
done
if [ -z "$run" ]; then echo "preflight: the bot's run did not appear (look at https://github.com/${REPO}/actions)" >&2; exit 1; fi
echo "preflight: https://github.com/${REPO}/actions/runs/${run}"
gh run watch "$run" --repo "$REPO" --interval 20 > /dev/null 2>&1 || true

# Every job is continue-on-error, so a failed job may still report as success, so look at its steps as well.
jobs="$(gh run view "$run" --repo "$REPO" --json jobs --jq '.jobs[] | [.name, .conclusion] | @tsv')"
echo "$jobs" | sed 's/^/  /'
failed_steps="$(gh run view "$run" --repo "$REPO" --json jobs \
  --jq '.jobs[] | .name as $j | .steps[] | select(.conclusion == "failure") | "  failed: \($j) > \(.name)"')"
bad_jobs="$(echo "$jobs" | awk -F'\t' '$2 != "success" && !(($1 == "publish" || $1 == "Hand off to the bot") && $2 == "skipped") { print "  failed: " $1 " (" $2 ")" }')"
if [ -z "$jobs" ]; then bad_jobs="  failed: workflow returned no jobs"; fi
while IFS= read -r expected || [ -n "$expected" ]; do
  expected="${expected%$'\r'}"
  case "$expected" in ''|\#*) continue ;; esac
  if ! printf '%s\n' "$jobs" | cut -f1 | grep -Fxq "$expected"; then
    bad_jobs="${bad_jobs}
  failed: missing expected job: ${expected}"
  fi
done < "$EXPECTED_JOBS"
if [ -n "$failed_steps" ] || [ -n "$bad_jobs" ]; then
  echo "preflight: FAIL"
  [ -n "$bad_jobs" ] && echo "$bad_jobs"
  [ -n "$failed_steps" ] && echo "$failed_steps"
  echo "  logs: gh run view ${run} --repo ${REPO} --log-failed"
  exit 1
fi
echo "preflight: PASS (${short} may be tagged)"
