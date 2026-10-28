#!/usr/bin/env bash
# Write the test report into the check of the current job (create-check-run: job).
#
# A check run created through the Checks API is filed by GitHub into some check suite of the commit, so with several
# workflows on one commit it can show up under the wrong workflow. The current job's own check always belongs to its
# workflow run; its id is the job id, found by run, attempt and runner name.
#
# Environment: SUMMARY (markdown file), TITLE, GH_TOKEN, plus the GitHub defaults GITHUB_REPOSITORY, GITHUB_RUN_ID,
# GITHUB_RUN_ATTEMPT, RUNNER_NAME, GITHUB_SERVER_URL.
# Never fails the job: a missing permission or API error only results in a warning.
set -euo pipefail

# check run output summaries are limited to 65535 characters
MAX_CHARS=65000

if ! jobs=$(gh api --paginate "repos/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID/attempts/$GITHUB_RUN_ATTEMPT/jobs"); then
  echo "::warning::cannot list the jobs of this run (needs 'actions: read'); the job check keeps its default output"
  exit 0
fi
id=$(jq -r --arg runner "$RUNNER_NAME" '.jobs[] | select(.status == "in_progress" and .runner_name == $runner) | .id' \
  <<< "$jobs" | head -n 1)
if [[ -z "$id" ]]; then
  echo "::warning::cannot identify the check of this job; it keeps its default output"
  exit 0
fi

summary=$(mktemp)
cp "$SUMMARY" "$summary"
if (( $(wc -m < "$summary") > MAX_CHARS )); then
  run_url="$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"
  { sed '/^## /,$d' "$SUMMARY"; echo "_The full report is too long for a check, see the [run]($run_url)._"; } > "$summary"
fi

payload=$(jq -n --arg title "$TITLE" --rawfile summary "$summary" '{output: {title: $title, summary: $summary}}')
if gh api -X PATCH "repos/$GITHUB_REPOSITORY/check-runs/$id" --input - <<< "$payload" > /dev/null; then
  echo "test report written into the check of this job ($id)"
else
  echo "::warning::cannot update the check of this job (needs 'checks: write'); it keeps its default output"
fi
