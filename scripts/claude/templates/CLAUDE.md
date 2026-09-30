# CLAUDE.md

This repo follows the Homesi / Simo Solutions Group change policy, which lives in the ops repo
`simo-homesi-ops`, file `docs/CHANGE_POLICY.md`.

Short version:
- Never commit or push to `main`. Branch `area/short-description` → PR → merge.
- Never deploy from a laptop (serverless / sam / cdk deploys, `aws lambda update-function-*`).
  Merging to `main` lets this repo's CI deploy.
- Secrets live in AWS Secrets Manager / GitHub secrets, never in the repo or the chat.
- `.claude/hooks/guard.py` enforces this. It is a copy installed by
  `scripts/claude/install-policy.sh` in the ops repo. Do not edit it here.
