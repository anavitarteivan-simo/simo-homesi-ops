#!/usr/bin/env bash
# pre-push hook (via pre-commit): refuse pushes to main/master. docs/CHANGE_POLICY.md §2.
case "${PRE_COMMIT_REMOTE_BRANCH:-}" in
  refs/heads/main|refs/heads/master)
    echo "Direct push to ${PRE_COMMIT_REMOTE_BRANCH#refs/heads/} is not allowed. Push a branch and open a PR." >&2
    exit 1 ;;
esac
exit 0
