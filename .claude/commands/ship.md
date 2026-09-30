---
description: Ship the current changes as a branch + PR (never straight to main)
---
Ship these changes following `docs/CHANGE_POLICY.md`: $ARGUMENTS

1. `git status` and `git diff`. Say which systems the change touches (docs only, Salesforce,
   n8n, a Lambda repo...). If it touches a live system, run `/prod-preflight` first and stop
   if it is not satisfied.
2. Scan the diff for secrets and borrower/realtor PII. Stop if you find any.
3. If on `main`, create a branch `area/short-description` (areas: `salesforce`, `n8n`,
   `customerio`, `bigquery`, `docs`, `reports`, `repo`, `scripts`). Never commit on `main`.
4. Make sure the owning docs are updated (`/sync-docs`) in the same PR.
5. Commit with `area: what changed` and the attribution trailer.
6. Show me the commit and the PR title/body (filled from `.github/pull_request_template.md`),
   then wait for my go-ahead.
7. On go-ahead: `git push -u origin <branch>` and `gh pr create`. Report the PR URL.
   Do not merge. Merging is a separate, confirmed step.
