# Customer.io Task storage — reduction plan

**Status:** PLAN, not executed. Drafted 2026-09-30.
**Goal:** stop Salesforce Data Storage from filling up. Customer.io email-event Tasks are the
main consumer.
**Covers:** (1) stop writing "Email Sent" Tasks; (3) archive, then hard-delete, the existing
Customer.io Tasks.
**Change path:** `docs/CHANGE_POLICY.md`. Every prod step below needs explicit confirmation
and a `/prod-preflight`.

---

## 0. Facts this plan rests on

All read live from Salesforce **prod** (`00DKb000000OvoRMAS`) on 2026-09-30 unless noted.

| Fact | Value | Tag |
|---|---|---|
| Data Storage used | **9,763 / 11,800 MB (82.7%)**, 2,037 MB free (the 2026-09 audit read 9,463 MB) | [Verified] |
| Tasks in the org | 3,280,335 (≈ 6.4 GB at 2 KB each, ≈ 66% of used storage) | [Verified] |
| Tasks created by `sf integrations` (`005Qg00000C9srvIAB`) | 2,511,244 | [Verified] |
| … of which Customer.io email events (`OwnerId = 005Kb00000B1ZEtIAN` "Team Marketing city", `Subtype__c LIKE 'Email%'`) | **2,506,092 ≈ 4,900 MB ≈ 50% of used storage** | [Verified] |
| Split by `Subtype__c` | Email Sent **1,941,498** · Opened 368,555 · Link Clicked 120,706 · Failed 66,477 · Unsubscribed 8,696 · Marked as Spam 161 | [Verified] |
| Status of those Tasks | **all `Open`**, none archived. Open activities are never auto-archived, and they do not feed `Lead.LastActivityDate`, which counts only closed Tasks and Events | [Verified] / [Likely] |
| Growth (all `sf integrations` Tasks) | Jul 253,521 · Aug 327,808 · Sep 296,284 per month ≈ **600 MB/month** | [Verified] |
| Projection if nothing changes | storage full **mid-Dec 2026 – Jan 2027**. When full, Salesforce rejects inserts of new Leads, Opportunities and Tasks, and the automations that create them | [Likely] |
| Writers | Customer.io destination **`52375`** in workspace **164380** (subs `182232` Email Sent/Lead, `712640` Email Sent/Opp, + 12 others) and destination **`344289`** in workspace **224311**, which mirrors the same 14 subscriptions | [Verified] from `SUBSCRIPTION_REDESIGN.md` §9 and `handover/HANDOVER_2026-09-04.md`. Not re-read live: the Customer.io MCP was not authenticated this session |
| Recycle Bin | Items in the Recycle Bin do **not** count against storage (Salesforce docs). Soft-deleted items stay 15 days | [Likely] (docs, not tested here) |
| Hard delete | Needs the **Bulk API Hard Delete** permission. Neither `sf integrations` nor `Ivan Anavitarte` (`005Qg00000Vs3DaIAJ`) has it today | [Verified] |
| BigQuery `salesforce.Task` | **Not an archive.** The Data Transfer Service does a daily **full refresh**, so rows deleted in Salesforce disappear from BigQuery the next day. It also held only 2.72 M rows vs 3.28 M in Salesforce (2026-09-15) | [Verified] from the handover. Row gap unexplained |

### What depends on these Tasks

| Consumer | Uses Customer.io Tasks? | Impact of the plan |
|---|---|---|
| Flow `Notify_Task_EmailOpened_Status` | Only `Subtype__c = 'Email Unsubscribed'` → sets `Lead.HasOptedOutOfEmail` | None: Unsubscribed keeps being written. [Verified] active metadata |
| Flow `Update_Lead_Status_When_Task_Created` | Any new Task on a Lead: if Lead `Status = New` **and** `Lead.OwnerId = Task.CreatedById`, sets Status = Working | Customer.io Tasks are created by `sf integrations`, so they flip New Leads **owned by `sf integrations`** to Working. Only **106** such Leads are New today. After Phase 1, "Email Sent" no longer flips them; Opened/Clicked still do. Decide if that side effect was intended (D4). [Verified] |
| Flow `Assign_subtype_to_tasks` | Fills `Subtype__c` from the Subject on every new Task | Fewer executions. No functional impact |
| Flow `First_Touch_with_Tasks` | Skips admin profiles (`sf integrations` is System Administrator) | None. [Verified] |
| Other Task flows (SLA, Call, Zoom) | Filter on Call / SMS / `Touch_Type__c` | None. [Likely] |
| BigQuery views `calls_summary`, `fct_calls_daily` | Read `salesforce.Task`, but for calls | None expected. [Likely]. Re-check every view that reads `salesforce.Task` before Phase 3 (step 3.1) |
| `EMAIL_ENGAGEMENT_DESIGN.md` (engagement score) | Design only; uses Sent as the "base signal" and recommends scoring Opened + Clicked only | Sent counts would have to come from Customer.io, not Salesforce. Not built, so nothing breaks |
| Salesforce reports / list views on Task | Unknown | Check in step 1.1 |

