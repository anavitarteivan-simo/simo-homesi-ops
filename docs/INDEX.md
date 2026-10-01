# Documentation index — read this first

Which file owns which truth. **When two docs disagree, the owner wins.** The project has
been bitten repeatedly by the same fact living in two places and drifting — so each fact has
exactly one home, and everything else links to it.

Migrated from the Claude Project "Salesforce" on 2026-09-28. Content is unchanged except
where noted in "Known stale content" below.

---

## Who owns what

| Question | Owner |
|---|---|
| How does a change reach each system (PRs, deploy paths), and what does the guard deny? | `CHANGE_POLICY.md` |
| What exists in prod today, under which identity, and what breaks when accounts change hands? | `handover/HANDOVER_2026-09-04.md` (live scan 2026-09-04; BigQuery 2026-09-15) |
| How is the Salesforce org built, and what will bite me? (31 numbered gotchas) | `salesforce/ORG_REFERENCE.md` |
| Every flow, validation / sharing / duplicate rule, trigger and scheduled job in the org (regenerated 2026-09-29) | `salesforce/AUTOMATION_INVENTORY.md` |
| What does field X mean? | `salesforce/DATA_DICTIONARY.md` |
| How is the n8n engine built, and what will bite me? | `n8n/ENGINE_REFERENCE.md` (§0 environment, §2 gotchas) |
| Customer.io workspaces, segments, sync, gotchas | `customerio/OPERATING_CONTEXT.md` |

### Borrower Follow-Up (FUR) system

| Question | Owner |
|---|---|
| What was it meant to do? Decisions marked "DECIDED \<date\>" are final. | `borrower-followup/DESIGN_SPEC.md` |
| What is deployed to prod, with prod Ids? | `borrower-followup/PROD_STATE_LOG.md` |
| Is it wrong today, in any environment? | `borrower-followup/OPEN_DEFECTS.md` |
| Has it been proven — and was the proof LIVE or PINNED? | `borrower-followup/TEST_EVIDENCE.md` |
| What must still happen before agents use it? | `borrower-followup/REMAINING_CUTOVER.md` |
| Every email the system sends, verbatim | `borrower-followup/EMAIL_INVENTORY.md` |
| What agents see (end-user manual, v11) | `borrower-followup/AGENT_GUIDE.md` |

### Other work in the same org

| Topic | File |
|---|---|
| 2-day Opportunity-save outage — why entry criteria must use `RecordTypeId` | `salesforce/PROD_OUTAGE_RCA_2DAY.md` |
| Who can own a Contact, how Contacts are created / converted, and what does (not) stop duplicates (2026-10-01) | `salesforce/CONTACT_OWNERSHIP_AND_DEDUP.md` |
| B2B Opportunity duplicate guard, rules A + B (design only, awaiting Business Owner, 2026-10-01) | `salesforce/B2B_OPP_DUPLICATE_GUARD_DESIGN.md` |
| Lead imports (Data Import Wizard) | `salesforce/LEAD_IMPORT.md` |
| Recruitment copilot (MMI + NMLS) | `salesforce/RECRUITMENT_COPILOT.md` |
| Latino name likelihood | `salesforce/LATINO_NAME_RUNBOOK.md` |
| SiMo BPO record type + reply-gated lead capture (design only) | `simo-bpo/DESIGN.md` |
| Lead email engagement score (design only) | `customerio/EMAIL_ENGAGEMENT_DESIGN.md` |
| Customer.io → Salesforce subscription redesign (executed 2026-05-21) | `customerio/SUBSCRIPTION_REDESIGN.md` |
| Customer.io SimoSolutions workspace replication spec | `customerio/SIMO_WORKSPACE_REPLICATION.md` |
| BigQuery analytics agent system prompt | `bigquery/AGENT_PROMPT.md` |
| LOA1 / LOA2 First Touch playbook (human process) | `playbooks/LOA_PLAYBOOK.md` |

---

## Old names → new paths

Older docs reference files by their previous names. Use this table to resolve them.

| Referenced as | Now at |
|---|---|
| `CLAUDE.md` (Salesforce Workspace), `01_SALESFORCE_ORG_CLAUDE.md`, `CLAUDE-Salesforce.md` | `salesforce/ORG_REFERENCE.md` |
| `CLAUDE.md` (Claude Make and N8N), `02_N8N_ENGINE_CLAUDE.md` | `n8n/ENGINE_REFERENCE.md` |
| `CLAUDE.md` (CIO Workspace / Salesforce + Customer.io) | `customerio/OPERATING_CONTEXT.md` |
| `Borrower_FollowUp_System_Design.md`, `03_DESIGN_SPEC.md` | `borrower-followup/DESIGN_SPEC.md` |
| `PROD_Cutover_LOG_2026-08-21.md`, `05_PROD_STATE_LOG.md` | `borrower-followup/PROD_STATE_LOG.md` |
| `FUR_Bucket_2_3_Checklist.md`, `06_OPEN_DEFECTS.md` | `borrower-followup/OPEN_DEFECTS.md` |
| `FUR_Branch_Coverage_Report.md`, `07_TEST_EVIDENCE.md` | `borrower-followup/TEST_EVIDENCE.md` |
| `PROD_Cutover_Checklist.md`, `08_REMAINING_CUTOVER.md` | `borrower-followup/REMAINING_CUTOVER.md` |
| `Borrower_FollowUp_Agent_Guide*.docx`, `09b_AGENT_GUIDE_v11_LATEST.docx` | `borrower-followup/AGENT_GUIDE.md` |
| `FUR_START_HERE.md`, `04_START_HERE_INDEX.md` | this file |

---

## Known stale content — fix as you touch these files

- **"Nothing is in prod" is false.** `borrower-followup/DESIGN_SPEC.md` §0 and
  `borrower-followup/REMAINING_CUTOVER.md` still say so. Per the handover (2026-09-04): FUR
  Salesforce metadata is in prod and all n8n workflows are bound to prod, but WF-1, WF-2 and
  WF-5 were never published, the Inbound Dispatcher is off, and `fur_settings.test_mode = true`.
  **Deployed, not live.**
- `salesforce/ORG_REFERENCE.md` is the Project copy (~2026-08-25). The laptop original
  (`Salesforce Workspace/CLAUDE.md`, 224 KB, 2026-08-27) is newer — replace this file with it
  if you can get it, and commit the diff.
- `n8n/ENGINE_REFERENCE.md`: same situation (`Claude Make and N8N/CLAUDE.md`, 2026-08-27).
- `borrower-followup/AGENT_GUIDE.md` and `playbooks/LOA_PLAYBOOK.md` are text-only: the
  screenshots were not in the Project copies.
- The previous index recorded "the cadence engine has never run on its own schedule" — every
  FUR proof is a manual run. Still true unless `TEST_EVIDENCE.md` says otherwise.

## Sensitivity

`handover/HANDOVER_2026-09-04.md` lists identities, account numbers and known security
weaknesses. AWS access-key IDs are masked (`AKIAWOMO************`). Keep this repo private.
