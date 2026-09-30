#!/usr/bin/env bash
# Launcher for guard.py: finds a working Python 3 (python3 is a dead Microsoft Store alias
# on many Windows machines) and fails CLOSED if none exists, so the guard can never be
# silently off. See docs/CHANGE_POLICY.md.
input=$(cat)
here=$(dirname "$0")
for py in python3 python "py -3"; do
  if $py -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
    printf '%s' "$input" | $py "$here/guard.py"
    exit 0
  fi
done
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"GUARD OFFLINE: no working Python 3.8+ found, so the prod guard could not check this call. Install Python 3 (README, setup step 1)."}}'
