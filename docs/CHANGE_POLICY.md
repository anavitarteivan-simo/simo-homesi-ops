# Change policy — how a change reaches each system

**Owner of:** "how do I ship a change to X, and what is forbidden?" for every system this
team runs: this repo, Salesforce, the AWS Lambdas, n8n, Customer.io, BigQuery.

Applies to people and to Claude Code alike. Adopted 2026-09-30.

---

## 1. Three layers, three jobs

| Layer | What it is | Who it binds | Can it be bypassed? |
|---|---|---|---|
| **Server** | GitHub rulesets, Salesforce permissions, AWS IAM, CI | everyone | no (only by an admin changing it) |
| **Claude Code** | `.claude/hooks/guard.py` + `permissions` in `.claude/settings.json`; org-wide managed settings (§5) | Claude sessions | project hooks: yes, locally (`disableAllHooks`). Managed settings: no |
| **Docs** | this file, `CLAUDE.md` | whoever reads them | it is guidance |

Rule of thumb: **anything that must "never" happen needs the server layer or managed
settings.** Project hooks catch mistakes; they are not a security boundary.

---

## 2. Change paths per system

| System | Source of truth | The only path to prod | Forbidden | Evidence the PR must carry |
|---|---|---|---|---|
| **This repo** | `main` on GitHub | branch `area/short-description` → PR → merge | commit or push to `main`, force push, deleting `main` | diff; owning docs updated (`/sync-docs`) |
| **Salesforce** | `salesforce/` on `main` | PR → deploy + verify in `homesi-staging` → merge → `sf project deploy validate --target-org prod` → deploy to prod **from a clean, up-to-date `main`** → PR with the doc update | deploying to prod from a feature branch or with uncommitted `salesforce/` changes; relying on the default org | staging deploy Id, validate result, rollback, post-deploy check (see `/prod-preflight`) |
| **AWS Lambdas** (lambda-bridge, Encompass sync `processFile`, data-quality, refi, meta-sync) | each service's own GitHub repo | branch → PR → merge → that repo's GitHub Actions deploys | `serverless`/`sls deploy`, `sam deploy`, `cdk deploy`, `aws lambda update-function-*`, `aws cloudformation deploy` from a laptop | CI run link, deployed version/alias |
| **n8n** | the n8n instance (exports in `n8n/workflows/` are the review record) | edit draft → test → publish → re-export JSON → PR showing the diff | editing an active workflow without exporting it afterwards; touching `fur_settings.test_mode` | active `versionId` before/after, execution Id that proves it (not a pinned test) |
| **Customer.io** | the workspace | change in the UI or MCP, after confirmation | changing campaign state without explicit confirmation | dated entry in `docs/customerio/OPERATING_CONTEXT.md` |
| **BigQuery** | project `mcp-connector-procedure` | DDL/DML only after confirmation | ad-hoc DML against shared tables | the statement, in the PR or doc |

[Unverified] The Lambda repo names and GitHub orgs (`City-Lending`, `salesForceCityLendingInc`,
`HomeSi-Latino`) come from `handover/HANDOVER_2026-09-04.md` row 15; confirm ownership before
relying on their CI.

### Break-glass (production is down)

1. A **human** runs the fix from their own terminal. Claude does not bypass the guard.
2. Within the same day, add an entry to the owning doc (e.g. `borrower-followup/PROD_STATE_LOG.md`)
   saying what was run, by whom, and why.
3. Within 24 h, open a PR that brings the source of truth in line with what is live.

---

## 3. What Claude Code enforces

Implemented in `.claude/hooks/guard.py`. Every row has a test in `.claude/hooks/test_guard.py`,
which runs in CI.

