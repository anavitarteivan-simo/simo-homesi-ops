#!/usr/bin/env bash
# Create or update the "protect-main" ruleset on a GitHub repo (docs/CHANGE_POLICY.md §4).
# Usage: scripts/github/apply-ruleset.sh [owner/repo] [--require-checks]
#   --require-checks  also require the "guard-tests" and "gitleaks" CI checks
#                     (only for repos that have .github/workflows/policy.yml).
set -euo pipefail
repo=${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
here=$(cd "$(dirname "$0")" && pwd)
body=$(cat "$here/ruleset-protect-main.json")
if [[ "${2:-}" == "--require-checks" ]]; then
  body=$(printf '%s' "$body" | python -c '
import json, sys
r = json.load(sys.stdin)
r["rules"].append({"type": "required_status_checks", "parameters": {
    "strict_required_status_checks_policy": False,
    "required_status_checks": [{"context": "guard-tests"}, {"context": "gitleaks"}]}})
print(json.dumps(r))')
fi
id=$(gh api "repos/$repo/rulesets" --jq '.[] | select(.name=="protect-main") | .id' || true)
if [[ -n "$id" ]]; then
  printf '%s' "$body" | gh api -X PUT "repos/$repo/rulesets/$id" --input - --jq '.name + " updated, enforcement=" + .enforcement'
else
  printf '%s' "$body" | gh api -X POST "repos/$repo/rulesets" --input - --jq '.name + " created, enforcement=" + .enforcement'
fi