---

## 1. Decisions needed before starting

| # | Decision | Recommendation |
|---|---|---|
| D1 | Stop "Email Sent" Tasks in **both** workspaces (164380 and 224311), for Leads and Opportunities (4 subscriptions)? | Yes. They are 77% of volume and the least informative event |
| D2 | What to delete in Phase 3 | **All** Customer.io "Email Sent" Tasks (writing has stopped, archive exists). For Opened / Clicked / Failed / Spam: those older than **12 months**. Keep all Unsubscribed (consent evidence) |
| D3 | Where the archive lives | A new BigQuery dataset `salesforce_archive` (not touched by the transfer). Needs a dataset owner. Today every BigQuery right belongs to `simologic.com` accounts (handover row 19). Fallback: private, encrypted S3 bucket |
| D4 | Keep the "Customer.io Task → Lead Working" side effect for Leads owned by `sf integrations`? | Probably unintended; confirm with the Lead owners. Not blocking |
| D5 | Who runs Phase 3 and in which window | One named admin, off-hours (after 20:00 ET), not during the BigQuery transfer (~05:02 UTC) |

---

## Phase 1 — stop writing "Email Sent" Tasks

**Recovers:** nothing. **Slows growth:** from ≈600 MB to roughly 140 MB/month [Likely], which
moves "storage full" out by more than a year.
**Systems:** Customer.io only. No Salesforce change. **No staging path:** both destinations
point at prod.

### 1.1 Pre-checks (read-only)
1. Authenticate the Customer.io MCP. Re-read live:
   `GET /cdp/api/workspaces/164380/destinations/52375/subscriptions` and
   `GET /cdp/api/workspaces/224311/destinations/344289/subscriptions`.
   Record the id, `subscribe` trigger and `enabled` of each "Email Sent" subscription
   (expected in 164380: `182232`, `712640`; in 224311: ids to be recorded).
2. Baseline in Salesforce prod:
   ```sql
   SELECT COUNT() FROM Task
   WHERE CreatedById = '005Qg00000C9srvIAB' AND OwnerId = '005Kb00000B1ZEtIAN'
     AND Subtype__c = 'Email Sent' AND CreatedDate = LAST_N_DAYS:1
   ```
   Repeat for `Email Opened`. Record the counts and `sf org list limits --target-org prod` (DataStorageMB).
3. Search Salesforce reports and dashboards that filter on Task `Subtype__c` / "Email Sent"
   (Setup → Reports, filter by Tasks and Events report type). List any owner who must be told.

### 1.2 Change (needs confirmation)
- **Disable, do not delete** the 4 "Email Sent" subscriptions (2 per workspace). Leave the
  other 10 per workspace untouched.
- Change one workspace first (164380, the larger one), check 1.3, then 224311.

### 1.3 Verify
- After 2 h and after 24 h, re-run the 1.1 query. "Email Sent" must be **0** for new
  records; "Email Opened" must continue at its usual rate.
- Re-read both subscription lists: the 4 are `enabled: false`, the rest unchanged.
- Customer.io destination error count unchanged.

### 1.4 Rollback
Re-enable the subscriptions. [Unverified] Events that happen while a subscription is disabled
are probably **not** replayed afterwards. That gap is acceptable.

### 1.5 Docs (same day)
`SUBSCRIPTION_REDESIGN.md` §9 (as-built), `OPERATING_CONTEXT.md` (dated entry),
`SIMO_WORKSPACE_REPLICATION.md` §4, a note in `EMAIL_ENGAGEMENT_DESIGN.md`.

---

## Phase 2 — archive the Customer.io Tasks

**Must finish and be verified before Phase 3.** Hard delete is irreversible; the archive is
the only rollback.

### 2.1 Scope query (the single definition used in Phases 2 and 3)
```sql
SELECT Id, WhoId, WhatId, Subject, Subtype__c, TaskSubtype, Status, ActivityDate,
       Description, OwnerId, CreatedById, CreatedDate, LastModifiedDate
FROM Task
WHERE CreatedById = '005Qg00000C9srvIAB'
  AND OwnerId     = '005Kb00000B1ZEtIAN'
  AND Subtype__c IN ('Email Sent','Email Opened','Email Link Clicked',
                     'Email Failed','Email Unsubscribed','Email Marked as Spam')
```
Archive **all 2.5 M** rows (not only those to be deleted), so a single export covers every D2
choice.

### 2.2 Export (read-only in Salesforce)
```bash
sf data export bulk --target-org prod --result-format csv --wait 60 \
  --query-file scripts/salesforce/cio-task-cleanup/scope.soql \
  --output-file data/cio_tasks_2026-MM-DD.csv
```
- Output goes to `data/` (git-ignored). The file contains **PII**: Subjects are personalised
  with borrower names, and each row links a borrower Id to their email behaviour. Never commit
  it, and never paste rows into docs or chat.