| Situation | Decision |
|---|---|
| `git commit` / `merge` / `cherry-pick` / `revert` / `am` while on `main` or `master` | **deny** |
| `git push` that targets `main`/`master` (explicit refspec, `HEAD` on main, bare `git push` from main, `:main`, `--delete main`) | **deny** |
| `git push --force` / `-f` / `--force-with-lease` / `+refspec` / `--all` / `--mirror` | **deny** |
| `gh pr merge --admin` | **deny** |
| `gh pr merge`, `gh repo edit/delete/rename/archive`, write calls via `gh api` | ask |
| Local Lambda / stack deploys (see §2 row "AWS Lambdas") | **deny** |
| `aws secretsmanager get-secret-value`, `aws ssm get-parameter --with-decryption` | ask |
| Any other AWS write (`create-*`, `delete-*`, `put-*`, `update-*`, `invoke`, `s3 rm/mv/cp/sync`…) | ask |
| `sf project deploy start/quick --target-org prod` when `salesforce/` is dirty or `HEAD` ≠ `origin/main` | **deny** |
| Any other Salesforce write to prod, or with no `--target-org` | ask |
| Anything referencing `fur_settings` / `Test_Mode__c` (kill switches) | ask |
| Write-type MCP calls to prod Salesforce, n8n, Customer.io, Make, BigQuery, AWS | ask |

The guard **fails closed**. If Python is missing or the script crashes, every Bash and MCP
call asks for confirmation instead of passing silently. `guard.sh` finds a working Python 3.8+
(`python3`, `python` or `py -3`).

### Adding or changing a rule

1. Change the table above.
2. Change `guard.py` **and** add the case to `test_guard.py`; run `python .claude/hooks/test_guard.py`.
3. If it is a "never" rule, add it to `.claude/managed/managed-settings.json` too (§5).
4. Open a PR. A rule without a test is not in force.

---

## 4. What GitHub enforces (this repo)

- **Ruleset `protect-main`** on the default branch: PR required, no force push, no deletion.
  Definition: `scripts/github/ruleset-protect-main.json`; apply with
  `scripts/github/apply-ruleset.sh`. Required approvals = 0 while one person maintains the
  repo (GitHub does not let you approve your own PR); raise it to 1 when there is a second
  maintainer. **[Verified] Applied 2026-09-30** to `anavitarteivan-simo/simo-homesi-ops`
  (ruleset id `24253415`, enforcement `active`, with `--require-checks`: `guard-tests` and
  `gitleaks` must pass). An older ruleset `Developer` (`24217230`) is `disabled` and targets
  no branch. Delete it or leave it; it has no effect.
- **CI** (`.github/workflows/policy.yml`): guard tests + gitleaks on every PR.
- **`CODEOWNERS`** routes `salesforce/`, `n8n/` and `.claude/` to their owners.
- **PR template** carries the `/prod-preflight` checklist.
- Locally, `pre-commit` blocks commits to `main` (`no-commit-to-branch`) and pushes to `main`
  (`scripts/git/block-push-to-main.sh`) for people working without Claude.

Apply the same ruleset to each Lambda repo once its ownership is confirmed.

---

## 5. Other repos (Lambdas) and every machine

This repo's `.claude/` only loads when Claude Code is opened **here**. Two mechanisms cover
the rest:

1. **Managed settings** (org-wide; cannot be overridden by project, local or user settings).
   Reference file: `.claude/managed/managed-settings.json`; install steps in
   `.claude/managed/README.md`. It holds the "never" deny rules from §3.
2. **`scripts/claude/install-policy.sh <path-to-repo>`** copies the guard, its tests and a
   pointer `CLAUDE.md` into another repo, so its sessions get the same hook and link back
   here. Re-run it after changing the guard; do not hand-edit the copies.

---

## 6. History

- **2026-09-30** — [Verified] The old hook (`python3 …/guard_prod.py`) never ran on Windows
  machines where `python3` is the Microsoft Store alias (exit 49). Claude Code treats a
  non-0/non-2 exit as a non-blocking error, so every call went through unchecked; only the
  `ask` rules in `settings.json` protected prod. Replaced by `guard.sh` (finds a real Python,
  fails closed).
- **2026-09-30** — [Verified] The old MCP check matched server names `salesforce-prod`, `n8n`,
  `customerio` only. The claude.ai connectors are named e.g. `claude_ai_Salesforce_-_sObject_prod`,
  so their writes were not flagged. The new check matches by substring and treats any
  Salesforce server not named staging/sandbox as prod.
