#!/usr/bin/env bash
# Install the change-policy guard into another repo (e.g. a Lambda service repo).
# docs/CHANGE_POLICY.md §5. Usage: scripts/claude/install-policy.sh <path-to-repo>
#
# - Always (re)copies guard.sh, guard.py, test_guard.py into <repo>/.claude/hooks/.
# - Creates <repo>/.claude/settings.json and <repo>/CLAUDE.md only if they do not exist;
#   otherwise prints what to merge by hand. Never overwrites them.
# Commit the result in that repo through a PR.
set -euo pipefail
dest=${1:?usage: install-policy.sh <path-to-repo>}
[[ -d "$dest/.git" ]] || { echo "$dest is not a git repo root" >&2; exit 1; }
src=$(cd "$(dirname "$0")/../.." && pwd)
tpl="$src/scripts/claude/templates"
rev=$(git -C "$src" rev-parse --short HEAD)

mkdir -p "$dest/.claude/hooks"
for f in guard.sh guard.py test_guard.py; do
  cp "$src/.claude/hooks/$f" "$dest/.claude/hooks/$f"
done
chmod +x "$dest/.claude/hooks/guard.sh"
echo "copied guard (simo-homesi-ops@$rev) -> $dest/.claude/hooks/"

if [[ -e "$dest/.claude/settings.json" ]]; then
  echo "KEEP: $dest/.claude/settings.json exists. Merge the hooks + deny rules from:"
  echo "      $tpl/settings.json"
else
  cp "$tpl/settings.json" "$dest/.claude/settings.json"
  echo "created $dest/.claude/settings.json"
fi

if [[ -e "$dest/CLAUDE.md" ]]; then
  echo "KEEP: $dest/CLAUDE.md exists. Add the policy pointer from: $tpl/CLAUDE.md"
else
  cp "$tpl/CLAUDE.md" "$dest/CLAUDE.md"
  echo "created $dest/CLAUDE.md"
fi

for py in python3 python "py -3"; do
  if $py -c "import sys" >/dev/null 2>&1; then
    $py "$dest/.claude/hooks/test_guard.py" >/dev/null 2>&1 \
      && { echo "guard tests pass in $dest"; exit 0; } \
      || { echo "guard tests FAILED in $dest" >&2; exit 1; }
  fi
done
echo "WARNING: no Python found; guard tests not run" >&2
