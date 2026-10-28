#!/usr/bin/env bash
# Post the test report as a pull request comment, or update the comment of an earlier run.
#
# Environment: SUMMARY (markdown file), MARKER (hidden HTML comment identifying the comment, unique per workflow
# and check name), PR (number), HEAD_REPO (owner/name of the PR head), WORKFLOW, RUN_URL, GH_TOKEN, plus the
# GitHub defaults GITHUB_REPOSITORY and GITHUB_RUN_NUMBER.
# Never fails the job: a missing permission or API error only results in a warning.
set -euo pipefail

# comments larger than this are rejected by GitHub (limit 65536 characters)
MAX_CHARS=65000

if [[ "$HEAD_REPO" != "$GITHUB_REPOSITORY" ]]; then
  echo "::notice::pull request from a fork ($HEAD_REPO): its token is read-only, no comment"
  exit 0
fi

body=$(mktemp)
header() {
  echo "$MARKER"
  echo "**$WORKFLOW** · [run #$GITHUB_RUN_NUMBER]($RUN_URL)"
  echo
}
{ header; cat "$SUMMARY"; } > "$body"
if (( $(wc -m < "$body") > MAX_CHARS )); then
  # overview table only: everything before the first category section
  { header; sed '/^## /,$d' "$SUMMARY"; echo "_The full report is too long for a comment, see the [run]($RUN_URL)._"; } > "$body"
fi

# the comment of an earlier run of this workflow carries the same marker
if ! comments=$(gh api --paginate "repos/$GITHUB_REPOSITORY/issues/$PR/comments"); then
  echo "::warning::cannot read the comments of pull request #$PR (needs 'pull-requests: write'); no comment"
  exit 0
fi
id=$(jq -r --arg marker "$MARKER" '.[] | select(.body | contains($marker)) | .id' <<< "$comments" | tail -n 1)

if [[ -n "$id" ]]; then
  gh api -X PATCH "repos/$GITHUB_REPOSITORY/issues/comments/$id" -F "body=@$body" > /dev/null &&
    echo "updated comment $id on pull request #$PR" ||
    echo "::warning::cannot update comment $id on pull request #$PR (needs 'pull-requests: write')"
else
  gh api -X POST "repos/$GITHUB_REPOSITORY/issues/$PR/comments" -F "body=@$body" > /dev/null &&
    echo "commented on pull request #$PR" ||
    echo "::warning::cannot comment on pull request #$PR (needs 'pull-requests: write')"
fi