- Expected size: a few hundred MB. Split by `CreatedDate` month if the job times out.

### 2.3 Load the archive (D3)
Load into BigQuery `mcp-connector-procedure.salesforce_archive.cio_email_tasks`, with
`CreatedDate` as the partition column. Restrict access to the dataset owner and one named
admin.

### 2.4 Verify the archive
- Total rows = the `COUNT()` of the scope query taken at export time.
- Per-`Subtype__c` counts match between Salesforce and the archive.
- A random sample of 20 Ids is identical field by field.
- Record the counts in `TASK_STORAGE_PLAN.md` §5 (log).

---

## Phase 3 — hard-delete (needs confirmation at every batch)

**Recovers:** Email Sent alone ≈ 1.94 M × 2 KB ≈ **3,790 MB**, taking storage from 82.7% to
**≈ 50%**. The D2 12-month cut on the other events adds a little more.

### 3.1 Pre-checks
1. The archive from Phase 2 is verified (2.4).
2. BigQuery: list every view and scheduled query that reads `salesforce.Task` (INFORMATION_SCHEMA
   or the handover Appendix A SQL). Confirm none relies on Customer.io email-event rows.
   Notify SimoOS / Lovable owners of the date.
3. Check whether the managed `ZVC` `TaskTrigger` (Zoom) runs logic on delete. If it does, test
   its impact in staging first.

### 3.2 Enable hard delete (metadata change, through a PR)
- New permission set `Bulk_API_Hard_Delete_Temp` with `bulkApiHardDelete = true`, deployed to
  `homesi-staging`, then prod (from merged `main`, per `CHANGE_POLICY.md`).
- Assign it **only** to the operator for the duration of Phase 3, then unassign it and record
  that in the log.

### 3.3 Rehearse in `homesi-staging`
Create ~5,000 Tasks there with the same shape (or use existing ones if the sandbox has them).
Run the exact delete commands of 3.4 and confirm: no errors, the related flows behave, and
storage drops after recalculation.

### 3.4 Delete in prod, in batches
1. Build the Id file per batch from the **archive** (not a new live query), so only archived
   rows are deleted. One batch = one `CreatedDate` month (≈ 50 k–400 k rows). **Sort each
   file by `WhoId`/`WhatId`** to avoid `UNABLE_TO_LOCK_ROW` on the parent Lead or Opportunity.
2. First batch: the oldest month (2025-01, ≈ 52 k rows). Then:
   ```bash
   sf data delete bulk --target-org prod --sobject Task --hard-delete --wait 60 \
     --file data/cio_delete_2025-01.csv --line-ending CRLF
   ```
   The prod guard will ask for confirmation. That is expected.
3. After each batch, record processed / failed / job Id. Retry failures only after reading the
   error. Stop on any unexpected error type.
4. Continue month by month. Run off-hours, and never overlapping ~05:00 UTC (BigQuery transfer).

### 3.5 Verify
- The scope query `COUNT()` for each deleted month = 0.
- `sf org list limits --target-org prod` shows DataStorageMB falling. [Likely] Storage is
  recalculated asynchronously, so allow up to 24 h before judging.
- Spot-check 5 Leads that had deleted Tasks: `Status`, `HasOptedOutOfEmail` and
  `LastActivityDate` unchanged.

### 3.6 Close
Unassign the hard-delete permission set. Update `PROD_STATE_LOG`-style entries in
`OPERATING_CONTEXT.md` and the log below. Add a numbered gotcha to `ORG_REFERENCE.md`:
"Customer.io event Tasks are Open, created by `sf integrations`, and ≈ 2 KB each."

### 3.7 Rollback
Hard delete cannot be undone. Only re-inserting from the archive restores data, and that gets
new Ids and new `CreatedDate` unless "Set Audit Fields upon Record Creation" is enabled. So
3.1 and 2.4 are the real safety net.

---

## 4. After the plan: keep it from coming back

- A monthly retention job (a scheduled script, or a batch Apex class through a PR) that
  archives and deletes Customer.io event Tasks older than 12 months.
- A storage alert at **85%**. Today nobody is warned until users see insert errors.
- Longer term: replace per-event Tasks with counters on Lead/Contact
  (`EMAIL_ENGAGEMENT_DESIGN.md` Level 1). A counter uses no extra storage.

## 5. Execution log

| Date | Step | Who | Result / Ids / counts |
|---|---|---|---|
| 2026-09-30 | Plan drafted from live reads (§0) | Claude Code session | — |

Sources for Recycle Bin and hard-delete behaviour:
[Salesforce LDV — Deleting Data](https://developer.salesforce.com/docs/platform/salesforce-large-data-volumes-bp/guide/ldv-deployments-techniques-deleting-data.html),
[Trailhead — Perform data deletes and extracts](https://trailhead.salesforce.com/content/learn/modules/large-data-volumes/perform-data-deletes-and-extracts),
[Hard Delete records with REST Bulk API](https://help.salesforce.com/s/articleView?id=000382207&language=en_US&type=1).
