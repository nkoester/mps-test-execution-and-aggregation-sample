#!/usr/bin/env bash
# Publish the combined test results of a successful release build (called by nightly.yml).
#
# Usage: publish_test_results.sh <package.zip> <version> <results-dir>
#   package.zip  all-test-results as one zip (top level: index.html of the aggregated Ant report,
#                TESTS-TestSuites.xml, one test-results-<category>-<run>/ folder per run)
#   version      e.g. nightly-20261028-42
#   results-dir  the same content unpacked, e.g. to deploy the HTML report as a website
#
# Hook for the publishing target: replace the body below, e.g. with a push to a gh-pages branch, an upload to a
# release (gh release upload) or to a binary repository. Credentials come from repository secrets passed as env.
set -euo pipefail

package=$1
version=$2
results=$3

echo "::notice::no publishing target configured: $package ($version) is not published"
{
  echo "## Test results not published"
  echo
  echo "\`$(basename "$package")\` ($(du -h "$package" | cut -f1)) would be published as \`$version\`."
  echo "Configure the target in \`.github/scripts/publish_test_results.sh\`."
} >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"
test -d "$results"
