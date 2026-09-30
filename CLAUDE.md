# CLAUDE.md — simo-homesi-ops

Operations repo for **Homesi / Simo Solutions Group**: Salesforce org, n8n automation,
Customer.io, BigQuery, and the docs that keep them running. This file loads in every
session, so it stays short. Detail lives in `docs/` — read it on demand.

**Start every non-trivial task by reading `docs/INDEX.md`.** It says which document owns
which truth. When two documents disagree, the owning one wins — say so out loud rather
than silently picking one.

---

## 1. Systems and environments

| System | Prod | Non-prod |
|---|---|---|
| Salesforce | alias `prod` — org `00DKb000000OvoRMAS`, `ruby-ruby-7485.my.salesforce.com` | alias `homesi-staging` — org `00DEm000008XXK7MAO` |
| n8n Cloud | `https://simosolutionsgroup.app.n8n.cloud` (all FUR workflows are bound to **prod**) | — |
| Customer.io | workspace `164380` (Homesí / Supreme Lending), `224311` (Simo Solutions Group) | — |
| BigQuery | project `mcp-connector-procedure` | — |

- **The default Salesforce `target-org` is `homesi-staging`. Never rely on it.** Always pass
  `--target-org prod` or `--target-org homesi-staging` explicitly on every `sf` command.
- Two Salesforce MCP servers may be mounted (`salesforce-prod`, `salesforce-staging`). Call
  `getUserInfo` first; the one returning `companyName: "Homesi"` is prod.
- Always state which org / workspace a finding came from.

## 2. Safety rules (non-negotiable)

1. **Prefer reads.** Any write, deploy, delete, merge, publish, or campaign state change in a
   prod system needs explicit confirmation. A hook (`.claude/hooks/guard.py`) enforces a
   prompt; do not try to route around it.
2. **Two kill switches — never change either without an explicit instruction:**
   - n8n Data Table `fur_settings` (`0A0KbAfzHmAHvhCl`) → `test_mode` = **true**. Redirects every
     borrower email to a test inbox.
   - Salesforce `Notification_Settings__c` org default (`a1RQg000005WcIbMAK`) → `Test_Mode__c`.
3. **Deploy to `homesi-staging` first**, then prod. Flows deploy in two phases (create version,
   then activate). See gotchas #21–#30 in `docs/salesforce/ORG_REFERENCE.md` before any deploy.
4. **Record-triggered flow entry criteria filter on `RecordTypeId` + the Id — never
   `RecordType.DeveloperName`.** This caused a 2-day prod outage
   (`docs/salesforce/PROD_OUTAGE_RCA_2DAY.md`).
5. **Do not repoint any mailbox** (n8n senders/recipients) without explicit instruction.
6. **Every change ships through a PR — never commit or push to `main`, never deploy a Lambda
   from a laptop, deploy Salesforce prod only from merged `main`.** Per-system paths and what
   the guard denies: `docs/CHANGE_POLICY.md`. Use `/ship` to open the PR.

## 3. Verification rules (each one has caused real damage here)

1. **A "fixed" claim is worthless unless the raw metadata/JSON was re-read after the write** —
   in the *active* version, not the draft. Write tools report success even when the change
   landed in a dead nested copy.
2. **A pinned n8n test never validates a query, a credential, or a send** — only
   transformation logic.
3. **A deploy's `created: true|false` is the only authoritative check that a Salesforce field
   exists.** `FieldDefinition` and `SELECT` both hide fields the running user has no FLS on.
4. **Editing an active n8n workflow creates a draft.** The running version keeps old values
   until it is published and the version IDs match.
5. **This system fails silently, not loudly.** Most bugs here produced a green execution.
   Verify the outcome in Salesforce rather than trusting a success status.
6. "The API returned zero" is not "there is nothing there." Re-read counts and IDs before
   acting on them; other people change these systems mid-session.

Tag claims: **[Verified]** read live this session · **[Likely]** strong inference ·
**[Unverified]** assumption to re-check.

## 4. Keep the docs true

This repo replaces a Claude Project whose biggest problem was stale documents. After any
change to a live system, update the owning doc **in the same session** (see `docs/INDEX.md`):

- what is live in prod → `docs/borrower-followup/PROD_STATE_LOG.md` (FUR) or the relevant
  system reference
- what is broken / unbuilt → `docs/borrower-followup/OPEN_DEFECTS.md`
- what is proven → `docs/borrower-followup/TEST_EVIDENCE.md`
- a new gotcha → append it, numbered, to the system's reference doc

Date every entry (`YYYY-MM-DD`). Never keep a second copy of a doc — link to it. Superseded
versions are deleted; git history keeps them.

## 5. Secrets and PII

- Secrets live only in `.env` (git-ignored) and in the `sf` CLI's own auth store. **Never read
  `.env`**, never print a token, never write a secret into any tracked file, commit message,
  or doc. Reference variables by name (`$N8N_API_KEY`).
- **No borrower or realtor PII in the repo.** Lead-import CSV/XLSX, FHA binders, eFolders and
  exports go in `data/` (git-ignored) or stay outside the repo. Do not paste real borrower
  data into docs — use record Ids.
- If a secret ever lands in a commit, stop and tell the user: it must be **rotated**;
  rewriting history is not enough.

## 6. Repo layout

```
docs/          all reference docs — start at docs/INDEX.md
salesforce/    SFDX project (run sf commands from here) — has its own CLAUDE.md
n8n/           exported workflow JSON + export script — has its own CLAUDE.md
data/          local-only working files (git-ignored, may hold PII)
reports/       dated PDF reports for people (+ src/ HTML) — conventions in reports/README.md
.github/       PR template, CODEOWNERS, CI (guard tests + gitleaks)
scripts/       repeatable tooling, by system (e.g. scripts/salesforce/automation-inventory/ regenerates AUTOMATION_INVENTORY.md)
.claude/       settings, prod-guard hook, commands, skills
```

## 7. Working style

- Answer the user in **Spanish**; write code, commits and docs in **English**.
- Small, reviewable changes. Show the diff or the exact command before anything touches prod.
- Commit messages: `area: what changed` (e.g. `salesforce: add FLS for Preferred_Language__c`).
