# Salesforce Workspace — Project Reference

This file is a reference for any AI agent (or new Cowork session) working in this Salesforce project. It captures shared context, canonical queries, and lessons learned so we don't have to rediscover them each time.

> **ACTIVE PROJECT (2026-07): Borrower Follow-Up System** — full spec in `Borrower_FollowUp_System_Design.md` (this folder; read its §0 handoff header first — design complete, nothing built, decisions marked DECIDED are final). Board deck: `Borrower_FollowUp_System_Board_Deck.pptx`.

> **ACTIVE PROJECT (2026-07): Bilingual Prequalification Form (Screen Flow `Prequalification_Form`)** — bilingual (ES/EN) guided intake on **Lead**, launched by the **`Start Prequalification`** Lead quick action. Currently **STAGING only, active v14+** (prod cutover of flow + action still pending). Writes to Lead prequal fields; on save updates the launching record (recordId) or dedupes by email/phone; ends with a document checklist. Doc logic = ID type (SSN/ITIN) × Employment (Employee/Self-Employed), **built with a Decision element `dec_Docs` (NOT a formula — Flow formulas null-poison and can't reference other formulas)**, stored to `Prequal_Required_Documents__c` with real newlines. Co-borrower gets its own list via `dec_CoDocs` → `CoBorrower_Required_Documents__c` (co-borrower ID type via `CoBorrower_ID_Type__c` picklist SSN/ITIN). The "Application" tab was renamed **"Prequalification Form"** on Lightning pages `Lead_Record_Page_Three_Admins_Borrower` (prod) + `Lead_Record_Page1_Borrower` (staging). **Phase 2 = public Experience Cloud guest form (reCAPTCHA + honeypot + OTP-gated dedupe) — not built.** Branch 703 rent-doc exception NOT yet wired (all ITIN applicants currently get the 2 rent docs).
>
> **Prequal range fields exist on BOTH Lead AND Opportunity — DO NOT recreate/override when building the Opportunity flow:** `Prequal_Downpayment_Range__c` (picklist: `$0 - $10,000` / `$10,001 - $20,000` / `More than $20,000`) and `Prequal_Income_Range__c` (picklist: `$0 - $5,000` / `$5,001 - $10,000` / `More than $10,000`). Created on Opportunity 2026-07-24 (staging + prod), FLS on Admin. The Lead prequal form writes ranges to these (the old currency `Downpayment_money__c` / `Income__c` are left for exact amounts). Best Day/Time-to-contact are multiselects storing `;`-joined values into widened Text(255) `Prequal_Best_Day_To_Contact__c` / `Prequal_Best_Time_To_Contact__c` (day names; time buckets store the hour range in the value, e.g. `Morning (9 AM–12 PM)`). Tax Years Filed = multiselect of dynamic Current-Year −1/−2/−3.
>
> **STANDING FLS RULE — ANY new custom field (DECIDED 2026-07-24, broadened from prequal-only): every new custom field, on every prod deploy, gets read+edit FLS (read-only for formula/roll-up/auto-number fields that can't be editable) on ALL 13 human working profiles — no exception.** Applies to fields on any object those profiles can access (Lead, Opportunity, etc.); for objects a given profile has no access to, that profile is skipped (FLS would error). The 13: `Agent`, `Agent Loa On-Demand`, `Agent Recruiter`, `Agent Sales`, `Agent TPO`, `Branch Manager`, `Branch Manager AA084`, `LO Profile`, `LOA Profile`, `Only_assignment`, `Sales agent Profile`, `Supervisor`, `Supervisor Sales` (System Administrator already has it). Do this via direct profile FLS, NOT a permission set (user directive). Integration/system/Chatter/guest profiles are excluded (no relevant object access → FLS errors/meaningless). Also added 2 fields (Lead + Opp) 2026-07-24 for a SEPARATE project: `Prequal_Help_Type__c` (picklist: Purchase Primary or Second Home / Purchase Investment Property / Refinance / Other) + `Prequal_Help_Other_Description__c` Text(255) — NOT wired into the prequal flow.

## Project context

This workspace is for the **Simo Solutions Group / Homesi** Salesforce org (alias `prod`, also `homesi-staging`).

The primary deliverable is the **Closing On Time KPI dashboard** (`01ZQg00000MH3EXMA1`, folder "B2C & B2B Dashboards"), which tracks how often Eve-lender Borrower loans close on or before their original estimated closing date.

## Canonical query: Closed Loans

The standard filter set for "closed loans" used across all dashboard reports and analyses. **Use this exact filter when the user asks about "closed loans" unless they specify otherwise.**

```sql
SELECT
    Id,
    Name,
    CloseDate,
    Disbursement_Date__c,
    Org_Est_Closing_Date__c,
    Closing_On_Time__c,
    On_Time_Pct__c,
    Branch__c,
    Loan_Officers__r.Name,
    Loan_Channel__c
FROM Opportunity
WHERE
    RecordType.DeveloperName = 'Borrower'
    AND Closed_Loan__c = true
    AND Lender__c LIKE '%Eve%'
    AND Current_Status__c != 'Archive Loan'
    AND Disbursement_Date__c >= LAST_N_MONTHS:3
ORDER BY Disbursement_Date__c DESC
```

### Filter rationale

| Filter | Why |
|---|---|
| `RecordType.DeveloperName = 'Borrower'` | Only Borrower record type (`012Kb000000RpDEIA0`) — the loan record type |
| `Closed_Loan__c = true` | Loan has been disbursed |
| `Lender__c LIKE '%Eve%'` | Catches "Everett Financial, Inc. dba Supreme Lending" |
| `Current_Status__c != 'Archive Loan'` | Excludes archived loans |
| `Disbursement_Date__c >= LAST_N_MONTHS:3` | Last 4 months including current — matches dashboard scope |

### Common variations

- **All time:** drop the `Disbursement_Date__c` filter
- **Just delayed:** add `AND Closing_On_Time__c = 'Delayed'`
- **Just on time:** add `AND Closing_On_Time__c = 'On Time'`
- **Active pipeline (open loans):** swap to `Closed_Loan__c = false AND Application_Date__c != null AND Org_Est_Closing_Date__c != null`
- **Specific window:** replace `LAST_N_MONTHS:3` with `THIS_MONTH`, `LAST_MONTH`, `THIS_FISCAL_QUARTER`, etc., or explicit dates `>= 2026-01-01 AND Disbursement_Date__c <= 2026-01-31`

### SOQL gotchas in this org

- **Cannot compare two fields in WHERE.** SOQL doesn't allow `WHERE Field1 = Field2`. Use the formula field `Closing_On_Time__c` (returns "On Time" / "Delayed") instead of comparing dates directly.
- **Cannot group by formula text fields.** `GROUP BY Closing_On_Time__c` fails. Filter on it instead (`WHERE Closing_On_Time__c = 'On Time'`).

## Key custom fields on Opportunity

| API Name | Label | Type | Notes |
|---|---|---|---|
| `Closing_On_Time__c` | Closing On Time | Formula (Text) | Returns `"On Time"` if `Disbursement_Date__c <= Org_Est_Closing_Date__c`, `"Delayed"` otherwise, NULL if not closed |
| `Stat_Closing_Risk__c` | Stat Closing Risk | Formula (Text) | **Forward-looking probabilistic risk for ACTIVE pipeline.** Returns `"Out of Scope"` (won't fund this month), `"Delayed"` (stuck in milestone too long), `"On Track"` (active and progressing normally), or blank (closed/Closed Lost/missing data). Uses Current_Milestone_Date__c as base date, applies milestone benchmarks from email spec. Brokered channel = flat 30-day rule; non-Brokered = 2× avg days in milestone. Statistical reference only — qualitative healthiness field is source of truth when they conflict. |
| `On_Time_Pct__c` | % On Time (Numeric) | Formula (Number) | Returns 100 / 0 / NULL — AVG gives % directly |
| `Delayed_Pct__c` | % Delayed (Numeric) | Formula (Number) | Returns 100 / 0 / NULL — AVG gives % directly |
| `Disbursement_Date__c` | Disbursement Date | Date | Actual close/funding date — kept in sync with standard `CloseDate` via flow |
| `Org_Est_Closing_Date__c` | Org Est. Closing Date | Date | Target close date set at application; NEVER updated after |
| `Closed_Loan__c` | Closed Loan | Checkbox | True when loan has funded |
| `Current_Status__c` | Current Status | Picklist | Use `!= 'Archive Loan'` to exclude archived |
| `Current_Milestone__c` | Current Milestone | Text(50) | "Started", "Processing", "Submittal", "Initial Decision", "Resubmittal", "Clear To Close", "Closing" |
| `Branch__c` | Branch | Picklist | Branch code (e.g., "716", "770") |
| `Loan_Officers__c` | Loan Officers | Lookup(Loan Officer custom obj) | Use `Loan_Officers__r.Name` for display |
| `Loan_Channel__c` | Loan Channel | Text(30) | E.g., "Brokered" (relevant for probabilistic risk model) |
| `Lender__c` | Lender | Text(50) | Filter `LIKE '%Eve%'` for Everett Financial |
| `Application_Date__c` | Application Date | Date | "Started" milestone date |
| `Listing_Agent__c` | Listing Agent | Lookup(Contact) | Set by `OpportunityUpdater` from the `listingAgent` payload. Child relationship label "Opportunities (Listing Agent)" (`Opportunities4`) — NOT currently on the Contact page layout. |
| `Buyers_Agent__c` | Buyers Agent | Lookup(Contact) | Set by `OpportunityUpdater` from the `buyersAgent` payload. Child relationship label "Opportunities (Buyers Agent)" (`Opportunities3`) — NOT currently on the Contact page layout. |
| `Referred_By__c` | Referred By | Lookup(Contact) | Pre-existing realtor referral. Child relationship label is plain "Opportunities" (`Opportunities`) and IS on the Contact page layout — appears under section header "Opportunities referred by this contact". History tracked. |
| `LE_Sent_Date__c` | LE Sent Date | Date | Created 2026-06-04. Loan Estimate sent date. Encompass-populated. Used by `LOA2_Task_Disclosures_FollowUp`. |
| `LE_Due_Date__c` | LE Due Date | Date | Created 2026-06-04. RESPA LE due date. Encompass-populated. Used by `LOA2_Task_Issue_Disclosures` for ActivityDate. |
| `LE_Revised_Date__c` | LE Revised Date | Date | Created 2026-06-05. Revised LE date. Used by `LOA2_Task_Close_On_COC_Cleared` to close the COC Rate Locked task. |
| `ICD_Date__c` | ICD Date | Date | Created 2026-06-05. Initial Closing Disclosure date. Used by `LOA2_Task_Close_On_COC_Cleared` alongside `LE_Revised_Date__c`, and by `LOA2_Task_ICD_Request` (blank gate) + `LOA2_Task_Close_On_ICD_Received` (close trigger). |
| `Title_Commitment_Date__c` | Title Commitment Date | Date | Created 2026-06-08. Title Commitment received date. Encompass-populated. One of three trigger fields for `LOA2_Task_ICD_Request`. No FLS / page layout yet. |
| `Hazard_Insurance_Date__c` | Hazard Insurance Date | Date | Created 2026-06-08. Hazard Insurance received date. Encompass-populated. One of three trigger fields for `LOA2_Task_ICD_Request`. No FLS / page layout yet. NOTE: distinct from pre-existing non-date `Hazard_Ins__c`. |
| `Lock_Date__c` | Lock Date | Date | Pre-existing. Rate lock date. Used by `LOA2_Task_COC_Rate_Locked` and as a trigger field for `LOA2_Task_ICD_Request`. |
| `Disclosures_Signed_Date__c` | Disclosures Signed Date | Date | Pre-existing. Borrower signed disclosures. Drives `LOA2_Task_Order_Appraisal`, `LOA2_Task_Send_to_Processing`, `LOA2_FHA_Docs_Email_to_Nila`. |
| `Appraisal_Ordered_Date__c` | Appraisal Ordered Date | Date | Pre-existing. Drives `LOA2_Task_Close_On_Appraisal_Ordered`. |
| `Submitted_to_Processing_Date__c` | Submitted to Processing Date | Date | Pre-existing. Drives `LOA2_Task_Close_On_Submitted_To_Processing`. |
| `Loan_Type__c` | Loan Type | Text(50) | Pre-existing. **Text not picklist** — filter with exact string `"FHA"` for FHA-only logic. Used by `LOA2_FHA_Docs_Email_to_Nila`. |
| `LOA_2__c` | LOA2 (text) | Text | Pre-existing. LOS-written **text name** of the LOA2 (e.g. "Daniela Esguerra"). Source field the `LOA1_and_LOA2_Automatic_Assignment` flow reads to resolve the `LOA2__c` User lookup. NOT used by the FHA template (we use `LOA2_Name__c` instead, since `LOA_2__c` is blank on the ~7 open opps where LOA2 was set via the UI lookup rather than the LOS). |
| `LOA2_Name__c` | LOA2 Name | Formula (Text) | Created 2026-06-08, **in use**. `TRIM(LOA2__r.FirstName & " " & LOA2__r.LastName)` — resolves the LOA2 user's name. **The `LOA2_FHA_Docs_Request` template merges `{!Opportunity.LOA2_Name__c}`** so the LOA2 line is never blank (covers the UI-assigned cases where `LOA_2__c` text is empty but `LOA2__c` lookup is set). FLS granted to Admin profile (`profiles/Admin.profile-meta.xml`). **Gotcha: formula fields can't reference User's compound `Name` (`LOA2__r.Name` fails deploy "Field Name does not exist") — use FirstName & LastName.** |
| `Agent_Role__c` | Agent Role | Picklist (on Task, also reused on Opp) | On Task: classifies task by who owns it (`LOA1`, `LOA2`, `Processor`). Used by `SLA_Follow_Ups` to gate the LOA2 no-cycle branch and by LOA2 dashboards/reports. All 5 LOA2 task-creating flows now stamp this with `LOA2`. |
| `Touch_Type__c` | Touch Type | Picklist (Task) | `"First Touch"` (24h SLA) or `"Follow Up"` (48h SLA). All 5 LOA2 task-creating flows stamp `"Follow Up"`. Required for `SLA_Follow_Ups` to score the task. |
| `Assigned_Date__c` | Assigned Date | DateTime (Task) | Set to `$Flow.CurrentDateTime` by all 5 LOA2 task-creating flows. `SLA_Follow_Ups` reads this as the baseline for computing business hours to completion. |

### Deprecated / unreliable fields — avoid

| API Name | Why to avoid |
|---|---|
| `Loan_Officer__c` | Labeled "Loan Officer Deprecated" — use `Loan_Officers__c` instead |
| `Closed_Won_Date__c` (Label: "Closed Date") | Only ~50% populated; inconsistent. Use standard `CloseDate` instead. Has same display label as standard CloseDate which causes confusion. |

### Standard CloseDate vs Disbursement_Date__c

**They are kept in sync** by an active flow ("Sync Close Date and Amount for Borrower Opportunities") for closed Borrower loans. Verified 0 mismatches across 153 loans in last 4 months. Either field can be used — `CloseDate` (standard) gets better OOTB Salesforce reporting support; `Disbursement_Date__c` is more semantically clear.

## Active flows on Opportunity

| Flow | Purpose |
|---|---|
| Sync Close Date and Amount for Borrower Opportunities | Keeps `CloseDate` in sync with `Disbursement_Date__c` |
| Close Opp when current status is Hired by Loan Officer | Auto-closes opp when status flips |
| Update current status by new or closed stage | Updates `Current_Status__c` from stage transitions |
| Update current Milestone/Loan status Opp | Before-save, Borrower opps. Recomputes `StageName` from `Closed_Loan__c` / `Loan_Status__c` / `Application_Date__c` / `Current_Milestone__c` on every save. **Guarded 2026-05-22** — see Stage protection below. |
| Sync Current Status with Stage | After-save, Opportunity. Sets `Current_Status__c` from `StageName` transitions. **Guarded 2026-05-27** — see Stage protection Fix 4. |
| LOA1 and LOA2 Automatic Assignment | After-save, Opportunity. Watches `LOA__c` / `LOA_2__c` / `Processor_Jr_Text__c` (text fields written by LOS). Looks up matching User by Name, writes Id to corresponding lookup field, then creates "First Touch" / "Document Follow Up" task. Has duplicate-prevention guard (added 2026-05-04). |
| LOA First Follow Up | After-save, Opportunity. Watches `LOA1__c` / `LOA2__c` / `Processor_Jr__c` (User lookups, picked via UI). Creates "First Touch" task + updates `*_Assignment_Date__c`. Has duplicate-prevention guard (added 2026-05-04). |
| First Touch with Chatter | After-insert, FeedItem. When a Chatter post is added to a "Document Follow Up" Task, advances ActivityDate + 2 business days and flips `Touch_Type__c` First Touch → Follow Up. **Bug fixed 2026-04-29** — missing Id filter caused it to update the user's oldest open task instead of the correct one. |
| SLA Follow Ups | After-save, Task. Scores Task completion against SLA (24h First Touch / 48h Follow Up). Writes `SLA__c` + `SLA_Missed_By__c`. **Modified 2026-06-04 (v8)** — removed LOA2 auto-cycle default branch (no more "Follow Up - LOA2" auto-tasks). LOA1 and Lead cycling unchanged. Switched to AUTO_LAYOUT_CANVAS. |
| 11 × LOA2 milestone task flows | After-save, Opportunity. Data-driven task creation + auto-close based on milestone date fields populating. See dedicated **LOA2 milestone task automation** section below. |

## Stage protection — Closed Won / Closed Lost (added 2026-05-22)

Three pieces keep Opportunity stage closes from being silently overwritten.

### Background — the 2026-05-15 mass-revert

The flow `Update_current_Milestone_Loan_status_Opp` (before-save, Borrower opps, created 2026-04-27) recomputes `StageName` from data fields on **every** save. It originally had only a `RecordType = Borrower` entry filter, so any save touching an already-closed opp re-derived its stage. On 2026-05-15 a bulk update by the It Support admin touched 572 Closed Lost Borrower opps; the flow fired on each and recomputed the stage — 569 reopened (Needs Analysis / Proposal / Negotiation), 3 → Closed Won. The stage values it assigns are the tell that this flow, not the batch itself, did the damage.

### Fix 1 — flow entry-criteria guard (flow version 21)

`Update_current_Milestone_Loan_status_Opp` start filters are now `RecordType = Borrower AND StageName != 'Closed Lost' AND StageName != 'Closed Won'`. Once an opp is closed the flow never runs on it again. It can still push *open* opps forward and close them; it just never re-touches a closed one. Evaluated on new values (before-save), so a manual close to Closed Lost skips the flow and sticks.

### Fix 2 — VR `Closed_Won_Automation_Only`

Blocks Stage = Closed Won unless `Closed_Loan__c = true`. Closed Won is automation-only — the flow's `update_opp` path sets it when the loan funds. Borrower record type only. Formula uses `OR(ISNEW(), ISCHANGED(StageName))` so it only blocks the *act* of setting it, not edits to existing records.

### Fix 3 — VR `Funded_Loan_Cannot_Be_Closed_Lost`

Blocks Stage = Closed Lost when `Closed_Loan__c = true`. A funded loan stays Closed Won. Borrower record type only.

Net behavior: users CAN set Closed Lost manually (sticks, no revert); users CANNOT set Closed Won; a funded loan cannot be marked Closed Lost; batch/integration updates to already-closed opps no longer revert them.

### Fix 4 — `Sync_Current_Status_with_Stage` entry guard (flow version 13, added 2026-05-27)

Same shape of guard, second flow. `Sync_Current_Status_with_Stage` is the flow that sets `Current_Status__c` from `StageName` transitions — Negotiation → `"Ratified"`, Proposal → `"Pre-Approved"`, Qualification → `"Pre-Qualified/Doc Requested"`, Needs Analysis → an On-Hold value, and **default (any other stage, including Closed Lost / Closed Won) → blank Current Status**. Entry was previously just `StageName IsChanged`; it is now `StageName IsChanged AND StageName != 'Closed Lost' AND StageName != 'Closed Won'`. So a transition to a closed stage no longer triggers the default-branch clear of Current Status, and a re-open transition still fires normally (incoming StageName is the open value). This was the second mechanism quietly blanking `Current_Status__c` on close, alongside the milestone flow's `Set_to_Closed_Lost` assignment.

### Fix 5 — `Clear_Current_Status_On_Manual_Close` flow (enforces "closed = no Current Status")

After-save flow, **Borrower record type only** (per decision 2026-07-06). Entry: `RecordType = Borrower AND Current_Status__c IsNull false AND (StageName = 'Closed Lost' OR StageName = 'Closed Won')`, `doesRequireRecordChangedToMeetCriteria = true`. Action: blanks `Current_Status__c` (`recordUpdates` on `$Record` with `inputAssignments` setting the field to empty). This is the affirmative "clear it" mechanism that complements Fix 2/3/4 (which only *stop* Current Status being set/kept on close). Fixes 4 and the milestone flow's `Set_to_Closed_Lost` blank it on specific transitions; this flow guarantees it for **any** save that lands a Borrower opp in a closed stage with a lingering status.

**v2 (2026-07-06):** trigger changed `Update` → `CreateAndUpdate` so opps *created* already-closed (import / lead-convert path) also get cleared, not just close-transitions.

**Backfill for pre-existing stale records:** opps closed *before* this flow existed still carried a Current Status (595 Borrower: mostly "Ratified", plus Pre-Approved / Pre-Qualified / On-Hold variants / 2 Archive Loan). Cleared via `scripts/clear_current_status_on_closed_borrower_opps.apex` (idempotent — re-run only touches records still holding a status). **Non-Borrower closed opps (Realtor 53, Loan Officer 33, Broker 1) were deliberately left untouched** — user scoped this rule to Borrower loans only; the same shared picklist is used on recruitment opps (incl. "Hired") but is out of scope here. VR note: clearing Current Status to blank with no StageName change does NOT trip `Require_LoanNumber_For_Update` (its OR resolves false on a blank new value + unchanged stage), so no Bypass flag is needed.

### Other Opportunity validation rules relevant to stage changes

- `Reason_for_loss` — requires `Reason_for_loss__c` when closing as lost. Picklist values include `No Reason` (a valid catch-all).
- `Require_LoanNumber_For_Update` — `Loan__c` (Loan #) must be populated before changing Stage or Current Status. Formula: `RecordType = Borrower AND ISBLANK(Loan__c) AND (ISCHANGED(StageName) to a non-[Qualification/Needs Analysis/Closed Lost] stage OR Current_Status = 'Ratified')`, gated by `NOT(Bypass_Validation_Rules__c)` and excluding the Automated Process + `sfintegrations@citylendinginc.com` users.

## Apex sharing automation

### Lead — `LeadCoOwnerSharing` (existing, pre-dates this project)

Trigger on Lead (after insert / after update). Grants `Edit` access via `LeadShare` (`RowCause = 'Manual'`) when:

- `Co_Owner__c` (Lookup to User) is set → shares directly to that user
- `Loan_Officer__c` (Lookup to `Loan_Officer__c` custom object) is set → resolves through `Loan_Officer__c.Salesforce_User__c` and shares to that user

Companion classes: `LeadCoOwnerSharingBackfill` (batch), plus `*Test` classes.

> **Known quirk in the Lead version:** when only one of the two fields changes, the trigger deletes ALL `Manual` shares for the lead but only re-inserts the share for the field that changed. The other share gets lost until that field is touched. The Opportunity version below was written without this bug (rebuilds from current state of all tracked fields).

### Opportunity — `OpportunityCoOwnerSharing` (added 2026-04-29, extended 2026-05-12)

Trigger on Opportunity (after insert / after update). Grants `Edit` access via `OpportunityShare` (`RowCause = 'Manual'`) for the users referenced by **four** fields:

| Field | Type | How user is resolved |
|---|---|---|
| `LOA1__c` | Lookup(User) | direct |
| `LOA2__c` | Lookup(User) | direct |
| `Processor_Jr__c` | Lookup(User) | direct |
| `Loan_Officers__c` | Lookup(Loan_Officer__c) | resolves via `Loan_Officer__c.Salesforce_User__c` |

Behavior on any of those four fields changing:

1. Delete existing `Manual` `OpportunityShare` rows for the opp
2. Rebuild from the **current state** of all four fields (deduped, owner skipped)

Note: `Loan_Officer__c.Salesforce_User__c` is auto-populated by the `LoanOfficerUserMatch` (before-insert/update) trigger based on email match between `Loan_Officer__c.Email__c` and `User.Email` (active users only, Guest excluded). To manually set it, change `Email__c` to the target user's email — the trigger does the rest. Setting `Salesforce_User__c` directly won't stick because the trigger overwrites it on every save.

Source files:

- `force-app/main/default/triggers/OpportunityCoOwnerSharing.trigger`
- `force-app/main/default/classes/OpportunityCoOwnerSharingBackfill.cls`
- `force-app/main/default/classes/OpportunityCoOwnerSharingTest.cls`
- `force-app/main/default/classes/OpportunityCoOwnerSharingBackfillTest.cls`

Backfill:

```apex
Database.executeBatch(new OpportunityCoOwnerSharingBackfill(), 200);
```

Run it any time shares drift (e.g., bulk loads bypassing the trigger). Last run: 2026-04-29 in prod, 326 manual shares created across 363 eligible open opportunities.

### Lookup filters on the Opportunity lookups (verified in prod)

| Field | Filter | Required? |
|---|---|---|
| `LOA1__c` | `User.Profile.Name = 'Agent Loa On-Demand'` | Yes (active, not optional) |
| `LOA2__c` | `User.Profile.Name = 'Agent Loa On-Demand'` | Yes (active, not optional) |
| `Processor_Jr__c` | none | n/a |

The custom error message on LOA1 reads "Only users with the title 'LOA' can be selected" but the actual filter checks **Profile**, not Title. Test users for any future Apex test that touches these fields must be inserted with `ProfileId` of the `Agent Loa On-Demand` profile.

### Owner-change detection (added 2026-07-13 — closes a real access bug)

**`OwnerId != oldOpp?.OwnerId` is now part of the `changed` check in `OpportunityCoOwnerSharing`.** Root cause it fixes: **changing an Opportunity's owner makes the platform delete ALL `RowCause='Manual'` shares** (owner-change sharing recalc). The trigger previously watched only the 4 LOA lookup fields, so a reassignment silently wiped every LOA co-owner share and nothing rebuilt it until an LOA field was next touched — the LOA (e.g. Karen de Fex on `006Qg00000iEugvIAC`, reassigned sf integrations→Angie→Giancarlo) lost access with no error. Now any owner change re-adds the opp to `oppsToClean` and rebuilds Manual shares from current LOA state (owner still skipped). Covered by test `owner_change_rebuilds_loa_shares`. Overhead is negligible (owner-only changes with no LOA fields set just query an empty share list and insert nothing).

- **Silent insert failures.** The trigger's `Database.insert(sharesToInsert, false)` only `System.debug`s errors — a genuinely failing share insert is invisible. Not hardened yet; if shares mysteriously don't appear, check debug logs. (License isn't a factor here: LOAs on the `Agent Loa On-Demand` profile carry a full **Salesforce (SFDC)** license, so Opportunity manual shares are permitted.)
- **Remediation for historical drift:** `scripts/run_opp_coowner_backfill.apex` (`OpportunityCoOwnerSharingBackfill`, idempotent) rebuilds Manual shares for every open opp with an LOA field set — run it once after this deploy to fix all loans that lost shares to pre-fix reassignments.

### Why we explicitly skip `userId == OwnerId`

Two layers: (1) our trigger has `if (userId == opp.OwnerId) continue;` because the owner already has full access via the auto-managed `RowCause = 'Owner'` share; (2) Salesforce would reject the insert anyway with `FIELD_INTEGRITY_EXCEPTION` ("Owner of the record cannot be a sharing recipient"). Our skip keeps the partial-save error log clean.

## Apex owner-assignment automation

### Opportunity — `OpportunityAccountExecutiveOwner` (added 2026-05-28)

Before-insert / before-update trigger on Opportunity. When `Account_Executive__c` (Text(50)) is populated AND `Affinity_Program__c` (Checkbox) is true, resolves an active non-Guest `User` by `User.Name` (case-insensitive) and sets `OwnerId` to that user's Id.

Behavior:

- Fires on insert and on update only when `Account_Executive__c` OR `Affinity_Program__c` changes (avoids re-evaluating every save).
- **No match**: leaves `OwnerId` unchanged (silent skip).
- **Ambiguous match** (multiple active users with the same `Name`): also leaves `OwnerId` unchanged.
- **One-way only**: if `Affinity_Program__c` becomes false later, or `Account_Executive__c` is cleared, ownership does NOT revert. Stays with whoever currently owns it.

Source files:

- `force-app/main/default/triggers/OpportunityAccountExecutiveOwner.trigger`
- `force-app/main/default/classes/OpportunityAccountExecutiveOwnerTest.cls` (8 tests, 100% trigger coverage)

No backfill needed at deploy time — at deploy `Account_Executive__c` had zero populated rows. If a future bulk load populates it without firing the trigger, the trigger fires on the next save of each opp; no batch class exists for this one.

### Known interaction with `OpportunityCoOwnerSharing`

When this trigger changes `OwnerId`:

- The previous owner's auto-managed `RowCause = 'Owner'` share is removed by Salesforce; the new owner's is created. The platform also deletes all `RowCause = 'Manual'` shares.
- The `after-update` `OpportunityCoOwnerSharing` **does** watch `OwnerId` (since 2026-07-13, see "Owner-change detection" above) and rebuilds the Manual shares from the current LOA1/LOA2/Processor_Jr/Loan_Processor_User/Loan_Officers state, skipping the new owner.
- The previous owner, if they are in one of those fields, gets their Manual share back through that field. No action needed.

(Corrected 2026-09-29: this section previously said the sharing trigger ignores owner changes. Verified against the active prod trigger body.)

## Apex email-tracking automation

### EmailMessage — `EmailMessageStubContactCreator` (added 2026-04-30)

Trigger on EmailMessage (after insert). When an outbound email (`Incoming = false`) is inserted with `RelatedToId` pointing at an Opportunity, the handler parses `ToAddress`, `CcAddress`, and `BccAddress` (each is semicolon- or comma-delimited) and creates a stub `Contact` for any external recipient that does NOT already match an existing Contact, Lead, or User.

**Why this exists.** Inbound email capture in this org is **gated on the sender's email address matching a Contact, Lead, or User**. Without that gating record, replies from external third parties (title companies, HOI vendors, appraisers, borrowers using personal addresses) are silently dropped — they never become EmailMessage records and are invisible to anyone except the user who sent the original outbound. Auto-creating stub Contacts at outbound time ensures replies will be captured and threaded back to the originating Opportunity automatically.

**What the stub looks like.** The minimum viable Contact:

- `LastName` = local part of the email (e.g., `donna.hooper` for `donna.hooper@stewart.com`), capped at the 80-char field limit
- `Email` = full address (lowercased)
- `AccountId` = null (no parent Account is required for the gating to work)

The stub is purely a registry entry. No Account, no Opportunity Contact Role, no other fields needed.

**Internal domains skipped (hardcoded in the handler):**

- `supremelending.com`
- `simosolutionsgroup.com`

Add more in `EmailMessageStubContactHandler.INTERNAL_DOMAINS` and redeploy if needed.

**Source files:**

- `force-app/main/default/triggers/EmailMessageStubContactCreator.trigger`
- `force-app/main/default/classes/EmailMessageStubContactHandler.cls`
- `force-app/main/default/classes/EmailMessageStubContactHandlerTest.cls`
- `force-app/main/default/classes/EmailMessageStubContactBackfill.cls`
- `force-app/main/default/classes/EmailMessageStubContactBackfillTest.cls`

**Backfill:**

```apex
Database.executeBatch(new EmailMessageStubContactBackfill(), 200);
```

Idempotent — safe to re-run any time. Walks every existing outbound EmailMessage with `RelatedToId != null` and calls the same handler used by the trigger, so historical third-party addresses get stubs retroactively. Run this once after deploy to backfill the existing data.

**End-to-end behavior verified in prod (2026-04-29):**

1. Send outbound from Salesforce Email composer with `RelatedTo = Opportunity` → real `EmailMessage` row created on the Opp.
2. External recipient replies from their mailbox.
3. Reply lands as a real `EmailMessage` row on the **same** Opp within ~1–6 minutes (`ReplyToEmailMessageId` populated, threading via the embedded `Message-Id` token Salesforce embeds in outbound bodies when Enhanced Email + Send Through Office 365 are enabled).
4. Anyone with read access to the Opp sees both halves of the thread on the Activity Timeline and in Activity History.

The gating Contact does NOT need to be on an Account, on the Opp's OCRs, or anywhere else — its existence is what unlocks capture.

### What capture mechanism is doing the work

This org runs both Einstein Activity Capture (Connected Account model) and the Outlook integration with "Log Future Emails on This Thread" enabled. The **real `EmailMessage` records** that show up on the Opp come from the Outlook integration's auto-log path, not EAC — EAC stores items externally in AWS and never writes to the `EmailMessage` table. EAC remains the safety net for everything else (mail captured from connected mailboxes that doesn't match a Contact still surfaces on personal Activity Timelines).

Key implication: lose the address match and you lose the Opp-level capture. EAC alone won't save you.

### Known behaviors / gotchas specific to this trigger

- **Internal-to-internal email isn't captured as an EmailMessage either way** (e.g., Luis sending to a coworker). The org's inbound capture filters out internal cross-talk before address matching even runs. Not handled by this trigger; not a problem for the Jr Processor workflow which is external-facing.
- **Replies that land in Outlook's Junk folder don't get captured.** EAC and the Outlook integration only read the main Inbox. If a reply mysteriously fails to appear after 10+ minutes, check Junk first.
- **EmailMessageRelation linkage is not populated retroactively.** A Contact created by the trigger after the outbound has been inserted does NOT get an `EmailMessageRelation` row pointing at that historical email. So the Contact's own Activity Timeline will be empty — the email shows up only on the Opp's Timeline. This is fine for the user goal (Opp-level visibility), worth being aware of if anyone navigates from a Contact expecting to see correspondence history.

## Apex REST endpoint — `OpportunityUpdater` (extended 2026-05-13, 2026-05-15)

A `@RestResource(urlMapping='/OpportunityUpdate/*')` `global with sharing` class exposing a single `@HttpPost updateOpportunity()`. Encompass (the LOS) calls this endpoint to push loan-level data into Salesforce — it either updates an existing Borrower Opportunity or creates a new Lead, converts it to a Borrower Opportunity, then updates the resulting record. Originally authored by Mauricio Maldonado 2024-04-18; substantially extended this session.

**Source files:**

- `force-app/main/default/classes/OpportunityUpdater.cls`
- `force-app/main/default/classes/OpportunityUpdaterTest.cls`

**Request payload shape** (deserialized into `OpportunityData`):

- `loanGuid` (required) — Encompass loan GUID, maps to `Opportunity.LoanId__c`
- `lienPosition` — used for second-lien rejection rule (rejects `"Second Lien"` or misspelled `"Second Lie"` when `Total_Loan_Amount__c < 50000`)
- `email[]`, `phone[]` — borrower contact arrays (phones run through `PhoneFormatter.formatPhoneNumber` before matching)
- `fieldsToUpdate[]` — generic `{fieldName, fieldValue}` pairs applied to Opportunity fields with type-aware coercion
- `loanOfficer { companyName, firstName, lastName, email, nmls, encompassID, phone }`
- `listingAgent { companyName, firstName, lastName, email, phone }`
- `buyersAgent { companyName, firstName, lastName, email, phone }`

**Opportunity match precedence** (tried in order, first hit wins):

1. `LoanId__c = loanGuid`
2. `Loan__c = <Loan__c value from fieldsToUpdate>`
3. `RecordType = Borrower AND Branch__c = <Branch__c> AND (Email__c IN :email OR Phone_360SMS__c IN :phone360Values)` (ORDER BY CreatedDate DESC)

**Phone matching = digit variants against `Phone_360SMS__c` (changed 2026-06-16).** Both the Opportunity fallback match (#3) and the Lead match now query the **360 SMS** field `Phone_360SMS__c` (a formula that strips non-digits from the phone) instead of the formatted `Phone__c` / `Phone`. The incoming phones are passed through `buildPhoneVariants(List<String>)` (`@TestVisible`) which strips each to digits and emits **bare digits + last-10 + `"1"`+last-10**, deduped — because the stored 360 value sometimes keeps the country code (`1XXXXXXXXXX`) and sometimes doesn't (`XXXXXXXXXX`). `PhoneFormatter` is no longer called for matching (still exists for other callers). **Deliberately uses `IN` (exact) not `LIKE '%...%'`: a leading wildcard can't use an index and risks the "non-selective query against large object" error on Lead (~140K rows), plus substring false positives; the formula field is non-indexable either way, so the indexed RecordType/Branch/IsConverted filters keep the scan scoped.**

**Parent-owner follow (2026-09-30, prod field `0AfQg0000023nnpKAA`, class `0AfQg0000023nuHKAQ`; replaces the 2026-09-29 "owner guard").** The Lambda sends `OwnerId` for F30EEP loans only (the owner of the parent loan matched by `GVMT_Human_Guid__c`, when that owner is not `sf integrations`). `OpportunityUpdater` applies it on create and stores it in `Opportunity.Parent_Owner_Synced__c` (Text 18, no FLS — integration-only). On an existing Opportunity `followParentOwner()` compares the incoming parent owner with that field: **same → `OwnerId` untouched** (a manual reassignment of the F30EEP loan is kept); **different → the parent was reassigned, apply it and store it**; **field empty → store it only, no reassignment** (all F30EEP loans created before 2026-09-30 are initialised this way on their next upload); **incoming user inactive → skipped** (retried next upload). `withoutOwnerId(...)` still drops `OwnerId` before `applyFieldUpdates`, so nothing else writes the owner. Consequence: if someone reassigns the F30EEP loan by hand and *later* the parent owner changes, the parent wins. The inactive-owner → `sf integrations` reassignment is unchanged. See gotcha #31.

If all three miss → new-Lead path: search for an unconverted Borrower Lead by email OR phone (most recent first). If found, update its fields and reuse it. If not, insert a new Lead with `LeadSource = 'Encompass Integration'`, `Bypass_Validation_Rules__c = true`, `Skip_Loan_Creation__c = true`. Then `Database.convertLead(setConvertedStatus='Qualified')` produces the Opportunity.

**Loan officer match precedence** (3 separate queries, each guarded by `!String.isBlank`, first hit wins):

1. `EncompassID__c`
2. `NMLS_Number__c`
3. `Email__c`

Match-only — existing LO records are linked as-is, never updated. New LO records get `Name = firstName + ' ' + lastName`, `Email__c`, `NMLS_Number__c`, `EncompassID__c`, `Phone__c`, and `Company__c` (find-or-create Account by `companyName`). The three-query structure encodes a deliberate priority — collapsing into one OR query would lose the precedence AND mishandle blank values (a blank bind matches every null row). Don't refactor.

**Agent match (listing + buyers, identical logic):** `WHERE Email = :email OR Phone = :phone LIMIT 1`. Match-only — never refreshes an existing Contact. New Contacts get `AccountId` from a find-or-create on `companyName`.

**Junk-data sentinel filter** (`isValidAgentContact`): blocks the entire agent block if email or phone is a known LOS placeholder. Patterns the filter catches:

- Email matching `^na@` (case-insensitive), or exactly `na` / `n/a`
- Phone with all-identical digits after stripping non-numerics (`999-999-9999`, `000-000-0000`, `111-111-1111`, etc.), or fewer than 7 digits

Without this filter, ~2-4% of agent-bearing rows would attempt to create a stub Contact (e.g., named "na" with email `na@gmail.com`). Because the agent match uses `Email = :email OR Phone = :phone`, that stub would then attach to every subsequent loan with the same placeholders — one garbage Contact pinned across many Opportunities. The filter is forward-only: any junk Contacts already in the org from before deploy still exist and would need a separate query+delete to clean up.

**Type coercion helper** (`applyFieldUpdates`): one shared helper that fetches `Opportunity.SObjectType.getDescribe().fields.getMap()` ONCE and applies type-aware coercion per field. Handles `Boolean`, `Currency` / `Double` / `Percent`, `Date` (MM/dd/yyyy parsed), and falls back to string. Sentinels: `fieldValue == '//'` skips the field entirely; blank `fieldValue` sets the field to null EXCEPT for `CloseDate` which is left untouched. Replaced two duplicated ~30-line inline loops (2026-05-15 refactor).

**Branch Transfer guard (added 2026-07-13).** `applyFieldUpdates` reads `opp.get('Branch_Transfer__c')` once; when the matched Opportunity has `Branch_Transfer__c = true` (a human flagged the loan as a branch transfer), it **skips the incoming `Branch__c`** so Encompass can't overwrite the deliberately-set Salesforce branch (`if (branchTransfer && fieldUpdate.fieldName == 'Branch__c') continue;`). All other fields still apply. `Branch_Transfer__c` was added to every opp SELECT that feeds the update path (the 3 existing-opp match queries + the post-lead-convert requery) so `get()` never throws SObjectException. New-lead-convert path: a freshly converted opp has `Branch_Transfer__c = false`, so the incoming branch applies normally. Covered by tests `testBranchTransfer_SkipsBranchOverride` (guard on → SF branch kept) and `testBranchTransfer_False_AllowsBranchOverride` (guard off → Encompass branch applied).

**Known integration-side quirks (TypeScript payload construction):**

- The integration splits a single full-name string on spaces — `firstName = [0]`, `lastName = slice(1).join(' ')`. A one-token name like "Madonna" yields `lastName=""`, which would throw REQUIRED_FIELD_MISSING on Contact insert. Apex defensively falls back `lastName = firstName → email-local-part` so the insert never fails.
- The `companyName` fallback chain (`<agent>_companyName ?? <agent>_firstName ?? ""`) can yield (a) an empty string when both LOS fields are blank, OR (b) the agent's full name as the "company" when only the brokerage is blank (creates an Account literally named after the person). Both pass through to Apex verbatim. Apex skips Account creation when `companyName` is blank (Contact gets `AccountId = null`); the person-named-Account case is the integration's behavior, not the Apex's.
- The integration's loan officer payload reads `loan["lophonenumber"]` for `phone`. This column was missing from the 5/11 LOS export — if it's missing at integration runtime too, `Loan_Officer__c.Phone__c` will be set to empty string on new LO inserts. Worth confirming in the integration source.

**Tests** (12 total, deployed via `RunSpecifiedTests:OpportunityUpdaterTest`):

- Integration tests: `testUpdateExistingOpportunity`, `testCreateLeadAndConvertToOpportunity`, `testCreateLoanOfficer`, `testCreateListingAgent`, `testCreateBuyersAgent`, `testInvalidRequest`
- Edge-case tests for blank `companyName` and blank `lastName` on both agent types
- Junk-placeholder tests: `testJunkListingAgent_NoContactCreated`, `testJunkBuyersAgent_NoContactCreated`
- Unit tests on `@TestVisible` helpers: `testJunkPlaceholderHelpers`, `testApplyFieldUpdates_TypeCoercion`

Standard deploy command:

```
sf project deploy start \
  -d force-app/main/default/classes/OpportunityUpdater.cls \
  -d force-app/main/default/classes/OpportunityUpdaterTest.cls \
  -l RunSpecifiedTests \
  -t OpportunityUpdaterTest \
  -o prod
```

Deploy practice this session: staging first (`-o homesi-staging`), then prod after staging passes. Staging metadata is generally in sync enough for this endpoint that test results are meaningful pre-prod signal.

**Behavior verified in prod (2026-05-14):** 349 listing-agent Contacts created from one batch run with no junk placeholders slipping through; 0 new Loan Officers (all matched existing records — Loan Officer roster is internal Supreme Lending staff, 1,603 records in the org, stable).

**Open items / future work:**

- Confirm `lophonenumber` column actually exists in the LOS source the integration reads from. If yes, the existing `Phone__c` mapping will start populating on new LO inserts.
- Two remaining cleanup improvements identified but not yet implemented: (a) break the ~250-line `updateOpportunity` method into smaller helpers (`findOrCreateOpportunity`, `resolveLoanOfficer`, `upsertAgentContact`); (b) swap a couple of `[SELECT ... LIMIT 1]` singular-assignment queries to `List<...>` to avoid QueryException-on-empty risk.
- `Buyers_Agent__c` and `Listing_Agent__c` related lists are NOT on the Contact page layout. Links are queryable but invisible from the Contact record. A layout-change deploy would expose them.

## Days in Current Stage dashboard (added 2026-06-17)

Tracks how long open Borrower opps have sat in their current stage, measured from the stage's milestone date:
- **Qualification** → days since `Pre_Qualified_Doc_requested_Date__c`
- **Proposal** → days since `Pre_Approved_Date__c`
- **Negotiation** → days since `Ratified_Date__c`

**Field:** `Opportunity.Days_In_Current_Stage__c` — Number formula (`BlankAsBlank`): `CASE(TEXT(StageName), "Qualification", TODAY()-Pre_Qualified_Doc_requested_Date__c, "Proposal", TODAY()-Pre_Approved_Date__c, "Negotiation", TODAY()-Ratified_Date__c, null)`. Returns **blank** when the milestone date is missing (so the AVG only counts opps that actually have the date — important because ~14.7k of ~15.9k Qualification opps have no prequal date). FLS on Admin.

**Report:** `Avg Days in Current Stage` (`B2CBorrower` folder, `00OQg00000HLi2fMAD`), report type **Opportunity** (standard), Summary, grouped **Stage → Branch → Loan_Officers__c**, measure = AVG of `Days_In_Current_Stage__c` (via `<aggregateTypes>Average</aggregateTypes>` on the column). Filter: RecordType Borrower + open (`<params><name>open</name>open`) + `STAGE_NAME equals Qualification,Proposal,Negotiation` + Current_Status != Archive Loan. One report feeds all dashboard breakdowns (no need for 3 separate reports — a dashboard chart can group by any of the report's groupings).

**Dashboard:** `Days in Current Stage` (`B2C & B2B Dashboards` / `JCGRB2CB2B`, `01ZQg00000QlXmLMAV`), 3 Column/Bar components off the one report grouping by Stage / Branch / Loan_Officers__c, all `<chartSummary><aggregate>Average</aggregate><column>Opportunity.Days_In_Current_Stage__c</column>`. **Dashboard metadata gotchas hit:** `dashboardGridLayout` REQUIRES `<numberOfColumns>` + `<rowHeight>` (else "rowHeight must be positive"); `<sortBy>` enum is `RowValueDescending` not `ValueDescending`; `<groupingSorts>` only allows `groupingLevel` + `sortOrder` (no `aggregate`/`column` — value sort comes from component `sortBy`).

## Reports in B2C Borrower folder (Closing On Time KPI)

| API Name | Purpose |
|---|---|
| `Closing_On_Time_MTD` | MTD only (now mostly unused) |
| `Closing_On_Time_Last_3_Months` | Renamed to display "Last 4 Months" — overall summary |
| `Closing_On_Time_Trend_4_Months` | Matrix: Month × Status |
| `Closing_On_Time_Branch_Month` | Older branch breakdown |
| `Closing_On_Time_Branch_x_Month_Matrix` | Branch × Month × Status matrix — main % calc source |
| `Closing_On_Time_Delayed_Detail` | Delayed loans detail (Month → Branch grouping) |
| `Closing_On_Time_OnTime_Detail` | On-time loans detail (Month → Branch grouping) |
| `Closing_On_Time_Pct_By_Month` | % On Time per Close Month × Branch (BarGrouped chart on dashboard) |
| `Closing_On_Time_Pct_Delayed_By_Month` | % Delayed per Close Month × Branch (BarGrouped chart on dashboard) |

## Dashboard layout snapshot (`01ZQg00000MH3EXMA1`)

**As of 2026-04-28 — confirmed working layout. This is the user's approved version.**

Five components in vertical flow, 12-column grid:

### Row 1 — Trend (full width, rows 0–9)
- **Trend - On Time vs Delayed by Month**
- Component: `ColumnStacked`
- Source: `Closing_On_Time_Trend_4_Months`
- Groupings: Disbursement Month + Closing On Time (status)
- Measure: RowCount (counts, not %)

### Row 2 — Branch x Month counts (side by side, rows 10–21)
- **Delayed Loans by Branch x Month** (cols 0–5)
  - Component: `BarGrouped` (horizontal)
  - Source: `Closing_On_Time_Delayed_Detail`
  - Groupings: Disbursement Month → Branch
  - Measure: RowCount
- **On Time Loans by Branch x Month** (cols 6–11)
  - Component: `BarGrouped` (horizontal)
  - Source: `Closing_On_Time_OnTime_Detail`
  - Groupings: Disbursement Month → Branch
  - Measure: RowCount

### Row 3 — % On Time by Month (full width, rows 22–31)
- **Closing On Time - % by Month**
- Component: `BarGrouped`
- Source: `Closing_On_Time_Pct_By_Month`
- Groupings: `CLOSE_DATE` (Month) → `Branch__c`
- Measure: `Average` of `Opportunity.On_Time_Pct__c`
- g2 sortColumn: `a!Opportunity.On_Time_Pct__c` desc (highest % on time surfaces first per month)
- decimalPrecision: -1

### Row 4 — % Delayed by Month (full width, rows 32–41)
- **Closing On Time - % Delayed by Month**
- Component: `BarGrouped`
- Source: `Closing_On_Time_Pct_Delayed_By_Month`
- Groupings: `CLOSE_DATE` (Month) → `Branch__c`
- Measure: `Average` of `Opportunity.Delayed_Pct__c`
- g2 sortColumn: `a!Opportunity.Delayed_Pct__c` desc (highest % delayed surfaces first per month)
- decimalPrecision: -1

### Dashboard properties
- Type: SpecifiedUser
- Running user: `m.rodriguez@supremelending.com` (It Support, System Administrator)
- Title: `Closing On Time`
- Color palette: unity (default Salesforce)

### Working pattern for future % charts
The two `% by Month` charts use this exact pattern, which is the proven-working format for displaying percentages in dashboard charts via metadata:

```xml
<chartSummary>
    <aggregate>Average</aggregate>
    <axisBinding>y</axisBinding>
    <column>Opportunity.<NumericPctField>__c</column>
</chartSummary>
<componentType>BarGrouped</componentType>
<groupingColumn>CLOSE_DATE</groupingColumn>
<groupingColumn>Opportunity.Branch__c</groupingColumn>
```

Pair this with a Summary report that:
- Has the numeric % field as a column with `<aggregateTypes>Average</aggregateTypes>`
- Groups by `CLOSE_DATE` (Month) and `Branch__c`
- Has both fields' FLS granted (otherwise the chart errors with "fields no longer available")

## MonitorBase Alert updates (Lead bulk-update via SF Inspector)

Process for loading MonitorBase predictive/refi alert exports onto existing Lead records — different from a regular lead import because it's an UPDATE keyed on `Id`, not an insert.

### Source file
MonitorBase exports a wide CSV like `monitorbase_<user>_alerts_<run>_<date>_<id>.csv` with 40+ columns. Only four are needed:
- `CRM ID` → the 15-char Salesforce Lead Id (e.g. `00QQg00000YUS1j`)
- `Alert Intel` → the long-form alert text
- `Alert Date` → datetime in `M/d/yyyy H:mm` format
- (none in source) → an indicator boolean we add ourselves

### Lead target fields (verified in prod)

| Source | Target API name | Type | Notes |
|---|---|---|---|
| `CRM ID` | `Id` | reference | Match key for the update. 15- or 18-char both work. |
| `Alert Intel` | `MonitorBase_Alert__c` | textarea | The narrative ("Term Reduction…", "Refinance Opportunity…", etc.) |
| `Alert Date` | `MonitorBase_Alert_Date__c` | datetime | Must be strict ISO 8601: `yyyy-MM-ddTHH:mm:ssZ` (the `T` separator and trailing `Z` for UTC are required — a space-separated `yyyy-MM-dd HH:mm:ss` fails with `'…' is not a valid value for the type xsd:dateTime`). The source is in Eastern Time (EST/EDT, `America/New_York`). Localize the naive `M/d/yyyy H:mm` to Eastern, then convert to UTC. Example: `3/11/2026 11:46` (ET) → `2026-03-11T15:46:00Z` (UTC, during DST). |
| (literal `TRUE`) | `MonitorBase_Indicator__c` | boolean | Flag that flips the lead to "MonitorBase-active". This is NOT `MonitorBase_Alert__c` — the boolean is `MonitorBase_Indicator__c`. |

### Output CSV shape (4 columns, API-name headers)

```
Id,MonitorBase_Alert__c,MonitorBase_Alert_Date__c,MonitorBase_Indicator__c
00QQg00000YUS1j,"Term Reduction: MBai12001 - …",2026-03-11 11:46:00,TRUE
```

### Loading tool

The user runs this through **Salesforce Inspector** (Chrome extension), not the Data Import Wizard:
- Action: **Data Update**
- Match field: **Id**
- API-name headers map directly to fields (Inspector doesn't need display labels).

Why Inspector for this and not the Wizard: Inspector handles the 15-char ID match cleanly and is faster for these small recurring batches (typical export is 50–100 alerts).

### Common pitfalls
- **Don't confuse `MonitorBase_Alert__c` (textarea) with `MonitorBase_Indicator__c` (boolean).** The instruction "set MonitorBase_Alert__c to true" is almost always a typo — the boolean indicator is the one that gets flipped.
- **Datetime format matters.** Salesforce won't parse `3/11/2026 11:46` directly; convert to `2026-03-11 11:46:00`.
- **Strip wrapping quotes** from numeric ID columns (`Alert ID`, `Prospect ID` in the source come as `'"503172080249248518"'`). Not used in the update file, but worth knowing if you ever need them.
- **Normalize smart-character noise in `Alert Intel`.** MonitorBase ships the text with curly typographic characters (right single quote `U+2019`, smart double quotes, em/en dash, ellipsis, NBSP, zero-width chars) that render as garbled symbols in Salesforce. Replace before writing the CSV. Minimal table:
  - `‘ ’` → `'` (U+2018, U+2019)
  - `“ ”` → `"` (U+201C, U+201D)
  - `– —` → `-` (U+2013, U+2014)
  - `…` → `...` (U+2026)
  - NBSP `U+00A0` → regular space
  - Zero-width chars `U+200B`, `U+200C` → removed

## Lead imports (Data Import Wizard / CSV)

Conventions for building Lead import CSVs for this org, established 2026-05-20.

### Record type & owner IDs (verified in prod)

| Thing | Id |
|---|---|
| Lead record type `Borrower` | `012Kb000000RpDAIA0` |
| Lead record type `Realtor` | `012Kb000000RpDDIA0` |
| Lead record type `Broker` | `012Kb000000RpDBIA0` |
| Lead record type `Loan Officer` | `012Kb000000RpDCIA0` |
| User — Jonathan Valenzuela (Loan Officer) | `005Qg00000UKNdWIAX` |
| User — Adriana Gonzalez (Loan Officer) | `005Qg00000TxaOXIAZ` |
| Lead record type `SiMo BPO` (`SiMo_BPO`, added 2026-07-02) | `012Qg000003xvgTIAQ` |
| Opportunity record type `SiMo BPO` (`SiMo_BPO`, added 2026-07-02) | `012Qg000003xvgUIAQ` |

> **SiMo BPO record type (2026-07-02):** cloned from Realtor on both Lead and Opportunity — same business process ("Realtor") and picklist assignments. Layouts `Lead-SiMo BPO Layout` / `Opportunity-SiMo BPO Layout` are copies of the Realtor layouts. Visibility: **Admin profile only** (deliberate — expand when the user says who works these). Purpose: Customer.io workspace split — the SimoSolutions Group CIO workspace syncs ONLY this record type; the Supreme Lending CIO workspace (164380) syncs 503/623 will exclude it (`RecordTypeId != ...`). See `CIO Workspace/CIO_SimoSolutions_Workspace_Replication_Spec.md`.
>
> **SiMo BPO database build (EXECUTED 2026-07-09):** the SiMo BPO working set was created by `CloneMMIToSimoBPO.cls` (batch, + `CloneMMIToSimoBPOTest`) — ALL output records are **Leads** with the SiMo BPO RT, including ones derived from Opportunities. Sources: MMI-sourced Loan_Officer/Realtor Leads (unconverted, minus 272 pre-flagged duplicate-discards) and Opportunities (all stages; mapped to Leads: Email__c→Email, Phone__c→Phone, Name split First/Last, Status=New, Company=NMLS_Company__c∥Name). Every new Lead: Owner = `sf integrations`, `Title` = "Realtor"/"Loan Officer" (origin RT), consent flags (DoNotCall, HasOptedOutOfEmail, SMS_Opt_In__c, tdc_tsw__SMS_Opt_out__c) reset false (deliberate new-entity decision), `Cloned_From_Id__c` = source Id (00Q=from Lead, 006=from Opp). **Result: 35,829 SiMo BPO leads (33,910 lead-derived + 1,919 opp-derived); 1,752 rejected as intra-set duplicates by the LeadPhoneTrigger/DetectDuplicateHandler + `not_allow_to_create_non_borrowers_leads` flow (free dedupe). Zero SiMo BPO Opportunities exist by design** — they come only from lead conversion, via flow `SiMo_BPO_Lead_Convert_Sync` (stamps SiMo BPO Opp RT + copies Title→Title__c on convert). Re-running the batch is safe (idempotent on Cloned_From_Id__c). Gotchas hit: LeadDataQualityTrigger enqueues 1 Queueable/lead (>50/txn = fatal) — bypassed because runner holds `Bypass_Lead_Automation` perm set; `Opportunity.First_Name__c` is a formula (not createable → must be added to dynamic queries explicitly); scripts in `scripts/clone_mmi_simo_bpo_*.apex`.
>
> **Record pages (added 2026-07-06 — GOTCHA):** a page layout + profile layout-assignment is NOT enough for a new record type in this org. The New/Edit modal renders from the **Dynamic Forms record page** assigned to the record type (org has Dynamic Forms create active), so a new RT with no record-page assignment falls back to a near-empty default page — symptom: New Lead modal showed only a section literally labeled "Section" with the Record Type field, even though `ProfileLayout` assignment was verified correct. Fix: cloned the Realtor pages → FlexiPages `Lead_Record_Page_SiMo_BPO` (from `Lead_Record_Page11` "Realtor BDs") and `Opportunity_Record_SiMo_BPO_Three_Column` (from `Opportunity_Record_Realtor_Three_Column1`), assigned via `profileActionOverrides` (View, Large+Small, profile Admin, recordType `Lead.SiMo_BPO` / `Opportunity.SiMo_BPO`) in BOTH apps `standard__LightningSales` (HOMESÍ-B2B) and `HOMESB2C` (HOMESÍ-B2C). If more profiles get this RT later, add matching profileActionOverrides per app. Realtor's own assignments span ~20 profiles per app — mirror those if visibility is expanded.

### Borrower lead import rules (user-confirmed)

- **Branch is required.** Always include `Branch__c`. If the source file doesn't specify a branch, ASK the user — do not guess. (Jonathan Valenzuela's leads use Branch `716`; Adriana Gonzalez's earlier batch used `710` — confirm per import.)
- **Do NOT include `Lead Importance` (`Lead_Importance__c`) in the import file.** Leave the column out entirely.
- **Do NOT include `Status` in the import file.** Leave it out — it defaults on its own.
- **If setting `Referred_By__c` (Contact lookup), you MUST also set `Referred_Date__c`.** Validation rule `Referred_By_Required_For_BD_Borrower` rejects the row with: *"For Borrower leads, if Referred By is set then Referred Date is required."* For a referral-database import, set Referred Date to today's date (or the date the referrer handed over the list) on every row. This was missed once on the Amitay Huerta batch — don't repeat.
- Minimum columns to build: `First Name`, `Last Name`, `Company`, `Email`, `Phone`, `Branch`, `Lead Source`, `Owner ID`, `Record Type ID` (+ `Notes`, `State/Province`, co-borrower fields as available, and `Referred By ID` + `Referred Date` together-or-not-at-all).

### General CSV-build conventions

- **Use Salesforce display-name (label) headers, not API names** — the user imports via the Data Import Wizard, which matches on labels. Key label mappings: `LastName`→"Last Name", `LeadSource`→"Lead Source", `Lead_Importance__c`→"Lead Importance", `Branch__c`→"Branch", `Notes__c`→"Notes", `OwnerId`→"Owner ID", `RecordTypeId`→"Record Type ID", `State`→"State/Province", `CoBorrower_FirstName__c`→"CoBorrower FirstName" (likewise LastName/Email/Phone).
- **Phone format:** normalize to `+1 (XXX) XXX-XXXX` (matches how the org stores phones).
- **Company:** concatenation of first + last name ("First Last") unless the user says otherwise.
- **Name split:** first word = First Name, remainder = Last Name (unless the user says otherwise). Title-case ALL-CAPS source names.
- **Co-borrowers:** for two-person rows, load the second person into `CoBorrower_FirstName__c` / `CoBorrower_LastName__c` / `CoBorrower_Email__c` / `CoBorrower_Phone__c` (do NOT create a separate Lead).
- **Always dedupe-check before import:** query existing Borrower leads by `Email IN (...)` and `Phone IN (...)` and drop/flag any already present.
- **Junk-data sentinels:** blank out obvious placeholder phones (e.g. `123-456-7890`, all-same-digit numbers) so they don't become bad match magnets — same rationale as the LOS placeholder filter in `OpportunityUpdater`.

### `LeadSource` picklist is NOT restricted

Importing a value not in the standard value set works fine — the value is stored on the record even though it won't appear as a selectable dropdown option. Precedent: `Juseth Database` (1,036 leads) and `Jonathan Database` are used this way. To make a value selectable in the UI, an admin must add it under Setup → Lead → Fields → Lead Source.

### Borrower Lead active validation rules (relevant to imports)

- `LeadSource_Required_Borrower` — Lead Source required for all Borrower leads.
- `Check_Field_Lead_Importance_Borrower` — references Lead Importance for Borrower record type (user nonetheless directs that the import file omit this column).
- `branch_mandatory_validation_rule` — Branch required when status moves into Discarded/On-hold/Working/Qualified or when Branch is cleared.

## Production Support (Nila + Adriana) — access + notes (2026-07-10)

**Branch visibility via criteria sharing rules** (Opportunity OWD is Private, so criteria rules grant access). Two public groups + two `sharingCriteriaRules` on Opportunity, `accessLevel Edit` (Read/Write), `includeRecordsOwnedByAll true`:
- Group `Production_Support_Nila` (member: Nila Granadillo `005Qg00000UyVu5IAF`) ← `Production_Support_Nila_Branches`: `Branch__c equals 760,707`.
- Group `Production_Support_Adriana` (member: Adriana **Cervantes** `005Qg00000UyX6HIAV` — there are 4 Adrianas, this is the Agent Loa On-Demand one) ← `Production_Support_Adriana_Branches`: `Branch__c equals 703,724,728,733,770,716,710,776,Affinity`.
- Group membership is NOT in the `Group` metadata — created via `GroupMember` inserts (connector). Criteria sharing rules can only share to groups/roles, not individual users, hence the per-person groups.

**Production Support Note (Latest Note + Note History pattern, same as LOA Work Items):**
- `Opportunity.Prod_Support_Note__c` Text(255) — the writable "latest note" (existing `Opportunity.Notes__c` LTA(40000) was already taken, so namespaced).
- `Opportunity.Prod_Support_Note_History__c` LTA(32768) — append-only history, newest on top.
- Flow `Append_Prod_Support_Note_History` (before-save, CreateAndUpdate, Opportunity, v1 active) — when `Prod_Support_Note__c` IsChanged and non-blank and history < 30000 chars, prepends `[<CurrentDateTime> GMT - First Last] <note>\n\n<old history>` via textTemplate. Modeled on `Sync_Mortgage_Condition_Completion`.
- FLS: Admin (both editable), Agent Loa On-Demand (Note editable, History readable-only — flow writes it in system context).
- Added as a **column in the `Production Support` report** (`00OQg00000HZbqvMAD`, Pipeline Management folder) right after `Stat_Closing_Risk__c`. Text(255) is inline-editable in reports (unlike the LTA history) — Production Support can type notes directly in the report.
- Added to the classic **Opportunity-Borrower Layout** "Loan" section next to `Healthiness__c` (the qualitative Delayed/On Track status). NOTE: `Stat_Closing_Risk__c` is NOT on the classic layout or the `Opportunity_Record_Borrower_Three_Column` flexipage (that page is pure Dynamic Forms). The classic-layout placement is what enables report inline editing (gotcha 28); if a Dynamic-Forms Lightning page needs the field shown on-record, add it there as a `fieldInstance` too.

## Healthiness auto-fill from Stat Closing Risk (2026-07-13)

**`Opportunity.Healthiness__c` (qualitative, manually-editable picklist) now auto-defaults from the `Stat_Closing_Risk__c` formula when blank.** Two prerequisites made the values line up:

- **Picklist rename:** `Healthiness__c` value **`Healthy` → `On Track`** (deployed via the field's `valueSet`). Value set is now **On Track / Delayed / Out of Scope**, matching what `Stat_Closing_Risk__c` returns (`On Track` / `Delayed` / `Out of Scope` / blank) so the copy is a clean 1:1. Safe rename — 0 records used `Healthy` and no metadata referenced it. (Data at rename time: 18 Delayed, 4 Out of Scope.) **Selectability caveat:** record types that use the full value set get `On Track` automatically; if any Opportunity RT has an explicit Healthiness picklist subset, add `On Track` there for manual UI selection. Flows/Apex can set it regardless of RT assignment.
- **Flow `Copy_Stat_Risk_To_Healthiness` (v1 active).** **After-save** (NOT before-save — a before-save flow can't read the `Stat_Closing_Risk__c` formula reliably; deploy flagged "field isn't supported" for RecordBeforeSave). Entry: `RecordTypeId = 012Kb000000RpDEIA0 (Borrower) AND Healthiness__c IsNull true AND Stat_Closing_Risk__c IsNull false`, `CreateAndUpdate`. Action: `recordUpdates` on `Id = $Record.Id` setting `Healthiness__c = $Record.Stat_Closing_Risk__c`. Only fills when blank (never overwrites a set Healthiness); once set, the IsNull filter fails so no recursion/re-fire.
- **Backfill:** `scripts/backfill_healthiness_from_stat.apex` fills the ~107 existing OPEN Borrower loans that had blank Healthiness + a Stat value. Idempotent. **User must run it** (`sf apex run -f scripts/backfill_healthiness_from_stat.apex -o prod`).

## `Needs_Agent__c` / `Needs_Agent_Date__c` REPURPOSED for Borrower Follow-Up (2026-08-24)

**These two fields were built for a different, abandoned project ("HOMESI Copilot") and their metadata described behaviour that is now deliberately NOT what is built.** Read this before trusting the field descriptions in an older org copy.

- **Original design (dormant, never used):** `Needs_Agent__c` set by "HOMESI Copilot" when AI detected *attorney mention, regulator threat, cancellation threat, severe distress*. `Needs_Agent_Date__c` **overwritten on each new escalation** and **persisting after the flag was cleared**, for stale-escalation trending.
- **Proof it was never live:** in PROD on 2026-08-24, `SELECT COUNT(Id) FROM Opportunity WHERE Needs_Agent__c = true` → **0**, and `Needs_Agent_Date__c != null` → **0 rows**. No data to migrate, no report to break.
- **User decision 2026-08-24: repurposed for the Borrower Follow-Up system**, with the OPPOSITE date semantics: **write once on first raise, clear on resume** — i.e. "waiting since", so an escalation queue can be aged and sorted oldest-first. The old overwrite-and-persist behaviour cannot express waiting time, which was the whole point of the field.
- **Field descriptions and inline help on all four fields were rewritten** to state the real behaviour and to note the repurpose date. Leaving metadata that described the old contract is how the next person gets misled.
- **`Lead.Needs_Agent_Date__c` did not exist** — only Opportunity had it. Created for parity so Lead escalations can be aged too. **`Opportunity.Needs_Agent_Date__c` already existed in prod; it did NOT exist in staging** (reverse drift again).
- **Residual risk, accepted:** the flag is a single boolean shared by whatever raises it. If a risk-detection system is ever built, an attorney threat and a "what are my closing costs?" question become indistinguishable in the same list view. A `Needs_Agent_Reason__c` / source field is the fix; **not built**.
- **Pre-existing conflict this exposed:** `Resume_FUR_On_WorkItem_Complete` (active in prod) unticks `Needs_Agent__c` when an AI Follow-Up work item is completed. If another system ever raises that flag on the same record, our flow will clear it. Harmless while nothing else writes it.

### The two flows that maintain it — `Set_Needs_Agent_Date_Opp` / `Set_Needs_Agent_Date_Lead`

**Deliberately built in Salesforce, not n8n.** A before-save flow makes the invariant true for *every* writer — n8n, an agent, a future process — and needed no workflow change. Same reasoning as `Clear_Next_Touch_On_FUR_Stop`. Putting it in n8n would also have required the escalation sub-workflow to first read the current flag value to know whether it was the first raise.

- **Before-save**, `recordTriggerType Update`, entry filter `Needs_Agent__c IsChanged = true` (so **no** `doesRequireRecordChangedToMeetCriteria` — the two are mutually exclusive, gotcha 23). Before-save means no extra DML and no recursion.
- Decision `decFlagDirection`: rule 1 = flag **true** AND date **IsNull** → assign `$Flow.CurrentDateTime`; rule 2 = flag **false** → assign a null DateTime variable (`varNullDateTime`) to clear it; **default has no connector** → a flag already stamped and still true is left alone. That default branch is what preserves "waiting since" across repeat escalations.
- Reads and writes **only direct fields of the triggering record** — no cross-object references in entry criteria (gotcha 30, the 2-day prod outage).
- **VERIFIED LIVE IN STAGING 2026-08-24**, four cases on real records: `false→true` with blank date stamped it (Opp `17:43:08Z`, Lead `17:44:10Z`); `true→false` cleared it to null; **a repeat update that changed another field on the same save while the flag stayed true left the date untouched** (this is the load-bearing test — it proves the record really saved and the criteria really evaluated, yet the clock did not move); and every Opportunity save succeeded, confirming a new before-save flow on that object is not breaking saves.

### 🔴 GOTCHA — `FlowCondition` uses `<rightValue>`; `RecordFilter` uses `<value>`

Both flows failed to deploy first time with `Error parsing file: Element {...}value invalid at this location in type FlowCondition`. Inside a `<decisions><rules><conditions>` block the comparison element is **`<rightValue>`**. Inside `<start><filters>` (and other record filters) it is **`<value>`**. They look identical and are not interchangeable. The error names the *type* (`FlowCondition`), which is the clue to which one you are in.

### DEPLOYED TO PROD 2026-08-24 ✅

- Field descriptions/help rewritten on all four fields. **`Lead.Needs_Agent_Date__c` already existed in prod** (`00NQg0000097LTx`, `created:false`) — see the FieldDefinition gotcha below. So all four fields pre-existed; only the metadata text changed.
- Flows `Set_Needs_Agent_Date_Opp` (`301Qg00000zPMLfIAO`) and `Set_Needs_Agent_Date_Lead` (`301Qg00000zPMLeIAO`) deployed, landed **Draft**, then activated via 2-phase FlowDefinition. Both `IsActive = true`.
- Admin FLS read+edit confirmed on all four fields via `FieldPermissions` on PermissionSet `0PSKb0000019iVGOAY`.
- **PROD SMOKE TEST PASSED:** a save on an **open Borrower Opportunity** (`006Qg00000p1jc2IAA`, Negotiation) succeeded with the new before-save flow active, and correctly did not fire (`Needs_Agent__c` false→false = no change). This is the load-bearing prod check — the gotcha-30 failure mode throws `UNKNOWN_EXCEPTION` on exactly this shape (open opp, not closed), so a clean save here is what proves the flow is safe on prod's much heavier Opportunity automation stack.
- **Still outstanding:** place both fields on the Opportunity classic layout + the "Opportunity Record Borrower - Final" Dynamic Forms page; FLS steps 2+ for the 13 human profiles.

### 🔴 GOTCHA — `FieldDefinition` SILENTLY OMITS FIELDS THE RUNNING USER HAS NO FLS ON

Bit this project **twice in one session**, both times producing a confident but wrong "the field does not exist in prod" conclusion:
- `Opportunity.Needs_Agent__c` — gap analysis said missing; deploy returned `created:false` against pre-existing `00NQg0000097LTz`.
- `Lead.Needs_Agent_Date__c` — same story, pre-existing `00NQg0000097LTx`.

Root cause: `FieldDefinition` (and `SELECT <field> FROM <obj>`, which returns `INVALID_FIELD: No such column`) reflect the **querying user's field-level security**, not the org's schema. An admin with no FLS on a field cannot see it by either method, and both failure messages read exactly like "the field was never created."

**RULES:** (a) a deploy's `created: true|false` is the only authoritative existence check — trust it over any query; (b) `INVALID_FIELD: No such column` means *"missing OR no FLS"*, never just "missing"; (c) when auditing a target org before a deploy, grant yourself FLS first or accept that absence is unproven. This is also why the old HOMESI Copilot fields were invisible: they were deployed years ago with no FLS ever granted.

## Converted-Lead re-point — `Repoint_FUR_On_Lead_Convert` flow (2026-08-10, staging)

Closes the Borrower Follow-Up "converted Lead" gap. Record-triggered flow on **Lead**, after-save Update, entry `IsConverted = true AND ConvertedOpportunityId != null` (+ `doesRequireRecordChangedToMeetCriteria` so it fires only at the conversion transition; both are DIRECT Lead fields — avoids gotcha #30). Two `Update Records`-by-criteria elements, system context (no FLS concern):
- **Repoint FURs:** `Follow_Up_Request__c WHERE Lead__c = $Record.Id` → set `Opportunity__c = $Record.ConvertedOpportunityId`, clear `Lead__c`.
- **Repoint Work Items:** `Mortgage_Condition__c WHERE Lead__c = $Record.Id` → same.
Now that `Mortgage_Condition__c` carries BOTH `Lead__c` and `Opportunity__c`, the old "migrate Requested_Document rows into conditions" step is unnecessary — `Requested_Document__c` hangs off the FUR, which now points at the Opp, so it follows automatically. Active on deploy (staging auto-activates flows). **Clearing `Lead__c` uses an empty `<stringValue>` inputAssignment — confirm at test that the lookup actually nulls (if not, the field just stays populated, harmless since `Opportunity__c` drives `isOpp`).** NOT YET LIVE-TESTED (needs a real Lead conversion — `IsConverted` can't be set via the data API; convert in UI or via Apex `convertLead`). PROD cutover: deploy this flow to prod too.

## Lead Work Items — Task-only work items on Leads (2026-08-05, staging + PROD)

Extends the LOA Work Items system (`Mortgage_Condition__c`) so users can create **Task-record-type** work items attached to a **Lead** instead of an Opportunity. Sales agents work Leads with Tasks only (no mortgage conditions, no LOA milestones). **Access is OPEN TO ALL 13 human working profiles** (not role/title-gated) — this is the deliberate model for this feature, distinct from the LOA-only conditions/milestones.

**What shipped to PROD 2026-08-05 (all verified):**
- **`Mortgage_Condition__c.Lead__c`** — Lookup(Lead), `relationshipName Work_Items`, `relationshipLabel "Work Items"`, `deleteConstraint SetNull`. The parent field for Lead work items (mirrors `Opportunity__c`).
- **`MortgageChecklistController`** — `getConditions(Id)` is parent-aware: `String.valueOf(id).startsWith('00Q')` → query `WHERE Lead__c = :id`, else `WHERE Opportunity__c = :id`. `getMyOpenMilestoneItems()` SELECT adds `Lead__c, Lead__r.Name`. Deployed with `RunLocalTests` (the 17 previously-failing prod tests were fixed by the user in a separate session — **204 tests / 0 failures at deploy**, so RunLocalTests is viable in prod again going forward).
- **`mortgageChecklist` LWC** — title "LOA Work Items" → **"Work Items"**; `targetConfig` now includes `<object>Lead</object>` so it's droppable on Lead record pages; `isLead`/`showConditions`/`showOppEmpty`/`showLeadEmpty` getters; Lead helper text "Create your lead tasks here." + Lead empty state "No tasks yet."
- **`myWorkItems` LWC (utility bar)** — parent display is generic now: `hasParent = hasOpp || hasLead`, `parentName`/`parentUrl` resolve Opportunity **or** Lead (`Lead__r.Name` / `/`+Lead__c). Previously a Lead task showed as "Personal item"; now shows the Lead name + link. (Template gate changed `item.hasOpp` → `item.hasParent`.)
- **`Add_Work_Items` flow (v8 active in prod)** — **Option A**: Screen 1 asks "Is this Work Item for a Lead or an Opportunity?" (`Target_Object` radio). Opportunity → existing Task/Conditions choice + `Opp_Lookup` (both `visibilityRule` Target_Object=Opportunity). Lead → `Lead_Lookup` (`flowruntime:lookup`, fieldApiName `Lead__c`, objectApiName `Mortgage_Condition__c`, visibilityRule Target_Object=Lead) → routes to `Screen_Task` (Decision `Is_Lead`). `Create_Task_Item` sets `Lead__c = Lead_Lookup.recordId`. `Get_Condition_RT` filters `DeveloperName='Task'` so Lead items get the **Task** RT (shows in the widget Tasks band). Prod landed it Draft → **2-phase FlowDefinition activation** (activeVersionNumber=8).
- **Access grant (14 partial profiles, objectPermissions-only + recordTypeVisibilities + fieldPermissions — safe merge):** 12 profiles that lacked the object (`Agent`, `Agent Recruiter`, `Agent Sales`, `Agent TPO`, `Branch Manager`, `Branch Manager AA084`, `LO Profile`, `LOA Profile`, `Only_assignment`, `Sales agent Profile`, `Supervisor`, `Supervisor Sales`) got **Mortgage_Condition__c R/C/E (no Delete)** + **Task RT visible+default** + **Lead__c FLS r/e**. `Agent Loa On-Demand` + `System Administrator` (already had the object) got **Lead__c FLS r/e** only. **Gotcha reconfirmed: even System Administrator needed Lead__c FLS** — the `flowruntime:lookup` in the flow enforces FLS, so without it the Lead lookup errored "you don't have access to this field" for everyone (this was the first staging test failure). Side folder `wiaccess/profiles/`.

**Why the controller works even for profiles without full FLS on every field:** `MortgageChecklistController` is `without sharing` AND Apex SOQL doesn't enforce FLS by default (no `WITH SECURITY_ENFORCED`), so the widget reads/writes all fields in system context regardless of the running user's per-field FLS. The only FLS-sensitive surface is the `flowruntime:lookup` on `Lead__c` in the Add flow — hence Lead__c FLS on all profiles.

**Full FLS grant (2026-08-05, completed same day — side folder `wifls/profiles/`):** the 12 newly-granted profiles also got the **complete 21-field FLS set mirrored from `Agent Loa On-Demand`** — 14 editable (`Category__c`, `Condition_Name_LTA__c`, `Condition_Name__c`, `Document_URL__c`, `Due_Date__c`, `Notes__c`, `Opportunity__c`, `Sort_Order__c`, `Agent_Role__c`, `Assigned_Date__c`, `Completed_Date__c`, `Latest_Note__c`, `Priority__c`, `Lead__c`) + 7 read-only formula/rollup (`Is_Complete__c`, `Borrower_Email__c`, `Borrower_Phone__c`, `Buyers_Agent_Name__c`, `Buyers_Agent_Phone__c`, `Listing_Agent_Name__c`, `Listing_Agent_Phone__c`). So fields render for these profiles on the tab, list views, and reports — not just through the widget. Built by querying `FieldPermissions WHERE Parent.Profile.Name = 'Agent Loa On-Demand'` and replicating.

**Still OPEN (as of 2026-08-05):**
- **On-record widget placement** — the "Work Items" component (`c:mortgageChecklist`) is droppable on Lead pages but was NOT yet placed on any of the **10 Lead record pages** (main Borrower page = `Lead_Record_Page_Three_Admins_Borrower` "Lead Record Borrower - Final"; BDs = `Lead_Record_Page_Three_Column1`; Realtor/LO/Broker/SiMo BPO variants exist). Left to the user to drag onto the right page(s) in App Builder (profile→page assignment is ambiguous; metadata edit of these large pages is risky). Until then, users create + see Lead tasks via the **utility bar** `myWorkItems` item (present on HOMESÍ-B2B `LightningSales_UtilityBar` + HOMESÍ-B2C `HOMES_B2C_UtilityBar`).
- ~~Staging still holds the 8 buggy-v1 LOA2 UW-stage flows~~ **RESOLVED 2026-08-06:** staging synced with prod — all UW-stage flows (create + close) now on the `RecordTypeId`-fixed versions (v2 active). Staging's Borrower Opp RT Id is identical to prod's (`012Kb000000RpDEIA0`), so the prod flow files were portable as-is.

## Gotcha: DUPLICATE "System Administrator" profile in prod (2026-08-05)

Prod has **TWO profiles both named "System Administrator"**: `00eKb000000aw4EIAQ` (the one the **It Support / m.rodriguez** admin user actually logs in on — its owned PermissionSet is `0PSKb0000019iVGOAY`) and `00eQg00000M4WMTIA3`. **Metadata profile deploys resolve by NAME**, so deploying `profiles/System Administrator.profile-meta.xml` lands on `00eQg…`, NOT the login profile `00eKb…`. Symptom this caused: after granting `Mortgage_Condition__c.Lead__c` FLS via a "System Administrator" profile file, the admin STILL hit the `flowruntime:lookup` "you don't have access to this field" error in the Add Work Items flow, because the running user's real profile (`00eKb…`) never got it. **Fix: write FLS/perms straight to the correct profile's owned PermissionSet by ID** — insert a `FieldPermissions` row (`ParentId = 0PSKb0000019iVGOAY`, `SobjectType`, `Field`, `PermissionsRead/Edit`) via the data API (hosted SF MCP `createSobjectRecord`), which targets the profile unambiguously by PermissionSet Id instead of by name. Custom-named profiles (Agent Sales, Sales agent Profile, the other 11) are unique, so name-based metadata deploys hit them correctly — only the standard "System Administrator" name is duplicated here. Worth eventually cleaning up the duplicate profile, but leave it for now.

## ROOT CAUSE of the duplicate "System Administrator" profile — SOLVED 2026-08-11

**The standard admin profile's Metadata API fullName is `Admin`, NOT "System Administrator."** Deploying a file named `System Administrator.profile-meta.xml` does not update the admin profile — it **CREATES A BRAND-NEW CUSTOM PROFILE** with that label (observed live in staging: `created:true`, new Id `00eEm00000BvdkfIAB`), and any FLS in that file lands on the new empty profile. This is almost certainly **how prod acquired its second "System Administrator" (`00eQg00000M4WMTIA3`)** — someone deployed a profile file named by label. It also explains the earlier symptom where admin FLS "deployed successfully" and the admin still could not see the field.

- **RULE: name the file `Admin.profile-meta.xml`.** Verified: deploying that returns `fullName:"Admin"`, `id:00eKb000000aw4EIAQ` (the real login admin), `created:false`.
- Equally safe: write `FieldPermissions` rows straight to the real admin profile's owned PermissionSet `0PSKb0000019iVGOAY` via the data API.
- The junk profile created during this test was deleted (0 users assigned); staging is back to one System Administrator.
- **Prod cleanup candidate:** `00eQg00000M4WMTIA3` is very likely the accidental duplicate. Profile Ids survive sandbox refresh, so `00eKb000000aw4EIAQ` is the standard Admin in both orgs.

## `Preferred_Language__c` (Lead + Opportunity) — deployed to STAGING 2026-08-11

Picklist `EN`/English + `ES`/Spanish, **unrestricted**, not required, no default. Purpose: the Borrower Follow-Up engine must know the borrower's language for Opportunity condition chases, where there is NO free text to detect from (conditions are internal English UW jargon, which is why WF-1 Path A hardcoded `Language__c: "EN"`). **Design rule: AI intake SEEDS this field only when blank; a human's choice always wins** — because language detection on a staff note detects the language the *staff member typed in*, not the borrower's language (English notes about Spanish-speaking borrowers are the norm here).
- Placement decision: beside the borrower's Email/Phone in the contact section of the classic **Opportunity-Borrower Layout** + the matching `Opportunity_Record_Borrower_Three_Column` flexipage, and beside the request box on the Lead. Classic layout matters for report/list inline editing (gotcha 28) so language can be bulk-set from a filtered list.
- **STAGING HAS A 6th RECORD TYPE, `Refinance`, on BOTH Lead and Opportunity** (previously undocumented; all RTs active). Values were assigned to all 12 RTs (Borrower, Broker, Loan_Officer, Realtor, SiMo_BPO, Refinance × 2 objects). RT headers require `businessProcess` + `label`; Refinance maps to a `Refinance` business process on both.
- FLS granted read+edit on 10 profiles + the `Borrower_Follow_Up_Integration` permset. **4 of the "13 human profiles" were SKIPPED — `Agent Recruiter`, `Agent TPO`, `Branch Manager AA084`, `Supervisor Sales` have ObjectPermissions on `QuickText` ONLY in staging (zero Lead/Opportunity access)**, so FLS would error. These are real working profiles in PROD and must be included there. Their partial profile files are already written.
- Reusable files: fields in the main tree; side folder `preflang/` holds 12 recordTypes + 14 `fieldPermissions`-only profile files.
- Used the data API for the permission set rather than a partial permset file, since **permission-set deploys can REPLACE rather than merge.**

## Branch picklist unified across Lead + Opportunity (2026-08-07, PROD)

**Decision (user): keep Branch UNRESTRICTED, sync the value sets — did NOT go Global Value Set.** Reason a GVS was rejected: a GVS is always *restricted*, and the Encompass integration writes `Opportunity.Branch__c` (`OpportunityUpdater`) — a restricted set would reject any branch code not yet added, risking loan-update failures. So Branch stays local + unrestricted on each object.

- **Value-set sync:** `Lead.Branch__c` was a subset (75 values) of `Opportunity.Branch__c` (90). Added the 15 Opp-only values to Lead (`Affinity, DC047, DC049, DC051, ER041, ER045, GR052, JC004, JC010, JC023, JCA08, JCGR58, MCMB, Main, VP063`) so both objects now hold the **same 90 values**. 777 was already in both value sets. (Going forward this is still 2 places to add a new branch — the tradeoff of staying unrestricted; GVS would be 1 place but restricted.)
- **Record-type availability (this is what actually controls whether a value SHOWS):** assigned **all 90 values to all 10 record types** — Lead + Opportunity × {Borrower, Broker, Loan_Officer, Realtor, SiMo_BPO}. This is why 777 "wasn't showing" before — it was in the value set but not assigned to the RT. Side folder `rtbranch/`.
- **Gotcha reconfirmed (#29): a RecordType metadata retrieve does NOT return custom-picklist (`Branch__c`) assignments** — only standard ones (LeadSource, Industry, Rating, etc.). So you can't see current custom-picklist RT availability via retrieve; you deploy a `<picklistValues>` block with ALL values to set it. **RecordType picklist deploys MERGE per-picklist** — deploying a RT with only some picklists' blocks does NOT wipe the others (that's why adding just the Branch block to the retrieved files was safe for the other custom picklists).
- Picklist **value API names may start with a digit** (201, 777, 913…) — unlike field/object API names. Never the cause of a display issue.
- **Final state (2026-08-10): only 24 values kept ACTIVE, the other 66 DEACTIVATED** (old branch naming no longer in use). Active 24: `201, 203, 276, 700, 701, 702, 703, 707, 710, 716, 718, 721, 724, 728, 733, 741, 747, 760, 770, 776, 777, 913, Affinity, Recruitment`. Deactivating a value removes it from the dropdown + auto-drops it from RT assignments, while existing Lead/Opp records keep their old value (unrestricted field). Done on both Lead + Opp.
- **Staging synced 2026-08-10** (field value sets 24-active/66-inactive + the 24 active assigned to all 10 RTs). Staging had no SiMo_BPO record types — they were created by this deploy (header + Branch block only; minimal).

## NPPM auto-population — `Set_NPPM_From_Referral_Chain` (2026-08-20, PROD v3 active)

Before-save flow on **Opportunity**, `CreateAndUpdate`. Derives `NPPM_Realtor__c`, `Referred_By_NPPM__c` and `Strategy__c` from the referral chain using **record Ids only** (no name/email matching — the user explicitly pushed back on email matching: *"but if we have all ids on the records why use emails?"*).

Entry `filterFormula` (NOT filter items — needs `ISNEW()`/`ISCHANGED()`):
```
AND({!$Record.RecordTypeId} = "012Kb000000RpDEIA0",
    NOT(ISBLANK({!$Record.Referred_By__c})),
    OR(ISNEW(), ISCHANGED({!$Record.Referred_By__c})))
```

### The data model (how the hops actually work)
`Contact → Opportunity` hops use **`Opportunity.ContactId`**, which is **read-only and derived from the PRIMARY `OpportunityContactRole`** — you cannot write it (`INVALID_FIELD_FOR_INSERT_UPDATE`); flip `OpportunityContactRole.IsPrimary = true` instead. `Opportunity → NPPM__c` is via **`NPPM__c.Source_Opportunity__c`**. Realtor Opp RT = `012Kb000000RpDHIA0`. **Both NPPM roles qualify** — `NPPM__c.Role__c` holds `Realtor-NPPM` (6) and `Realtor-BD` (7); the user's own worked example (FRED A GOMEZ) is a **BD**, and they confirmed both count.

### ⚠️ TWO referral shapes — the 1-hop case is the majority and was the original bug
- **1-HOP (direct):** the Referred By contact **IS** an NPPM. Checked **FIRST** (`Get_NPPM_Direct` → `dec_NPPM_Direct` → `Set_NPPM_Direct`). **214 Borrower loans** as of 2026-08-20 (113 already tagged Yes by hand, 101 blank).
- **2-HOP (downline):** Referred By contact → their Realtor Opp → *that* Opp's Referred By → their Realtor Opp → NPPM. **25 loans.**

**The bug (v2, caught before it did damage):** the flow only modelled 2-hop. **12 of the 13 NPPM source opps have a BLANK `Referred_By__c`** (they sit at the top of the tree — only Miguel Ordoñez has an upline, Mariano Claudio). So on a direct referral the flow walked to the NPPM's own realtor opp, found no upline, hit the `Referrer_No_Upline` rule and stamped a **confident "No"** — clearing `NPPM_Realtor__c` on 113 correctly-tagged loans. Caught because a backfill-sizing query showed the 2-hop chain resolved only 25 loans while 143 were already tagged Yes. Verified zero `No` values existed in prod, so nothing was corrupted. **Lesson: when a chain-walk automation concludes "nothing above me qualifies", first ask whether the node you're standing on qualifies.**

### Element order (v3)
`Get_Referrer_Opp` → `dec_Referrer_Found` → **`Get_NPPM_Direct`** → **`dec_NPPM_Direct`** → (Yes: `Set_NPPM_Direct` → `dec_Affinity`) / (No: `dec_Referrer_Opp` → `Get_Upline_Opp` → `dec_Upline_Opp` → `Get_NPPM` → `dec_NPPM` → `Set_NPPM_Found` → `dec_Affinity`).

`dec_Referrer_Found` exists specifically so `Get_NPPM_Direct` never runs with a **null** `Source_Opportunity__c` filter value — a null-equals filter would match any NPPM row with a blank Source Opportunity and tag a random NPPM.

### Guardrails (user directive: *"assume all NPPM are well structured and do guardrails in case there is no Id linked"*)
Sets `No` **only on a confident negative** (referrer is not an NPPM AND their upline is not either, or the referrer has no upline). When a link is missing because the data is unstructured (contact has no Opportunity / no primary contact role), `dec_Referrer_Found` and `dec_Upline_Opp` defaults have **no connector** → both fields are left **untouched** rather than stamped with a false No. This is what protects the 113 hand-tagged direct referrals.

### `Strategy__c` is set HERE, not left to `Update_Strategy_Opps` — before-save ORDERING gotcha
`Update_Strategy_Opps` (before-save, Opportunity) maps `Referred_By_NPPM__c = Yes` → `Strategy__c = NPPM`. It kept landing on `B2B Strategy` anyway. **Root cause is NOT recursion** (the user's first guess) — **two before-save flows on the same object have no guaranteed execution order**, and each runs once per save, so `Update_Strategy_Opps` read `Referred_By_NPPM__c` while it was still null and fell through to its default. Fix: write Strategy inside this flow. `dec_Affinity` guards it — if `Affinity_Program__c = true` the rule has **no connector** so Strategy is left alone, preserving `Update_Strategy_Opps`' ranking of Affinity above NPPM.

### Data fixes made while building this
- `NPPM__c` source opps with null `ContactId`: 3 of 13. Fixed **FRED A GOMEZ** (`006Kb00000Kut2KIAR` → Contact `003Kb00001XmSxpIAF`) and **Walter Mena** (`006Kb00000Kut6yIAB` → `003Kb00001XmTATIA3`) by setting `OpportunityContactRole.IsPrimary = true`. **Jose Rodriguez (`006Qg00000MZSb9IAH`) has no ContactId AND no OCR at all** — left alone; the user suspects he may be wrongly flagged as an NPPM. His chain will never resolve until an OCR exists.
- Created NPPM records for Estefania Borns (`a1OQg000004DR89MAG`) and Laura Delgado (`a1OQg000004DR4vMAG`).

### Verified in prod (2026-08-20)
- 1-hop: Yecenia Donado `006Kb00000KuwQDIAZ` (Referred By = WALTER Mena) → NPPM Walter Mena `a1OQg0000045ZVuMAM` (Realtor-NPPM), Yes, Strategy NPPM.
- 2-hop regression: Manuel Elias Moreno `006Qg00000EZZSiIAP` (Referred By = Carlos Mesa → FRED) → NPPM FRED A GOMEZ `a1OQg0000045ZVtMAM` (Realtor-BD), Yes, Strategy NPPM.

### Lead twin — `Set_NPPM_From_Referral_Chain_Lead` (2026-08-21, PROD v1 active)

Same flow, triggering on **Lead** instead of Opportunity. The chain itself is unchanged — it walks Contact → Realtor **Opportunity** → NPPM__c regardless of what the starting record is, and `Lead.Referred_By__c` is the same Lookup(Contact). Only two things differ:
- Entry `filterFormula` uses the **Lead** Borrower RT `012Kb000000RpDAIA0`.
- **No Affinity guard.** `Lead` has NO `Affinity_Program__c` field (confirmed — zero fields matching `%ffinity%`), and `Update_Strategy_Field` (the Lead Strategy flow) has no Affinity rule either, so `Set_NPPM_Direct` / `Set_NPPM_Found` connect straight to `Set_Strategy_NPPM`.

**Strategy is written here too, for the same before-save ordering reason.** `Update_Strategy_Field` is before-save on Lead with entry `RecordTypeId = Borrower` only (no IsChanged filters), so it fires on EVERY Borrower lead save and its default branch writes `B2B Strategy`. Verified live: Julio Cabrera was sitting on `B2B Strategy` and flipped to `NPPM` only because this flow sets it directly.

**Fields already existed on Lead** (`NPPM_Realtor__c`, `Referred_By_NPPM__c`, `Strategy__c`, `Referred_By__c`) and are mapped Lead → Opportunity on convert. Nothing previously *populated* the two NPPM fields on Lead — `Update_Strategy_Field` only *reads* them. The 2,980 already-tagged Borrower leads were manual/import.

**Verified in prod (2026-08-21):**
- 1-hop: Julio Cabrera `00QKb00000cV2RjMAK` (Referred By = WALTER Mena) → NPPM Walter Mena `a1OQg0000045ZVuMAM` (Realtor-NPPM), Yes, Strategy NPPM (was B2B Strategy).
- 2-hop: Juan Cortes `00QQg00000J0zrmMAB` (Referred By = Carlos Mesa → FRED) → NPPM FRED A GOMEZ `a1OQg0000045ZVtMAM` (Realtor-BD), Yes, Strategy NPPM.

**Lead-side data at build time:** unconverted Borrower leads with `Referred_By__c` populated = **15,899** — 2,980 already `Yes` (all 2,980 also have `NPPM_Realtor__c`, so the tagging was complete not partial) and **12,919 blank**. That blank pile is ~60× the Opportunity scope; most will NOT resolve (the chain only reaches referrers connected to the 13 NPPMs). Size it with a query before any Lead backfill.

### "Owner is an NPPM" (hop 3) — CONSIDERED AND REJECTED 2026-08-21. Do not rebuild.
Asked twice (once for Opportunity, once for Lead): should the flow tag `NPPM_Realtor__c` when the record's **Owner** is an NPPM and there is no referral? **No — the case has zero records, because the org already handles it by convention: the NPPM puts THEMSELVES in `Referred_By__c`, which hop 1 already covers.**
- Only **3 users** carry `Title` in (`Realtor-NPPM`, `Realtor-BD`): Jose Boggio `005Qg00000TiTyTIAV`, Laura Delgado `005Qg00000UfNSQIA3`, Fred Gomez `005Qg00000TMKkAIAX` (inactive).
- Jose Boggio owns **160** unconverted leads; **all 160** have `Referred_By__c` = his own Contact `003Qg00000ohWEMIA2` (`Recruitment_Role__c = Realtor-BD`) and are correctly tagged Yes + NPPM_Realtor + Strategy NPPM via the 1-hop path. Laura and Fred own **zero** leads. Leads owned by these 3 with a blank Referred By: **0**. Same on Opportunity: **1** Borrower opp owned by the 3, already tagged.
- **No Id path exists from `User` to `NPPM__c`** — the object has only Brokerage/Email/Name/Phone/Role/Source_Opportunity/Owner. `Owner.Title` proves *that* someone is an NPPM, never *which* NPPM record. Email matching would fail anyway: User/Contact email is `jose.boggio@supremelending.com` while `NPPM__c.Email__c` is `dynrealteam@gmail.com`.
- **Owner is the wrong attribution key regardless:** `OwnerId` changes on reassignment/round-robin, so NPPM credit would evaporate (or get cleared by a re-fire) the moment a lead moves to an LO. `Referred_By__c` is a stable statement about origin.
- Note `Update_Strategy_Opps` / `Update_Strategy_Field` ALREADY cover the owner case **for `Strategy__c` only** (their NPPM rule is `Referred_By_NPPM__c = Yes OR Owner.Title = Realtor-NPPM OR Owner.Title = Realtor-BD`). They never populate the two NPPM fields.
- **If it ever becomes real** (realtor-user roster grows): add `NPPM__c.Salesforce_User__c` Lookup(User) (mirroring `Loan_Officer__c.Salesforce_User__c`), populate the handful of users by Id, then add hop 3 = `Get NPPM WHERE Salesforce_User__c = $Record.OwnerId`, checked LAST and gated on Referred By blank — and loosen the entry criteria, which currently requires `Referred_By__c` non-blank so the flow never runs on these records at all.
- **Residual risk accepted:** the convention is habit, not enforcement. A report of Borrower leads/opps owned by a Realtor-NPPM/Realtor-BD user with blank `NPPM_Realtor__c` would catch drift (should always be empty). Offered, not built.

### Dormant duplicate Strategy flows (delete candidates, 2026-08-21)
`Set_Strategy_NPPM_on_Lead` (`300Qg000012kdkfIAA`) and `Set_Strategy_NPPM_on_Opportunity` (`300Qg000012kdkgIAA`) are **both IsActive = false** and are narrower duplicates of logic already living in `Update_Strategy_Field` / `Update_Strategy_Opps` (they only do `Referred_By_NPPM__c = Yes AND Strategy != NPPM → Strategy = NPPM`). Safe to delete — if either were ever activated it would become a second competing before-save writer of `Strategy__c`. User deleting these manually.

### Open items
- **Backfill NOT run.** ~239 loans are in chain scope (25 two-hop already tagged + 214 direct, of which 101 are blank). The flow only fires on create or a `Referred_By` change, so existing loans stay as-is until touched. A no-op touch-save script would do it.
- **Staging sync NOT done** — prod-only; confirm staging even has `NPPM__c` + `Source_Opportunity__c` before deploying (the flow hardcodes prod RT Ids `012Kb000000RpDEIA0` / `012Kb000000RpDHIA0`, which have historically matched staging).
- Deploy emits a benign **Info** warning that `Get_Upline_Opp` may cause bulk performance issues (3 queries per record).

## LOA milestone NOTIFICATION EMAILS — ALL 12 live in PROD (10 on 2026-08-24, #4 + #5 on 2026-08-25). Source: "NOTIFICACIONES SALESFORCE" doc

Twelve notifications were specified; **all 12 are live**. Doc #3 was dropped (user: "no notification #3 needed"). #4 (Appraisal POD) and #5 (Rate Lock) were converted a day later so the first ten could be verified without disturbing the two emails that were already live to processors.

### #4 and #5 conversion (2026-08-25, prod `LOA2_Task_Appraisal_POD` v5 / `Lock_Rate_Locked_Email_Alert` v2)
Both already emailed **the Loan Processor only** and both gated the send on `Loan_Processor_Email__c` being present — #4 via an `r_HasEmail` decision, #5 via an entry-criteria filter. **Both gates were removed**, because with LO + LOA2 now on the list the notification must still go out when the processor email is missing (80% of loans). Subject/body replaced with the document's wording; recipients switched to the shared `fRecipients` formula.
- `Lock_Rate_Locked_Email_Alert` also had `doesRequireRecordChangedToMeetCriteria` swapped for **`Lock_Date__c IsChanged`**, and gained a `faultConnector` (it had none — a failed send would have blocked the Opportunity save). Its fault path lands on a terminal decision `dec_End`.
- **Known and accepted (user decision):** rate locks now generate **two** emails — #5 "Rate Locked - Please Review for COC" and #12a "COC Review (LE)" — because Encompass increments `COC_LE_Trigger__c` on the same event. Confirmed on 3 loans (Carlos Grajales 776002071111, Eugenio Gutierrez Cabrera 760002060704, Tule River: Daniel Gomez 700002073578), all of which locked on 8/24. User: *"its ok they will receive two alerts for the same event on rate locks."*
- Verified in prod on `Melquiades Test - 84651464644` with Test Mode toggled on for the duration of the test and off immediately after, so no real LO received a test email. Both rendered correctly with "Not assigned" for blank LOA2 and blank Loan Processor.

### Architecture decision — email lives INSIDE the milestone flows, ungated
User directive: *"for this emails triggers we need to send them anyways regardless if the LOA2 is assigned or not."* Entry criteria is flow-level, so an email inside an LOA2-gated flow can't be ungated. **User's solution (better than building 12 separate notification flows): remove `LOA2__c` from the ENTRY criteria and re-apply it as an in-flow decision (`dec_HasLOA2`) immediately before work-item creation.** Email fires for everyone; work item still only when LOA2 is set. Same end-state for work items, no new flows.

**Bonus the user spotted implicitly: this also kills the burst-on-LOA2-assignment vector.** With `LOA2__c` gone from entry criteria, LOA2 going blank→populated can no longer newly-satisfy the criteria set, so the flows stop firing on assignment. Combined with swapping `doesRequireRecordChangedToMeetCriteria` for `<date> IsChanged`, the entry criteria can now only be satisfied by the milestone date actually changing. Verified live in staging: assigning LOA2 fired the 3 unconverted flows but NOT the converted one.

### Per-flow shape (all 8 milestone flows + Close_On_CTC)
`Entry: Borrower RT + <date> IsChanged + not Closed Won/Lost` → `dec_HasRecipients` → `Send_Email` → `dec_HasLOA2` → dup guard → `Create Work Item`.

### 🔴 CRITICAL — every `Send_Email` MUST have a `faultConnector`
**A failing email action in an after-save flow ROLLS BACK THE RECORD SAVE.** Hit live in staging: setting `Appraisal_Received_Date__c` returned `CANNOT_EXECUTE_FLOW_TRIGGER — "Org-Wide Email provided is not valid"` and the Opportunity could not be saved at all. Same outage shape as gotcha #30. Every Send_Email now has `<faultConnector>` pointing at the next element, so a failed send degrades to "no email" instead of "no save". This matters in prod for: OWEA revoked, malformed address, and **the org's daily single-email limit** — any of which would otherwise stop users saving loans.

### `Notification_Settings__c` — hierarchy custom setting (test switch)
`Test_Mode__c` (Checkbox) + `Test_Recipient__c` (Email). When Test Mode is true, EVERY notification flow routes all recipients to Test_Recipient__c. Lets the whole suite be verified against one inbox and flipped live **without redeploying any flow**. Org-default record `a1RQg000005WcIbMAK`. **Test Mode is not an "off" switch — while on, real notifications are swallowed, not suppressed. To pause notifications properly, deactivate the flows.**

### 🔴 GOTCHA — an EMPTY text formula is NULL, so `NotEqualTo ""` does NOT detect "empty"
The `dec_HasRecipients` guard was originally `fRecipients NotEqualTo ""`. **That does not work.** A Salesforce text formula returning an empty string is stored as **null**, and in a Flow decision `null <> ""` evaluates **TRUE** — so the guard passed on loans with no recipients at all and the Send Email action was called with a null address. Live prod failure 2026-08-25 on `Irma Juarez Escalante - 747002076086` (`006Qg00000pZLfJIAW`), which has **no Loan Officer, no LOA2 and no Loan Processor email**; the error email even printed the value as `{!fRecipients} (null)`. **Fix: use the `IsNull` operator (`fRecipients IsNull false`), applied to all 12 notification flows.** Verified by stripping every recipient off the test loan and re-firing: save succeeded, no email, no error.

**Blast radius while it was broken: 15,201 open Borrower opps have all three recipient fields blank.** The `faultConnector` meant records still saved and work items were still created — the only symptom was a "Flow Error Details" email per occurrence. Without the fault connector this would have blocked saves on 15k loans.

### Recipients — 2 HARDCODED + LO + LOA2 + Loan Processor (updated 2026-08-25)
`fRecipients` formula, identical in every flow: test-mode branch first, else **two always-on hardcoded addresses — `pier.laino@supremelending.com` and `alejandra.murillo@supremelending.com`** — followed by `Loan_Officers__r.Email__c`, `LOA2__r.Email` and `Loan_Processor_Email__c`, each appended as `"," & addr` only when non-blank. User's rationale: *"so there is always a notification going out."*

**Consequence, accepted by the user:** the hardcoded pair means `fRecipients` can never be empty, so loans with no LO / no LOA2 / no processor email now DO generate a notification where they previously sent nothing. It also makes `dec_HasRecipients` permanently true — the guard is kept anyway so the flows stay safe if the hardcoded list is ever removed.

### ⚠️ REAL SCOPE of these notifications — only Encompass-fed loans, NOT the whole pipeline
**Only Opportunities with `Loan__c` populated AND `Lender__c LIKE '%Eve%'` ever have these milestone date fields written**, because Encompass is the only writer. Measured 2026-08-25:
- Open Borrower opps **in scope** (Loan # + Eve lender): **2,010**
- Of those, with **no LO, no LOA2 and no processor email**: **51**

An earlier note in this file said 15,201 loans had no recipients — that was the count across the ENTIRE open Borrower pipeline and is **not** the exposure for these flows; the vast majority of those 15k are early-stage records Encompass never touches, so their milestone dates never change and the flows never fire. Use the 2,010 / 51 figures when reasoning about notification volume or blast radius.

The earlier leading-comma-strip logic (`IF(LEFT(...,1)=",", MID(...,2,240), ...)`) was **removed** — with two literals always leading, no dangling separator is possible, and the old `MID(...,240)` cap risked truncating a long address list.

**Body includes `Branch: {!fBranch}`** on every notification (added 2026-08-25, right after the Loan # line; `BRANCH:` in the two COC bodies which use uppercase labels). `fBranch = IF(ISBLANK(TEXT(Branch__c)), "Not specified", TEXT(Branch__c))` — `Branch__c` is a picklist so `TEXT()` is required. Verified rendering "Branch: Affinity" on the prod test loan.

**Body uses `Loan_Processor__c` (Text NAME), NOT the email** — the name is populated on **424 of 452** in-processing loans (94%) while `Loan_Processor_Email__c` is on only **90 (20%)**. Blank → "Not assigned" (user's choice). **Consequence to fix at the integration: the processor is NAMED in ~94% of emails but can only RECEIVE ~20% of them.** Encompass isn't mapping `Loan_Processor_Email__c` for most loans. Coverage: LOA2 ~100%, LO 387/452 (86%), Processor 90/452 (20%).

### The 10 live notifications
| # | Subject | Trigger field | Flow |
|---|---|---|---|
| 1 | Application Triggered - Disclosures Need to Be Sent | `Application_Date__c` | `LOA2_Task_Issue_Disclosures` v9 |
| 2 | Disclosures Pending Signature | `LE_Sent_Date__c` | `LOA2_Task_Disclosures_FollowUp` v10 |
| 6 | Disclosures Signed - Review and Submit to Processing | `Disclosures_Signed_Date__c` | `LOA2_Task_Send_to_Processing` v7 |
| 7 | File Submitted to Processing | `Submitted_to_Processing_Date__c` | `LOA2_Task_IPR_Wait` v5 |
| 8 | File Submitted to Underwriting | `Submitted_to_UW_Date__c` | `LOA2_Task_Submitted_To_UW` v5 |
| 9 | Initial UW Decision Received | `Initial_UW_Decision_Date__c` | `LOA2_Task_Initial_Decision` v5 |
| 10 | File Resubmitted to Underwriting | `Resubmitted_Date__c` | `LOA2_Task_Resubmitted_To_UW` v5 |
| 11 | Congratulations - Clear to Close! | `Clear_to_Close_Date__c` | `LOA2_Task_Close_On_CTC` v3 (no LOA2 gate, no work item) |
| 12a | Change Detected / COC Review (LE) | `COC_LE_Trigger__c` IsChanged | `LOA2_Notify_COC_LE` v1 **(new)** |
| 12b | Change Detected / COC Review (CD) | `COC_CD_Trigger__c` IsChanged | `LOA2_Notify_COC_CD` v1 **(new)** |

`COC_LE_Trigger__c` / `COC_CD_Trigger__c` are **Number(18,0) counters written by Encompass** (not checkboxes), so `IsChanged` is the trigger — each increment is a new COC event. At build time LE had **2** records populated and **CD had ZERO**, so 12b is deployed but never observed firing on real data.

### ⚠️ #2 silently skips on simultaneous batch loads
`LOA2_Task_Disclosures_FollowUp` requires `Disclosures_Signed_Date__c` blank. When Encompass lands `LE_Sent_Date__c` and `Disclosures_Signed_Date__c` in the SAME save (common — see the disclosures-orphan note), #2 never sends. Confirmed in the prod test: both dates in one save → no email; LE Sent alone → email sent correctly. Arguably correct (they're already signed) but it is NOT a bug report when someone says "the signature chaser never arrives."

### Verified in PROD 2026-08-24 on `Melquiades Test - 84651464644` (006Qg00000j39BJIAY)
All 10 fired, all routed to the test recipient, **0 work items created** (loan has no LOA2 → `dec_HasLOA2` held). Body renders dates as "August 24, 2026" and "Not assigned" for blank LOA2. The 2-address recipient list was separately proven in staging (`tbrito@…invalid,eyaber@citylendinginc.com`) since Test Mode masks it in prod.

**MISTAKE MADE DURING THE TEST:** setting `Loan_Type__c = "FHA"` on the test loan (just to populate the email's Loan Type line) tripped the pre-existing `LOA2_FHA_Docs_Email_to_Nila` flow, which is NOT under Test Mode — a real FHA docs request went to Homesisupport@supremelending.com + kiana.smith@supremelending.com for a fake loan. **Check what else keys off a field before setting it on a test record in prod.**

### Audit of the remaining `requireChange` flows — 3 hardened 2026-08-25 (prod)
After the Resubmitted defect, every Opportunity-triggered flow was scanned for the same pattern (`doesRequireRecordChangedToMeetCriteria` combined with either the `LOA2__c` gate or a filter that is true in a field's default/blank state). Four flagged; **three fixed**, one deliberately left:

| Flow | Problem | Fix (prod) |
|---|---|---|
| `LOA2_Task_Order_Appraisal` v11 | `Appraisal_Ordered_Date__c IsNull true` (blank = default) + LOA2 gate | LOA2 gate → in-flow `dec_HasLOA2`; requireChange → `Disclosures_Signed_Date__c IsChanged` |
| `LOA2_Task_COC_Rate_Locked` v7 | LOA2 gate + `Lock_Date__c IsNull false` | LOA2 gate → in-flow `dec_HasLOA2`; requireChange → `Lock_Date__c IsChanged` |
| `LOA2_Task_ICD_Request` v5 | `ICD_Date__c IsNull true` (blank = default) + LOA2 gate | LOA2 gate → in-flow `dec_HasLOA2`; **requireChange KEPT** — the trigger is the *conjunction* of Title Commitment + Hazard Insurance + Lock Date, so there is no single driving field to put `IsChanged` on. Removing the LOA2 gate still eliminates the dominant misfire vector (LOA2 assignment). |

**NOT changed: `Notify_New_LOA_Assignment`.** The scan flagged it, but it triggers on **`OpportunityTeamMember`**, not Opportunity, and its `LOA_Assignment_Date__c IsNull true` + `TeamMemberRole = LOA` + requireChange combination is the intended semantic (fire when a team member becomes an LOA). Left alone.

Behaviour is unchanged in all three — moving the LOA2 test from entry criteria to an in-flow decision means the flow now *runs* on more records but still only *creates* work items when LOA2 is set. Prod smoke test: an open Borrower Opportunity saved cleanly with all three active (this is the gotcha-30 failure shape, so a clean save is the load-bearing check).

### Open items
- **#4 and #5 not converted** — still processor-only. `LOA2_Task_Appraisal_POD`'s new version IS in staging (v5) but NOT prod; prod runs the old one. **Reverse drift — remember when resuming.**
- **Staging does not have the 10** (prod-only) and has **no valid OWEA**, so any converted flow there faults and emails a "Flow Error Details" notice. Set staging to *System email only* before creating the OWEA — staging email scrubbing is INCONSISTENT (some addresses are `.invalid`, others are live real addresses like `eyaber@citylendinginc.com`).
- `Loan_Processor_Email__c` integration mapping (20% coverage).

## ⚠️ `doesRequireRecordChangedToMeetCriteria` is NOT "this field changed" — false "Resubmitted to processing" milestones (FIXED 2026-08-24, prod v5 / staging v4)

**Symptom:** the "Resubmitted to processing - awaiting LP conditions" LOA2 milestone was appearing on loans that had **never been submitted anywhere**, seconds after LOA assignment. Example: Tule River / Bayardo Suarez `006Qg00000p1TdkIAE` — item created 2026-08-17 15:20:52, one second after the First Touch LOA1 item, with `Submitted_to_Processing_Date__c`, `Submitted_to_UW_Date__c` and `Resubmitted_Date__c` ALL null and `Current_Milestone__c = "Started"`.

**Root cause.** `LOA2_Task_Resubmitted_To_Processing` entry criteria was an AND of `LOA2__c IsNull false` + `RecordTypeId = Borrower` + `StageName != Closed Won/Lost` + **`Resubmitted_Date__c IsNull true`**, with `doesRequireRecordChangedToMeetCriteria = true`, intending to mean "Resubmitted Date was CLEARED". **It does not mean that.** `doesRequireRecordChangedToMeetCriteria` means *the record did not satisfy the ENTIRE criteria set before this save and does now* — so with a filter that is true by default (`Resubmitted_Date__c` blank is every loan's starting state), the flow fires whenever **any OTHER filter newly turns true**. The dominant path: **`LOA2__c` going blank → populated**, which `LOA_Assignment_First_Touch` does on every single loan. **The `LOA2__c IsNull false` gate added 2026-08-06 is what converted this from a rare misfire into an every-loan misfire.**

**Why only this flow.** All 6 UW-stage create flows share the `requireChange` + state-filter shape, but the other 5 key on a date being **populated** (`IsNull false`), so a false fire needs the date already set when LOA2 is assigned — much rarer, and the Name-prefix dup guards absorb it. This one keyed on **blank**, the universal default. **Lesson: never combine `doesRequireRecordChangedToMeetCriteria` with a filter that is satisfied by a field's default/empty state — use an explicit `IsChanged` instead.**

**Fix (v5 prod / v4 staging):** removed `doesRequireRecordChangedToMeetCriteria` and added **`Resubmitted_Date__c IsChanged true`** alongside the existing `Resubmitted_Date__c IsNull true`. Two filters on the same field is legal and together mean "the field changed AND is now blank" = genuinely cleared. (Per gotcha #23, `IsChanged` and `requireChange` are mutually exclusive, so the flag had to go.)

**Verified in staging** on Jose Vasquez `006Em00000ObbKXIAZ`: (a) assigning LOA2 created the 5 legitimate milestones whose dates were already populated (Issue Disclosures, COC Rate Locked, Appraisal POD, IPR review, File submitted to UW) and **no** "Resubmitted to processing"; (b) setting then clearing `Resubmitted_Date__c` DID create it (due +2bd, owned by the LOA2) **and** closed "File resubmitted to UW". Both paths correct.

**Data cleanup:** 55 "Resubmitted to processing" items existed; **43 were false** (parent loan has no `Submitted_to_UW_Date__c` — a file that never reached UW cannot be resubmitted to processing), **36 of them still open** in LOAs' queues. User chose **delete** (not Status = N/A). Script: `scripts/delete_false_resubmitted_to_processing.apex` (idempotent). The other 12 have a real UW date and were left alone.

**Side observation worth knowing:** assigning LOA2 to a loan whose milestone dates are already backdated fires a *burst* of legitimate milestones at once (5 on the staging test loan). Not a defect, but it explains "why did this loan suddenly get 5 work items".

## Denied loans could be dragged back to an open Stage via Current Status — FIXED 2026-08-19 (prod + staging)

**Symptom:** a denied Borrower loan (`Loan_Status__c = "Application denied"`, Credit App Status `Denied - UW`) sat in Stage **Needs Analysis** for 5 days (Maria Hernandez Rojas 703002064514, reopened manually from Closed Lost by a user 2026-08-14). Editing the **Stage** directly re-closed it instantly; editing **Current Status** did NOT.

**Root cause = after-save recursion guard.** `Auto_Update_Stage_Based_on_CurrentStatus` (**RecordAfterSave**, Update, Borrower RT, entry `Current_Status__c IsChanged`; authored by Camilo 2025-12) maps Current Status → Stage (e.g. `Pre-Qualified (On Hold)` → **Needs Analysis**). Because it updates the SAME record in **after-save**, that recursive save does **NOT** re-run **before-save** record-triggered flows — so `Update_current_Milestone_Loan_status_Opp` (before-save, holds the `Loan_status → Closed_Lost_y` rule that closes denied loans) never re-evaluated. Changing Stage in the UI is a normal save, so the before-save flow DID run and re-closed correctly. **Lesson: a correction that lives in a before-save flow cannot fix a value written by an after-save flow on the same record in the same transaction — put the guard in the writer, or duplicate the check after-save.**

**Verified the before-save flow itself is fine:** a no-op touch-save on the record immediately set `StageName='Closed Lost'`, cleared `Current_Status__c`, set `Reason_for_loss__c='Loan was adverse'`, `CloseDate=Date_Denied__c`. Path: entry formula → `Encompass_Reactivation` (default) → `Manual_Hold_Guard` (default; its hold rules require **Application Date blank**, so a loan with an App Date is never held) → `Entity_Loan_Created` (default) → `Update_fields` (Closed_Loan false → default) → `Loan_status` → `Closed_Lost_y` → `Set_to_Closed_Lost`.

**Fix (v9 prod / v8 staging active): `Terminal_Loan_Guard`** added as the FIRST element of `Auto_Update_Stage_Based_on_CurrentStatus`. Rule `Is_Terminal_Loan` (`1 OR 2 OR 3 OR 4 OR 5`) matches `Loan_Status__c` IN (*Application denied, Application withdrawn, Application approved but not accepted, File Closed for incompleteness*) **OR** `Loan_Folder__c = "Adverse Loans"`, and has **no connector** → the flow ends without touching Stage. Default → `What_is_the_current_status` (unchanged behavior). Protects ALL branches (Pre-Qualified, Sent to Trio/TBD, Pre-Approved, Ratified) — note the Pre-Approved and Ratified branches already checked for Closed Won/Lost, but the Pre-Qualified branch did not, which is where it leaked. Backfill sweep after the fix: **0** open Borrower opps with a terminal Loan Status, so Maria's was the only case.

- **Staging drift found:** staging was missing `Opportunity.Ratified_Date__c` (referenced by this flow), which blocked the deploy — created it in staging (Date, FLS Admin + Agent Loa On-Demand) and added the field file to the repo (it had never been tracked).
- **Still open (user decision):** nothing blocks a user manually moving a Closed Lost opp to an open stage. The 5/15-era guards only stop *automation* reverting closed opps and manual Closed **Won**. A VR blocking `Closed Lost → open stage` when Loan Status is terminal was offered but NOT built.

## Lessons learned / gotchas (apply to future deploys)

1. **Always grant FLS on new custom fields.** Custom fields default to invisible per profile. Either include `<fieldPermissions>` on a Profile in the deploy, deploy a Permission Set with the field permissions, or have the user grant FLS via Setup → Object Manager → Field → Set Field-Level Security after deploy.

2. **CSF (Custom Summary Formula) syntax in metadata is finicky.** The format `Field:AGGREGATION` works for deploy validation but doesn't always render in the report UI. The reliable alternative: add `<aggregateTypes>Average</aggregateTypes>` to a `<columns>` entry on a numeric field. Salesforce uses values `Sum`, `Average`, `Maximum`, `Minimum`, `Unique` — NOT `Avg`. **Deploying a working CSF `<aggregates>` block (verified 2026-07-06 on `Pullthrough_Ratio_8NL`): child element order is strictly alphabetical (`calculatedFormula`, `datatype`, `description?`, `developerName`, `downGroupingContext?`, `isActive`, `isCrossBlock`, `masterLabel`, `scale`); the display-name tag is `<masterLabel>` — `<label>` deploy-fails with "label invalid at this location in type ReportAggregate" (the validator flags the element AFTER the real problem, so a bad/missing tag surfaces as an error on the next line); `<datatype>` enum values are LOWERCASE `currency` / `number` / `percent` (capitalized `Number`/`Percent` fail). A `percent` CSF multiplies the raw ratio by 100 for display, so `WON:SUM / RowCount` (=0.556) renders as `55.56%` — do NOT pre-multiply by 100. `WON:SUM` = count of Closed Won; over a report filtered to Closed Won+Lost, `WON:SUM / RowCount` = pull-through / win rate.** Example: `Pull-through Ratio` report (`00OQg00000HYdTNMA1`, B2C Borrower folder) — grouped by Application Month, Borrower + Closed Won/Lost, last 3 months.

3. **Dashboard chart `chartSummary` for custom-aggregate fields:** include `<aggregate>Average</aggregate>` alongside `<column>Opportunity.Field__c</column>`. If the metadata-set chart errors out with "fields no longer available", UI re-bind (Edit chart → wrench → re-select measures) is the reliable fix.

4. **Reports default to `Created Date | Current FQ` time-frame filter** unless explicitly overridden. Add `<timeFrameFilter><dateColumn>CREATED_DATE</dateColumn><interval>INTERVAL_CUSTOM</interval></timeFrameFilter>` to disable it.

5. **RecordType filter format in report XML:** column = `RECORDTYPE`, value = `Opportunity.Borrower` (object-prefixed developer name).

6. **Salesforce dashboard charts can have at most 2 grouping columns.** Cannot natively show 3-dimensional data (Branch × Month × Status) as a single chart — use a matrix report for that.

7. **Component types learned:**
   - `Bar` / `Column` — single grouping
   - `BarGrouped` / `ColumnGrouped` — clustered, two groupings
   - `BarStacked` / `ColumnStacked` — stacked, two groupings
   - `BarStacked100` / `ColumnStacked100` — 100% stacked (% view)
   - `Table` — flattens matrix reports awkwardly; not great for Branch × Month
   - `LightningTable` — NOT a valid value, despite documentation suggesting it
   - Charts with two groupings need both `g1` and `g2` sort orders defined in `groupingSortProperties`

8. **Title length limit on dashboard components: 40 characters.** Description max 255 characters.

9. **Field type `Avg` aggregation enum value:** Use `Average`, not `Avg`. Salesforce metadata API rejects `Avg`.

10. **Default org alias is `homesi-staging`.** Always pass `prod` explicitly when working with production org.

11. **Apex test users for fields with lookup filters need the right profile/role/etc., not just the right Title.** The custom error message on a lookup filter is what the admin typed in (e.g., "Only users with the title 'LOA' can be selected") — it's not necessarily what the underlying filter actually checks. Always confirm the filter rule by querying `CustomField.Metadata.lookupFilter` via Tooling API:
    ```sql
    SELECT Metadata FROM CustomField
    WHERE TableEnumOrId = 'Opportunity' AND DeveloperName = 'LOA1'
    ```
    Then read `Metadata.lookupFilter.filterItems` to see what fields/operators the filter actually uses. (Example: `LOA1__c`'s filter is on `User.Profile.Name = 'Agent Loa On-Demand'`, not on Title.)

12. **`LanguageLocaleKey = 'en'` is rejected by this org.** Use `'en_US'` for test User inserts. The error is `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST: bad value for restricted picklist field: en`.

13. **Mixed DML in `@TestSetup`.** Inserting `User` and a non-setup object (Account, Opportunity, etc.) in the same `@TestSetup` transaction throws Mixed DML. Cleanest pattern: insert Users in `@TestSetup`, insert other records in each `@IsTest` method (separate transaction).

14. **Inserting `OpportunityShare` with `UserOrGroupId == OwnerId` fails.** Salesforce throws `FIELD_INTEGRITY_EXCEPTION` ("Owner of the record cannot be a sharing recipient"). Always skip the owner explicitly when building share lists.

15. **Managed package triggers (e.g., `tdc_tsw.OpportunityTrigger` from TaskRay) coexist fine with custom triggers on the same object.** No conflict; both fire. To verify whether a trigger is from a managed package, check `ApexTrigger.NamespacePrefix` and `ManageableState`.

16. **Inbound email capture in this org is gated on Contact/Lead/User address match.** When an outbound EmailMessage is sent from the Salesforce Email composer to an external party, the reply only becomes an `EmailMessage` record on the originating Opportunity if the sender's email address already exists as a Contact, Lead, or User at the time the reply arrives. No match → reply silently dropped (not captured anywhere queryable). Threading via `ReplyToEmailMessageId` determines which Opp the reply attaches to once capture has fired, but the address match is what fires the capture in the first place. The `EmailMessageStubContactCreator` trigger automates stub Contact creation for outbound emails so this gating condition is always met going forward.

17. **Polymorphic relationships can't be filtered by type in SOQL.** `WHERE RelatedTo.Type = 'Opportunity'` is not valid syntax on `EmailMessage`. Workaround: filter by key prefix in Apex (`String.valueOf(em.RelatedToId).substring(0, 3) == '006'`) after the query, or use SOQL `TYPEOF` with care.

18. **Opportunity Lookup(Contact) fields each create their own child related list, but page-layout exposure is separate.** This org has three: `Buyers_Agent__c` (relationship `Opportunities3`, label "Opportunities (Buyers Agent)"), `Listing_Agent__c` (`Opportunities4`, "Opportunities (Listing Agent)"), and `Referred_By__c` (`Opportunities`, "Opportunities"). Only `Referred_By__c`'s related list is on the Contact page layout right now (shown under section header "Opportunities referred by this contact"). Setting `Buyers_Agent__c` or `Listing_Agent__c` via Apex is real and queryable, but **invisible** on the Contact record until those related lists are added to the layout. Beware the confusing case: an agent that's *also* in the referral program shows under "Opportunities referred by this contact" via `Referred_By__c`, which can fool you into thinking the buyers/listing-agent link is what you're seeing.

19. **LOS placeholder sentinels in this org.** When users in Encompass don't have real agent data, they enter recurring placeholder patterns: emails matching `^na@` (`na@gmail.com`, `na@na`, `NA@NA`), phones `999-999-9999` / `000-000-0000` / `111-111-1111` (all-same-digit), and company name `"FSBO"`. `OpportunityUpdater.isJunkPlaceholderEmail` / `isJunkPlaceholderPhone` catch these. Without filtering, the Email-OR-Phone match logic on Contact lookups would pin one stub Contact to many Opportunities over time. If you build any new Apex that ingests LOS data via Contact-style matching, reuse these helpers.

20. **TypeScript integration name-splitting quirk for agents.** The integration splits `<agent>_firstName` (which is a full-name string from the LOS) on spaces — `firstName = [0]`, `lastName = slice(1).join(' ')`. Single-token names like "Madonna" yield `lastName=""`, breaking `Contact` insert because `LastName` is required. The `companyName` fallback chain (`<agent>_companyName ?? <agent>_firstName ?? ""`) can also yield empty strings OR person names as `Account.Name`. Apex defensively handles both — but the cleanest fix lives in the TypeScript (read separate first/last fields if the LOS exposes them, drop the firstName→companyName fallback).

21. **`deploy_metadata` MCP tool has no checkOnly flag.** Two safe paths to "validate before prod" with the current MCP tooling: (a) deploy to `homesi-staging` first with `RunSpecifiedTests` (genuine pre-prod test, staging is generally in sync enough for Apex deploys), OR (b) deploy straight to prod with `apexTests` set — `rollbackOnError: true` means a failing test rolls back the entire deploy atomically, so prod can never be left broken. Both are safe; staging-first is the most cautious.

22. **Set `CanvasMode = AUTO_LAYOUT_CANVAS` on all new flows.** Without it, the deployed flow lands in FREE_FORM_CANVAS mode and Flow Builder stacks every element at coordinate (0, 0), making the flow unreadable without manually dragging each node. The metadata snippet to include in every new flow file:

    ```xml
    <processMetadataValues>
        <name>CanvasMode</name>
        <value><stringValue>AUTO_LAYOUT_CANVAS</stringValue></value>
    </processMetadataValues>
    ```

    Already applied retroactively to `SLA_Follow_Ups` and all 9 LOA2 milestone task flows. Make this part of the flow-authoring template.

23. **`doesRequireRecordChangedToMeetCriteria = true` is mutually exclusive with `IsChanged` operators in flow filters.** Salesforce throws a validation error if both are present. Choose one approach per flow: either set the flag to `true` and use plain equals/not-equals filters (clean for "fire only on transition" semantics on update flows), OR omit the flag and use explicit `IsChanged` operators in filter items. The LOA2 task-creating flows use option 1; the `Close_On_*` flows use option 2 because they need to fire on the specific transition of the milestone date populating, not on every save where the date is non-null.

24. **2-phase deploy for flow activation.** Salesforce will NOT activate a flow version in the same deploy that creates that version — the `FlowDefinition` reference resolves against the registered versions BEFORE the new `Flow` is committed. Required workflow: (1) deploy `<name>Flow</name>` with the new version as Draft, (2) query `SELECT DeveloperName, MAX(VersionNumber) FROM Flow GROUP BY DeveloperName` to confirm the new version number, (3) write `FlowDefinition` files with `<activeVersionNumber>` set to that new max, (4) deploy a second manifest with `<name>FlowDefinition</name>`. Skipping step 2 (assuming the version number) is the most common failure mode — version numbering depends on prior deploy history which the local repo doesn't track.

25. **Inactive-User fallback pattern for any flow that assigns ownership from a User lookup.** When `Some_User_Lookup__c` points to an inactive User, Salesforce throws `INVALID_CROSS_REFERENCE_KEY: owner cannot be blank` on Task/Owner assignment. Defensive pattern: add a Record Lookup `User WHERE Id = $Record.Some_User_Lookup__c AND IsActive = true`, then a formula `IF(ISBLANK(Lookup.Id), $Record.OwnerId, $Record.Some_User_Lookup__c)`. Reference the formula instead of the raw field in the OwnerId assignment. The LOA2 task flows all use this pattern.

26. **Workflow Email Alerts with `<recipients><type>email</type>...` fail to deploy in this org.** Use `<ccEmails>literal.address@domain.com</ccEmails>` instead. This sends to the literal address as a cc on the email alert. Simpler to source-control (no User Id lookup needed) and works reliably across orgs.

27. **Text email templates are deployable via metadata; HTML templates are not (cleanly).** HTML email templates require a Letterhead, which is its own metadata type, can have shared-resource dependencies, and is fiddly to source-control. For internal-use templates that don't need branding (like the LOA2 FHA Docs alert to Nila), use `templateType = text` and skip the Letterhead entirely. The text template lives at `email/unfiled$public/<Name>.email` + `.email-meta.xml`.

28. **Report / list-view inline editing reads the classic page layout — NOT the Lightning record page (Dynamic Forms).** A field placed on an Opportunity Lightning record page via Dynamic Forms (a Field Section in Lightning App Builder) displays and inline-edits fine *on the record*, but is invisible to report inline editing and list-view inline editing — those still resolve field editability against the classic **page layout** for the record's record type. Symptom: the field shows an editable pencil on the record but a padlock in a report, even for a System Administrator with edit FLS. This is NOT a field-level-security problem. Real example: `Healthiness__c` (Opportunity, restricted picklist) was padlocked in a report purely because it had been added to the Lightning page via Dynamic Forms but never to the classic *Borrower Layout*. Fix: add the field to the classic page layout (Setup → Object Manager → Opportunity → Page Layouts) for **every record type whose records appear in the report** — Opportunity has 5 layouts (Borrower, Broker, Loan, Opportunity, Realtor). Adding it to the page layout does not affect the Dynamic Forms Lightning page. Also note: the old "can't inline-edit a picklist when the report spans multiple record types" limitation was removed in Winter '22 — record-type spread is NOT the cause of a report padlock (`LeadSource` has record-type-specific values and is still inline-editable).

29. **Adding a picklist value requires assigning it to the RECORD TYPE too — not just the field value set.** A new value (especially on a *restricted* picklist) added only to the field's `<valueSet>` will NOT appear in the New/Edit UI, report inline edit, or list-view edit for a given record type until it is ALSO assigned to that record type's picklist values (`RecordType` metadata `<picklistValues>` block for that field). Symptom: the value exists on records (Flows/Apex can set it regardless of RT assignment) but users can't pick it. Note: a metadata *retrieve* of a RecordType often does NOT return custom-picklist RT assignments, so an absent block is not proof the value is assigned — deploy a `<picklistValues>` block listing ALL values (including the new one) to force it. Deploying that block SETS the RT's available values, so include every value, not just the new one. Hit twice this project: `Healthiness__c` = "On Track" and `Root_Cause_Category__c` = "Other" (both restricted; both needed the Borrower RT assignment on top of the value-set add).

30. **In a record-triggered flow's ENTRY criteria, filter record type with the DIRECT field `RecordTypeId` + the RT Id — NEVER the cross-object `RecordType.DeveloperName`.** Entry-criteria filters only support direct fields of the triggering object. A cross-object reference like `RecordType.DeveloperName EqualTo 'Borrower'` is silently stored as a **null field reference**, **deploys AND activates without any error**, then throws only at runtime: `java.lang.RuntimeException: interaction.dal.query.filters.EqualsFilterImpl does not have info on field: null__NotFound on Opportunity`. This caused a **~2-day PROD outage (2026-07-28 → 2026-07-29)**: the 8 LOA2 UW-stage flows each had this nulled RT filter, so **every save of an OPEN Opportunity failed** with `UNKNOWN_EXCEPTION` (recurring core ErrorId `530106887`) for ALL users including System Administrator, in both UI and API. **CLOSED opps saved fine** because the flows' `StageName != 'Closed Won' AND != 'Closed Lost'` guards short-circuited the AND before the null filter was reached — this **open-fails / closed-works split is the diagnostic fingerprint** (also: insert-OK/update-fail on an Update-only flow, and a bare no-Account opp still fails, ruling out sharing/Contact/record-type). Customer **debug logs showed `Status = Success` with no `FATAL_ERROR`** (the failure is in the flow entry-criteria DAL, post-logged-execution), so it looked like a commit/sharing-layer Gack; only Salesforce Support decoding the ErrorId from backend logs revealed the flow field reference. **Do NOT chase sharing/OWD for a 530106887-style "open opp save Gacks" — check recently-changed record-triggered flow entry criteria for a bad field reference first.** Fix: `RecordTypeId EqualTo 012Kb000000RpDEIA0` (Borrower Opp RT Id — the proven pattern used by ~88 other flow filters here; RT Ids are org-specific so this is not portable to staging). **Emergency mitigation: deactivate the offending flow(s) in seconds by deploying a `FlowDefinition` with `<activeVersionNumber>0</activeVersionNumber>` (non-Apex, no test run, instantly reversible), then fix → redeploy new version → 2-phase reactivate.** The Contact OWD/sharing changes earlier that same day were COINCIDENTAL, not the cause.

31. **The Encompass sync (`supreme-encompass-salesforce` Lambda → `OpportunityUpdater`) copies fields from the PARENT loan onto every F30EEP loan, on every upload (2026-09-29).** For `Loan_Program__c = 'F30EEP'` rows the Lambda looks up the Opportunity whose `LoanId__c` = the row's `GVMT_Human_Guid__c` (the C40EEP "human" loan) and sends its `OwnerId`, `Referred_By__c`, `Referred_Date__c`, `State__c`, `LOA1__c`, `LOA1_Assignment_Date__c`, `Sales_Agent__c`, `Sales_Agent_Assignment_Date__c` and `LOA_support_OD__c`. Symptom: a user changes the owner of a "Tule River: …" loan and `sf integrations` changes it back 40–70 min later. Field history shows the revert as `sf integrations`, which looks like a trigger but is the payload. `OpportunityAccountExecutiveOwner` was a false lead (it needs `Affinity_Program__c = true`). Seen on `006Qg00000mWiGqIAK` and `006Qg00000osf7sIAA` (parent owner Giovanni Osorio). Why Giovanni: he owns both parents (760002056191 came from a Lead he owned; he assigned himself 716002059723 on 2026-07-31). **Fixed for `OwnerId` only:** first (2026-09-29) by ignoring the payload owner on update, then (2026-09-30) replaced by the parent-owner follow above — the F30EEP loan follows *changes* of the parent owner, and a manual reassignment survives while the parent owner stays the same. **The other copied fields still overwrite on every upload**, so a manual change to them on an F30EEP loan will also be reverted. To find what the sync writes, read `src/infrastructure/web/handler.ts` + `mapping.ts` in the `salesForceCityLendingInc/supreme-encompass-salesforce` repo; field history alone cannot tell a payload write from a trigger write.

## Merged assignment flow `LOA_Assignment_First_Touch` (2026-06-22; ACTIVATED; LOA1 → work item 2026-07-10, v4 active)

**Consolidates `LOA1_and_LOA2_Automatic_Assignment` + `LOA_First_Follow_Up` into ONE flow**, AND moves the **LOA2 AND LOA1** first-touch items from standard Tasks to **LOA Work Items** (`Mortgage_Condition__c`, record type **Task**). This flow is now the **ACTIVE** assignment flow (v4); the two original flows are deactivated.

- **Why merge:** the two old flows are near-identical (same task-creation half) split only by entry point — text fields (LOS-written, with User-by-name resolution + lookup write) vs lookup fields (UI-picked, with `*_Assignment_Date__c` stamp). They collide (text flow sets the lookup → re-fires the lookup flow), which is why the cross-flow dup guards exist. One flow on the already-flow-heavy Opportunity object is better than 2→3.
- **Merged behavior:** triggers on ANY of the 6 fields (text OR lookup) changing. Per role: resolve the User (lookup-active first, else by-name from text → write the lookup), stamp `*_Assignment_Date__c`, dup-guard, then create the item.
- **Output split (IMPORTANT; updated 2026-07-10):** **LOA2 AND LOA1** each create a `Mortgage_Condition__c` work item (RT **Task**, resolved by `Get_Task_RT` lookup on DeveloperName='Task'). Dup guards: `Name StartsWith "First Touch - LOA2"` / `"First Touch - LOA1"` on `Opportunity__c = $Record.Id`. **UPDATE 2026-08-05 (v6 active prod): the `Is_Complete__c=false` filter was REMOVED from the LOA1 guard (`Get_Existing_LOA1_Item`)** — it now matches First Touch-LOA1 regardless of open/completed, so First Touch is created **once per loan ever** (same fix as the Processor Jr guard, 2026-06-09). Root cause of the dupes: after a First Touch was Completed, the nightly `sf integrations` batch re-wrote the LOA text field, re-fired the flow, found no *open* first touch, and created a second (seen on Juan Carino 716002054911: two "First Touch - LOA1", 7/24 + 8/3). **NOTE: LOA2 first touch is NOT being created anymore in prod — last one 2026-07-13 (48 total); LOA1 is the only active first touch (238, ongoing).** Only the LOA1 branch fires now, so only its guard needed the fix. **Staging synced 2026-08-06 (v2 active).** LOA1 work item is stamped `Agent_Role__c='LOA1'`, `Assigned_Date__c`, `Due_Date__c` (business-day CASE), `Status__c='Not Started'`, `OwnerId=LOA1_OwnerId`. **`Update_LOA1_Lookup` (writes `LOA1__c` + `LOA1_Assignment_Date__c`) is KEPT** — the LOA1 resolve + assignment-date stamp still happen, only the *output* changed Task→work item. `Set_LOA_Work_Item_Agent_Role` (before-save) will re-derive Agent_Role from the loan's Current Status (LOA1 for non-Ratified — consistent). **Only Processor Jr still creates a standard Task** (`Document Follow Up`, unchanged — Touch_Type set, once-per-opp guard).
- **Bug fixed during testing:** the per-role "Resolved?" gate originally compared `<Role>_ResolvedUserId` formula `NotEqualTo ""` — Flow treats empty/null inconsistently, so the branch created an item even when NO user was found. Fixed to gate **directly** on `Get_<Role>_ByLookup.Id IsNull false OR Get_<Role>_ByText.Id IsNull false`. Side effect: a lookup pointing at an INACTIVE user (no text to re-resolve) now SKIPS that branch (the by-lookup query filters `IsActive=true`), rather than creating an item owned by the Opp owner.
- **Sandbox prereqs deployed to `homesi-staging` to host this:** `Mortgage_Condition__c` Task RT + `Priority__c` + `Status__c` (On-Hold) + `Category__c` (Legal/Misc) — staging was missing the prod-only metadata; all four had to deploy in ONE transaction (rollbackOnError).

### Cutover steps (when ready — user's manual go)
1. Activate `LOA_Assignment_First_Touch` AND deactivate BOTH `LOA1_and_LOA2_Automatic_Assignment` and `LOA_First_Follow_Up` **together** (activating without deactivating = duplicate items).
2. The ~189 existing open LOA2 first-touch standard Tasks are treated as **legacy** (left to close out as Tasks — NOT migrated, per user). Only NEW LOA2 first-touch items are work items.

### `SLA_Follow_Ups` LOA1 opp-cycle REMOVED (v9 active, 2026-07-10)

When LOA1 first-touch moved to a work item (above), the **LOA1 follow-up auto-creation was removed from `SLA_Follow_Ups`** per user ("we should have the first touch only, remove the LOA1 follow up"). Deleted from the flow: the `Which_LOA_Role` decision, `Get_Opportunity_LOA1` lookup, `Is_Opportunity_Active` decision, `Copy_2_of_Add_2_Business_DaYS` (NextBusinessDay apex actionCall), `FUP_Task_Opps` recordCreate, and formulas `FollowUpActivityDateOpp` + `SubjectOpp`. The `Lead_or_Opportunity` decision's `Is_Opportunity` rule now **ends after SLA scoring** (no connector) — completing an opp Task still writes `SLA__c` / `SLA_Missed_By__c` (via `Update_Records_1`) but spawns NO follow-up. **The Lead cycle (`FUP_Task_Lead` via `Get_Lead`/`Is_Lead_Active`/`Add_2_Business_DaYS`) and all SLA scoring are PRESERVED.** LOA2 opp-cycle was already gone (v8, 2026-06-04). Net: `SLA_Follow_Ups` now only *scores* opp/LOA Tasks and cycles Leads — it creates zero LOA follow-up tasks.

### Flow-side impact of first-touch → work item (known effects)
- **SLA coverage gap = 4 active Task-based flows**, all filter `Touch_Type__c = "First Touch"` **role-agnostically**, so they silently STOP covering LOA2 **and now LOA1** first-touch (both are work items with no `Touch_Type`): `SLA_Follow_Ups`, `SLA_Aging_9AM`, `SLA_Aging_5PM`, `SLA_Task_Aging`. They don't error — Processor / Sales Agent first-touch stay covered. "SLA on LOA first-touch" is gone until an SLA-on-work-items (SLA v2) is built. The LOA work items DO carry `Assigned_Date__c` so SLA v2 is buildable.
- **`First_Touch_with_Chatter` is unaffected** — it only acts on `Subject StartsWith "Document Follow Up"` (Processor, still a Task).
- No other active flow references the "First Touch - LOA2" subject.

## Document Follow Up task automation (Opportunity)

Two record-triggered flows on Opportunity create "First Touch" / "Document Follow Up" tasks for LOA1, LOA2, and Processor Jr roles. They watch different fields and can both fire on the same opp at different points in its lifecycle.

| Flow | Trigger fields | Trigger type | Source field origin |
|---|---|---|---|
| `LOA1_and_LOA2_Automatic_Assignment` | `LOA__c`, `LOA_2__c`, `Processor_Jr_Text__c` (all text) IsChanged | CreateAndUpdate (after-save) | LOS / sf integrations writes these text values |
| `LOA_First_Follow_Up` | `LOA1__c`, `LOA2__c`, `Processor_Jr__c` (all User lookups) IsChanged | Update (after-save) | User picks via UI lookup field |

The first flow looks up the matching User by Name from the text field and writes the User Id to the corresponding lookup field. Both flows then create the task. Subjects:
- LOA1 task: `First Touch - LOA1 - <opp name>`
- LOA2 task: `First Touch - LOA2 - <opp name>`
- Processor Jr task: `Document Follow Up - <opp name>` (note the different prefix)

### Duplicate-prevention guard (added 2026-05-04)

Both flows now have a guard before each `Create_First_Touch_Task_*` action: a `Get_Existing_*_Task` lookup queries for an open task on the same opp + same owner + matching subject prefix. If one is found, the create is skipped. In `LOA_First_Follow_Up` the flow still continues to update the `*_Assignment_Date__c` field; in `LOA1_and_LOA2_Automatic_Assignment` it exits that branch.

**Why this was needed:** the manual UI path (user picks Luis in `Processor_Jr__c` lookup) fires `LOA_First_Follow_Up` and creates a task. Later, the LOS batch update populates `Processor_Jr_Text__c` for the first time, which fires `LOA1_and_LOA2_Automatic_Assignment` and creates a second (duplicate) task. The guard prevents this collision.

**Processor Jr guard hardened 2026-06-09 (LOA1_and_LOA2_Automatic_Assignment v9, LOA_First_Follow_Up v5):** the `Get_Existing_Processor_Jr_Task` lookup previously filtered `Status = 'Open'`, so once a "Document Follow Up" task was *completed*, a later re-save (e.g. the nightly `sf integrations` batch re-writing `Processor_Jr_Text__c`) would find no open task and spawn a fresh one. Symptom: Tule River opp `006Qg00000jEq4rIAC` got a 2nd Document Follow Up on 6/8 after the 1st was completed 6/4. Fix: **removed the `Status = 'Open'` filter from the Processor Jr guard in both flows** — it now matches Document Follow Up tasks on the opp regardless of open/closed (still keyed by `WhatId` + `OwnerId` = Processor Jr + Subject StartsWith "Document Follow Up"), so the task is created **once per opp per processor, ever**. NOTE: the LOA1/LOA2 guards still filter `Status = 'Open'` (those tasks are allowed to cycle) — only the Processor Jr branch was changed. Activated via 2-phase FlowDefinition deploy (these flows use inline `<status>Active</status>` but the new versions still landed as Draft and needed FlowDefinition activeVersionNumber bumped to 9 / 5).

### `First_Touch_with_Chatter` flow

Triggered on FeedItem create where ParentId is an Opp/Lead/Task. When parent is a Task with subject starting with "Document Follow Up", the flow advances the task's due date to next business day + 2 and flips Touch_Type from "First Touch" to "Follow Up".

**Bug fixed 2026-04-29:** the `Get_Related_Task` lookup was missing `Id = $Record.ParentId` filter, so it would update the user's OLDEST open Document Follow Up task instead of the one where the Chatter was actually posted. Now filters by Id correctly.

## Auto-complete LOA Work Items on status change (2026-07-10)

Two active flows close open LOA Work Items (`Mortgage_Condition__c`, `Is_Complete__c=false`) automatically:
- **`Close_LOA_Work_Items_On_Opp_Close`** (after-save Opp, Update) — Borrower opp reaches `StageName` Closed Won / Closed Lost, OR `Current_Status__c` = `Archive Loan` → sets **ALL** open work items to `Status__c='N/A'`.
- **`Complete_LOA1_Work_Items_On_Ratified`** (after-save Opp, Update, `doesRequireRecordChangedToMeetCriteria=true`, v1 active) — Borrower opp's `Current_Status__c` **transitions to `Ratified`** → sets open items with **`Agent_Role__c='LOA1'` only** to `Status__c='Completed'` (the LOA1→LOA2 handoff; LOA2 items stay open). Get-all + loop (`ItemsToUpdate` collection). requireChange so it fires only on the transition, not every save while Ratified (and new items added post-Ratified are LOA2 anyway per `Set_LOA_Work_Item_Agent_Role`).

## Agent_Role by Current Status on new LOA Work Items (2026-07-10)

Flow **`Set_LOA_Work_Item_Agent_Role`** (before-save, **Create only**, `Mortgage_Condition__c`, v1 active). On any NEW work item tied to an Opportunity (`Opportunity__c` not null), stamps `Agent_Role__c` from the parent loan's `Current_Status__c`: **`Ratified` → `LOA2`, everything else (incl. blank) → `LOA1`**. **Excludes the `LOA2_Milestone_Task` record type** (decision on `$Record.RecordType.DeveloperName != 'LOA2_Milestone_Task'`) — the 10 automated LOA2 milestone flows set `Agent_Role='LOA2'` themselves and must stay LOA2 regardless of status; without the exclusion this flow would flip a milestone created on a non-Ratified loan to LOA1. Catches ALL manual condition/task creators in one place (`ConditionGridController`, `ConditionListParser`, `Generate_Checklist_from_Template`, the Add Work Items Task path, manual UI) instead of editing each. Reads `$Record.Opportunity__r.Current_Status__c` cross-object (works in before-save). Verified live: Ratified opp → LOA2, Pre-Approved opp → LOA1.

**UPDATE 2026-08-10 (v2 prod / v1 staging active): a top-priority `FirstTouch_LOA1` decision rule was added** — if `RecordType != LOA2_Milestone_Task` AND `Name StartsWith "First Touch - LOA1"` → force `Agent_Role='LOA1'`, evaluated BEFORE the Ratified→LOA2 rule. Reason: a First Touch-LOA1 created on an already-Ratified loan (late LOA1 assignment, or already-Ratified import/convert) was getting mis-stamped LOA2 by the status logic. The once-per-loan guard (2026-08-05) fixed the *duplicate*-driven cases but not the "first one created post-Ratified" edge case (~2 in 4 days). Now First Touch-LOA1 is always LOA1 regardless of status. **Historical backfill:** `scripts/backfill_firsttouch_loa1_role.apex` corrects the ~41 pre-existing First Touch-LOA1 rows stamped LOA2 → LOA1 (idempotent; update doesn't re-fire this create-only flow). Run via `sf apex run`.

## LOA Work Item consolidation (2026-06-10) — READ THIS BEFORE TOUCHING LOA2 FLOWS OR MORTGAGE CONDITIONS

**The 10 LOA2 milestone flows no longer create/close Tasks.** They now create/close **`Mortgage_Condition__c` records** (object label **"Work Item"** / plural **"Work Items"** — renamed from "LOA Work Item" 2026-08-06 in prod + staging so end users aren't confused; API name unchanged). The widget band, utility item, and tab all now read "Work Item(s)".

> **⚠️ GOTCHA (2026-08-07): a PARTIAL CustomObject header deploy silently DISABLED reports and broke every report on the object.** The label rename was deployed via a minimal `object-meta.xml` (side folder `objlabel/`) containing only label/pluralLabel/sharing/nameField/visibility. Omitting `<enableReports>` reset it to the default (OFF) — reports on `Mortgage_Condition__c` all broke with **"The report definition is obsolete. Your administrator has disabled all reports for the custom object, or its relationships have changed."** The *label change itself is harmless*; the **deploy method** was the culprit. **Lesson: a CustomObject header deploy is NOT purely additive for the boolean `enable*` flags — omitted ones revert to default.** When deploying just an object header (label rename, sharing change, etc.), ALWAYS include the full set: `enableReports`, `enableActivities`, `enableBulkApi`, `enableFeeds`, `enableHistory`, `enableSearch`, `enableSharing`, `enableStreamingApi` (+ `allowInChatterGroups`, `compactLayoutAssignment`, `deploymentStatus`, `visibility`, `externalSharingModel`, `sharingModel`, `nameField`). Do NOT deploy the full repo `objects/Mortgage_Condition__c/Mortgage_Condition__c.object-meta.xml` to prod — it carries local-only fields (`Follow_Up_Request__c`, `Chase_*`) not in prod and rolls back. Fixed by redeploying the minimal header WITH all `enable*` flags set to their real values (`objlabel/`). Reason: Activity (Task/Event) reports never support inline editing, and joined reports don't either — so milestone items and mortgage conditions were consolidated into one object to get a single inline-editable report for the LOAs.

### Object changes (`Mortgage_Condition__c`)

- **Record types (prod IDs):** `Mortgage_Condition` ("Mortgage Condition", `012Qg000003tTm2IAE`, org/profile DEFAULT), `LOA2_Milestone_Task` ("LOA2 Milestone Task", `012Qg000003tTm1IAE`), and **`Task` ("Task", `012Qg000003uX4PIAU`, added 2026-06-16)**. Staging has its own IDs — flows resolve the RT via a `Get_*_RT` Record Lookup on DeveloperName, never hardcoded.
- **`Task` record type (2026-06-16):** ad-hoc personal tasks added via the Add Work Items "Task" path now get their OWN record type instead of `Mortgage_Condition`, so they break out as a separate group in the consolidated report (which groups by Record Type) and get their own collapsible **"Tasks"** band in the `mortgageChecklist` widget. The `Add_Work_Items` flow's `Get_Condition_RT` lookup filter was changed `DeveloperName = 'Mortgage_Condition'` → `'Task'` (flow v7). RT visibility + "Mortgage Condition Layout" assignment granted on Admin + Agent Loa On-Demand profiles. Picklist assignments mirror the Mortgage_Condition RT (all Category/Status/Agent_Role values; Category default = Other). **The conditions path (ConditionGridController) is unchanged — it still creates `Mortgage_Condition`-RT records via profile default.** `mortgageChecklist` LWC: `_isTask()` (RT `Task`), `_taskRecords()`, and `_conditionRecords()` now excludes both milestones AND tasks; new `taskItems`/`hasTasks`/`tasksOpen`/`__tasks__` section. **Historical "tasks" created before this (as `Mortgage_Condition` RT, Category Other) are NOT auto-migrated — they're indistinguishable from real conditions; reassign RT manually if needed.**
- **New fields:** `Agent_Role__c` (picklist LOA1/LOA2/Processor), `Assigned_Date__c` (DateTime), `Completed_Date__c` (DateTime — stamped by `Sync_Mortgage_Condition_Completion` the first time Status reaches Completed/Waived/N/A, regardless of source).
- **Note history pattern (2026-06-11):** `Latest_Note__c` Text(255) is THE writable note field everywhere (reports, list views, layouts, both LWCs). `Notes__c` (LTA) is the append-only history: `Sync_Mortgage_Condition_Completion` v4 prepends `[YYYY-MM-DD HH:MM:SS GMT - First Last] message` (newest on top, via textTemplate for the newline) whenever Latest_Note changes and is non-blank; skips appending past 30k chars. Notes is Readonly on layouts and stripped in `updateCondition` (`testUpdateCondition_directNotesWriteIgnored` guards this). Timestamps are GMT — flow formulas can't do user timezones.
- **Name-edit guards (2026-06-11):** report inline editing writes Name directly, bypassing the LWC controller guards. VR `Milestone_Name_Locked` blocks ISCHANGED(Name) on the milestone RT everywhere (flows never rename after create, so no conflict). `Sync_Mortgage_Condition_Completion` v3 copies manual Name edits on CONDITION records to `Condition_Name_LTA__c` — only when Name changed and LTA did NOT change in the same save (widget edits set both together, so they're skipped). Report inline editing does NOT support Long Text Area fields (`Notes__c`, `Condition_Name_LTA__c` are read-only in reports — platform limit, not FLS/layout).
- **Status per record type:** Condition RT = all 5 values; Milestone RT = Not Started / In Progress / Completed only.
- **Layouts:** existing "Mortgage Condition Layout" expanded (Due Date, Category, Notes, Opportunity, Document URL etc. — required for report inline editing per gotcha 28); new "LOA2 Milestone Task Layout" for the milestone RT.
- **Profiles updated:** Admin (FLS on 3 new fields, RT visibilities, layout assignments) and **Agent Loa On-Demand** (previously had ZERO access to the object — now Create/Read/Edit, full FLS, both RTs visible, default = Condition). Records created by `ConditionListParser` / `Generate_Checklist_from_Template` get the Condition RT via profile default — no code change was needed.

### Flow rework pattern (all 10 LOA2_Task_* flows, prod versions: Issue_Disclosures v7, Disclosures_FollowUp v7, Order_Appraisal v8, COC_Rate_Locked v4, Send_to_Processing v4, ICD_Request v3, Close_On_Appraisal_Ordered v5, Close_On_COC_Cleared v2, Close_On_ICD_Received v2, Close_On_Submitted_To_Processing v2)

- Create: `Name = LEFT("<milestone> - " & Opp.Name, 80)`, `Opportunity__c`, `OwnerId` (same inactive-LOA2 fallback), `Due_Date__c`, `Status__c='Not Started'`, `Agent_Role__c='LOA2'`, `Assigned_Date__c`, `RecordTypeId` from `Get_Milestone_RT` lookup. No more Touch_Type/Priority (Task-only fields).
- Dup-guard / auto-close lookups: `Opportunity__c = $Record.Id AND Name StartsWith '<milestone>' AND Is_Complete__c = false` (replaces WhatId/Subject/IsClosed).
- Auto-close sets `Status__c = 'Completed'`; `Completed_Date__c` comes from the sync flow.
- Flow labels renamed "LOA2 Task:" → "LOA2 Work Item:". `LOA2_FHA_Docs_Email_to_Nila` untouched.
- **`SLA_Follow_Ups` no longer scores these items** (it's Task-triggered). SLA v2 on work items = future work; `Assigned_Date__c`/`Completed_Date__c` are already captured to make it possible.

### Report

**`LOA Work Items - Open (with Contacts)` (added 2026-06-16, `00OQg00000HKsTtMAL`, folder LOA Reports):** a replica of the Consolidated report PLUS borrower + agent point-of-contact columns. **Why formula fields instead of an Opportunity-primary report type:** the user built a custom report type `Opportunities_with_Conditions` (Opportunity primary, child `Mortgage_Conditions__r`) to expose Opportunity fields, BUT **metadata report deploys reject ALL custom report types with "invalid report type"** (confirmed against two different custom RTs — it's a tooling/platform limit, not specific to one RT; private/personal reports also can't be retrieved to copy the format). The auto report type `CustomEntity$Mortgage_Condition__c` does NOT expose the `Opportunity__c` lookup's fields via metadata tokens either (`Mortgage_Condition__c.Opportunity__r.Email__c` → "no CustomField found"). **Solution: 6 cross-object formula text fields on `Mortgage_Condition__c`** that pull the contact data down from the parent Opportunity, so the existing (deployable) report type exposes them as own-object columns: `Borrower_Email__c` (`Opportunity__r.Email__c`), `Borrower_Phone__c`, `Listing_Agent_Name__c` / `Buyers_Agent_Name__c` (`TRIM(Opportunity__r.<Agent>__r.FirstName & " " & LastName)` — **same compound-`Name` gotcha as `LOA2__r.Name`: Contact's `Name` can't be referenced cross-object, use First/Last**), `Listing_Agent_Phone__c` / `Buyers_Agent_Phone__c` (`Opportunity__r.<Agent>__r.Phone`). FLS granted on Admin + Agent Loa On-Demand. **Formula-field deploy gotcha: `<formulaTreatBlanksAs>` enum is `BlankAsBlank` (singular), not `BlankAsBlanks`.** The `Opportunities_with_Conditions` report type was also enhanced (added Agent_Role__c / Latest_Note__c / RecordType to its Mortgage Conditions child section) in case the user finishes a report on it via the UI, where custom report types work fine.

`LOA Work Items - Open (Consolidated)` in folder **LOA Reports** (`LOAReports`), report type `CustomEntity$Mortgage_Condition__c`, filter `Is_Complete__c = false`, grouped Opportunity → Record Type. Inline-editable (Status, Due Date, etc.) because the primary object is the custom object and fields are on the classic layouts. Column tokens for custom-entity reports: `CUST_NAME`, `CUST_OWNER_NAME` (NOT `CUST_OWNER`), `CUST_RECORDTYPE`, `CUST_CREATED_DATE`, custom fields as `Mortgage_Condition__c.Field__c`. **2026-06-12: added `Mortgage_Condition__c.Condition_Name_LTA__c` column** (full long text next to the 80-char Name; read-only in the report — LTA platform limit).

### Data scripts (run with `sf apex run -f scripts/<name>.apex -o prod`)

- `backfill_work_item_record_types.apex` — stamps the Condition RT on the ~84 pre-existing records (created before RTs existed; they sit on Master until backfilled). Idempotent.
- `migrate_open_loa2_tasks_to_work_items.apex` — converts the open LOA2 milestone Tasks (8 at build time) into milestone work items and **deletes** the Tasks (completing them would fire SLA_Follow_Ups and write false SLA-Missed scores). Idempotent. **RUN 2026-06-10 — verified clean.**
- `backfill_work_item_names.apex` — fixes condition records whose `Name` is the record ID. Root cause: `ConditionListParser` and `Generate_Checklist_from_Template` only wrote `Condition_Name_LTA__c` and never set `Name`, so Salesforce auto-filled the ID. Both creators fixed 2026-06-10 (parser sets `Name = text.left(80)`, deployed with ConditionListParser_Test; flow v2 adds an `Item_Name = LEFT(...,80)` formula assignment, activated via FlowDefinition). Script backfills `Name` from `Condition_Name_LTA__c` (fallback `Condition_Name__c`), only touching records whose Name equals their own 15-char Id prefix. Idempotent.

### Checklist widget (`mortgageChecklist` LWC) repurposed 2026-06-10

The Opportunity-page widget is now titled **"LOA Work Items"** with two sections: a pinned **"LOA2 Milestones — managed by automation"** band (shows `Name`, 3-value status combobox, due badge; NO delete, NO name edit) above the unchanged categorized conditions checklist. Conditions-only progress bar.
**Collapsible sections (2026-06-15):** three-level collapse via `handleSectionToggle` + `expandedSections` Set. Keys: `__milestones__` (the milestones band), `__conditions__` (an **umbrella "Mortgage Conditions" header** added 2026-06-15 that wraps ALL category groups — collapsing it hides every category at once, mirroring the milestones band; carries a `completedCount/totalCount` badge), and one key per category name (each category still individually collapsible inside the umbrella). **All sections collapsed by default** (empty Set) so the widget stays compact and doesn't push down the components below it on the Opp page; the conditions progress bar stays visible even when the umbrella is collapsed. `.section-header` has a hover style in the CSS.
`MortgageChecklistController` changes: `getConditions` now also selects `Name` + `RecordType.DeveloperName` (LWC splits on it); `updateCondition` silently strips `Condition_Name_LTA__c`/`Category__c`/`Document_URL__c` for milestone records (flows find them by Name — renames would break auto-close) and, for conditions, syncs `Name = LTA.normalizeSpace().left(80)` when the LTA name is edited; `deleteCondition` throws for milestone records. Tests: `MortgageChecklistController_Test` (17 methods incl. 2 milestone-guard tests).

### Utility bar "LOA Work Items" (added 2026-06-10)

The standard **To Do List utility item shows Tasks ONLY** (`runtime_sales_todo_list:unifiedToDoListAuraWrapper`) — custom objects can never appear in it. Replicated for work items with a **List View utility item** (`flexipage:filterListCard`) on the HOMESÍ-B2B app's utility bar (`flexipages/LightningSales_UtilityBar`, the app 12/14 active LOAs use), pointing at list view `Mortgage_Condition__c.My_Open_Milestone_Tasks` (filterScope Mine, RT = LOA2_Milestone_Task, Is_Complete = false — single-RT filter keeps list-view inline editing of Status working). The HOMESÍ-B2C app (`HOMES_B2C_UtilityBar`) was NOT updated — only 1 LOA uses it; add the same item there if asked.

**Custom utility LWC `myWorkItems` (2026-06-11, replaced the filterListCard item):** the standard List View utility card has NO expand/inline-edit (fixed rendering), so the utility item now uses custom LWC `c:myWorkItems` (flexipage componentName `c:myWorkItems`) — expandable rows like the To Do List: chevron opens full name, Opportunity link, type label, Status, Due Date, Add Note + history; completing removes the row. Header has a "View all" link to the `My_Open_Milestone_Tasks` list view. **Scope widened 2026-06-11: shows ALL of the user's open work items (conditions + milestones), not just milestones** — `getMyOpenMilestoneItems()` (name kept for compat) is now Mine + open, due-date sorted; milestone rows get the 3-value Status picklist, condition rows the full 5 values (Waived/N/A complete them). NOTE: the tab list views (`My_Open_Milestone_Tasks`, `Due_*`, `Overdue`) are still milestone-RT-only — single-RT filter preserves list-view inline editing of Status.

**Guided New / no orphans (2026-06-12, REPLACED the brief personal-item form):** all creation goes through screen flow **`Add_Work_Items`** (v2 active): radio choice **Task** (single item: name → Name+LTA, due date, optional first note) or **Mortgage Conditions**. **Opportunity is MANDATORY for both** (flowruntime:lookup on `Mortgage_Condition__c.Opportunity__c`, required) — `createPersonalItem` was REMOVED; no orphan work items. Entry points: (1) the object's **New button is overridden** (actionOverride type lightningcomponent, Aura `newWorkItemOverride` embedding lightning:flow; Large form factor only, skipRecordTypeSelect), (2) the panel "+" opens LWC `addWorkItemsModal` (LightningModal hosting lightning-flow). Tasks are Condition-RT records (Category Other) owned by the runner. Panel expanded rows show the FULL `Condition_Name_LTA__c` text (falls back to Name). **v2 (2026-06-12):** the conditions path no longer subflows into `Add_Conditions_from_List` — Back/Previous can't cross subflow boundaries, so the paste-list screen + `ConditionListParser` actionCall are INLINED in `Add_Work_Items` (Previous now returns to the chooser); Screen_Task got `allowFinish=true` (with false, the screen renders NO forward button at all — Finish IS the create button on a terminal screen). Flow gotchas: screen field type `TextBox` is invalid at v65 (use `InputField` + dataType); a screen can't have BOTH allowBack and allowFinish false; `allowFinish=false` on a last screen suppresses the only forward/create button.

**v3 (2026-06-15) — conditions path is now a 2-step editable grid.** The single paste screen was split: **Screen 1** (`Screen_Conditions`) = paste box + **Next** (the batch Category dropdown was REMOVED — category is now per-row); **Screen 2** (`Screen_Conditions_Grid`) hosts custom LWC **`c:conditionsGrid`**, a spreadsheet-style editable table — one row per parsed line with an editable Condition text input, a **Category** combobox, a **Due Date** picker, and a per-row delete (✕). The LWC owns its own **Back** / **Create Conditions** buttons (`showFooter=false` on the screen; it fires `FlowNavigationBackEvent` / `FlowNavigationNextEvent`), parses the pasted text client-side (mirrors the `ConditionListParser` bullet/number-stripping regex), and on Create calls Apex **`ConditionGridController.createConditions(opportunityId, rows[])`** which inserts one `Mortgage_Condition__c` per non-blank row (Name=text.left(80), Condition_Name_LTA__c=full text, Status='Not Started', Category default 'Other', Due_Date per row, Sort_Order 10/20/30…). `createdCount` is output back to the flow for the success screen. The old inline `Parse_Conditions` actionCall (`ConditionListParser`) + `Screen_Cond_Error` fault screen were REMOVED from `Add_Work_Items` — **`ConditionListParser` itself is untouched and still used by the `Add_Conditions_from_List` flow.** New files: `classes/ConditionGridController.cls` (+`_Test`, 6 methods, 100% coverage) and `lwc/conditionsGrid`. **Gotchas this build:** (1) a `ComponentInstance` screen field with `<isRequired>false</isRequired>` lands the flow **InvalidDraft** (deploy reports success — verify Status via Tooling) — omit `isRequired` on custom-LWC screen fields; (2) to keep cell inputs from losing focus on every keystroke, the LWC mutates the row object **in place** (no array reassignment) on name/category/due edits and only reassigns the array on row delete (which renumbers the `#` column).

**v4 (2026-06-15) — Next-button fix + grid UX/category polish.** (a) Both `Screen_Conditions` (paste) and `Screen_Conditions_Grid` need `allowFinish=true` or this org's runtime hides the forward button entirely even on non-terminal screens — same gotcha that forced `allowFinish=true` on `Screen_Task`. (b) `conditionsGrid` Due Date now **defaults to 2 business days out** (weekend-skipping JS, no holidays). (c) Removed the inner `slds-scrollable_y`/`max-height` wrapper and set `.grid-wrap{position:relative;z-index:2}` over `.action-bar{z-index:1}` so the Category dropdown + Due-Date calendar render IN FRONT of the Back/Create buttons instead of being clipped/hidden (lightning-combobox/date popovers render inline, so any `overflow` ancestor clips them). (d) **Category options now load live** from the `Category__c` picklist via `getObjectInfo`+`getPicklistValues` (wired on `defaultRecordTypeId`) — no hardcoded list, can't duplicate. Added picklist values **Legal** and **Misc** to `Mortgage_Condition__c.Category__c` (sorted, unrestricted; full set now Assets/Credit/Income/Insurance/Legal/Misc/Other/Property/Title). (e) **Auto-category from condition code**: the grid reads a leading `{X-NNNN}` code and maps the letter → Category: **A=Assets, C=Credit, I=Income, L=Legal, M=Misc, P=Property**; any other letter / no code → `Other`. Title & Insurance are custom (manual, not coded). Uses the CODE itself, not the text after it (e.g. `{L-0048} Credit - LDP/GSA…` → **Legal**). The code is left in the text — the existing condition-name code-stripping flow removes it on save. **LWC-template gotcha: a literal `{...}` in the .html is parsed as a binding expression and fails deploy (LWC1083) — escape braces as `&#123;`/`&#125;`.**

**v6 (2026-06-15) — Due Date is now MANDATORY on both paths.** Task screen: `Item_Due` is `isRequired=true` with a `defaultValue` = formula `Default_Task_Due` (2-business-day CASE on `$Flow.CurrentDate`, same Thu+4/Fri+4/Sat+3/else+2 shape as `LOA2_Task_ICD_Request`); label changed "Due Date (optional)" → "Due Date". Conditions grid: the date `lightning-input` is marked `required` and `handleCreate` blocks with an error if any row's `dueDate` is blank (rows still pre-fill 2 business days out). Enforcement is UI/flow-level only — `ConditionGridController` and other creators (paste-from-list, template generator, LOA2 milestone flows) are unchanged; a DB-level validation rule was offered but not added (would need to confirm every automated creator always sets a date first).

**v5 (2026-06-15) — CRITICAL: the paste box was MOVED INTO the `conditionsGrid` LWC because Flow strips `{…}` codes.** Root cause of "categories never auto-fill": **Salesforce Flow treats `{C-0025}` as merge-field syntax.** When the pasted text was captured in a Flow `LargeTextArea` (`conditionsList`) and passed to the LWC via `<elementReference>`, Flow's merge engine resolved each `{X-NNNN}` to empty string before the component ever saw it (confirmed via a temp debug line: input arrived as `" Credit - AUS…"` — leading space where the code was). No grid-side regex can recover them. **Fix:** the LWC now owns BOTH steps internally — a `mode` state (`'paste'` | `'grid'`) shows a `lightning-textarea` first (component-owned `inputText`, never a Flow variable), then the editable grid. The flow's `Screen_Conditions` paste screen was DELETED; `Decision_Type` default now goes straight to `Screen_Conditions_Grid` (LWC only, `showFooter=false`). The LWC drives nav: paste-step **Back** = `FlowNavigationBackEvent` (to chooser), paste-step **Next** = internal parse → grid mode, grid **Back** = internal → paste mode, grid **Create** = Apex insert → `FlowNavigationNextEvent` (to success). **Lesson: never route text that can contain `{...}` through a Flow string variable/merge — capture it inside an LWC.** Gotcha during this change: couldn't drop the now-unused `pastedText` @api property because obsolete flow versions (3,4) still bind it — kept it declared-but-unused in both `.js` (`@api pastedText`) and the `targetConfig` to satisfy the "targetConfig is missing a property referenced in flow versions" deploy error.

**Tab + due-date views (added 2026-06-10, reworked 2026-06-12):** CustomTab `Mortgage_Condition__c` (visible DefaultOn for Admin + Agent Loa On-Demand) with list views `My_Open_Milestone_Tasks` (relabeled **"My Open Work Items"** — API name unchanged, the utility panel "View all" link depends on it), `Due_Today`, `Due_Tomorrow`, `Due_This_Week`, `Overdue` (all Mine + Is_Complete=false, differing only on the Due_Date__c filter). **2026-06-12: the milestone-RT filter was REMOVED from ALL five views** (user wants conditions + milestones together everywhere). **Consequence (confirmed 2026-06-16): a Lightning list view containing MORE THAN ONE record type cannot be inline-edited AT ALL** — the pencil does nothing; this is a hard Salesforce limitation ([help doc](https://help.salesforce.com/s/articleView?id=xcloud.basics_customviews_lv_lex_considerations.htm)), NOT a per-picklist-value issue (so making the Status/Priority value sets uniform across RTs did NOT enable it — that change was kept anyway, harmless). **Reports do NOT have this limitation** (multi-RT inline edit works in reports since Winter '22), so the inline-edit path for the combined set is the `LOA Work Items - Open (Consolidated)` report, not the list views. User chose to keep the combined list views (view-only) rather than split them by record type.

**Status / Priority changes (2026-06-16):** `Status__c` gained **On-Hold** (not a "done" status; `Is_Complete__c` unaffected) and all 3 RTs now share the uniform set Not Started / In Progress / On-Hold / Completed / Waived / N/A — the milestone RT gained Waived/N/A purely to keep value sets uniform for inline edit (automation still only uses the first three; the milestone band LWC still shows 3 + On-Hold). New field **`Priority__c`** (High/Normal/Low, Normal default, unrestricted) assigned to all 3 RTs, FLS on Admin + Agent Loa On-Demand, added to both classic layouts and as a column on all 5 list views. On-Hold added to the status comboboxes in both `mortgageChecklist` and `myWorkItems` LWCs. **ListView relative-date gotcha:** values use SOQL-style underscored tokens — `TODAY` and `TOMORROW` work as-is but week tokens must be `THIS_WEEK` / `LAST_WEEK` (literal `THIS WEEK` fails with "Invalid date").

**Tab in app navigation (2026-06-12):** `Mortgage_Condition__c` added to `<tabs>` of CustomApplication **`standard__LightningSales`** (HOMESÍ-B2B) — without it, opening list views / records from the App Launcher spawned temporary workspace tabs on every navigation (the "every list view opens a new tab" symptom). Now it's a real nav item with normal in-place list-view switching. **Gotcha: the app file is retrieved as `standard__LightningSales` (plain "LightningSales" fails) and references prod-only flexipage `Scheduled_SMS_Record_Page1`, so the app CANNOT deploy to homesi-staging** — deploy it to prod only, and remember rollbackOnError: keep it OUT of staging batches or the whole batch reverts. **Added to HOMESÍ-B2C too (2026-07-08):** `Mortgage_Condition__c` added to `<tabs>` of CustomApplication **`HOMESB2C`** (retrieve/deploy name `HOMESB2C`; also references prod-only `Scheduled_SMS_Record_Page1` → prod-only, keep out of staging batches). The B2C utility bar `HOMES_B2C_UtilityBar` now ALSO has the `myWorkItems` utility item (added 2026-07-08 — same `<componentName>myWorkItems</componentName>` item with identifier `loa_work_items_queue`, label "LOA Work Items", icon list, height 600 / width 500 / scrollable, placed after the To Do List item). Both apps' utility bars now carry it.

**List-view buttons + Mass Complete (2026-06-12):** object `searchLayouts` now excludes standard buttons `Import` + `PrintableListView` and adds custom list-view button **`Mass_Complete`** ("Complete Selected", WebLink displayType=massActionButton, requireRowSelection, linkType=page → VF `MassCompleteWorkItems` with `standardController recordSetVar` + extension `MassCompleteWorkItemsExt`). Select rows → Complete Selected → confirmation page → sets `Status__c='Completed'` on selection (sync flow stamps `Completed_Date__c`/`Is_Complete__c`) → returns to the list. Tests: `MassCompleteWorkItemsExtTest` (2 methods). Remaining buttons: New, Change Owner, Complete Selected.

### Access model (2026-06-11) — OWD Private

`Mortgage_Condition__c` OWD changed Public Read/Write → **Private**. Consequences and design:

- **LOAs see only their own items** in the report, tab, list views, and utility panel (platform-enforced; the "Mine" list-view filters are now redundant but harmless).
- **`MortgageChecklistController` is `without sharing` ON PURPOSE** — the Opportunity checklist widget must show ALL work items on a loan to anyone who can open the Opportunity. Record access for the widget is gated by Opp visibility; everywhere else by ownership/sharing. Don't "fix" it back to with sharing without re-reading this.
- **Team leads**: public group **`LOA_Team_Leads`** (created empty — ADD MEMBERS in Setup → Public Groups) + owner-based sharing rule `LOA_work_items_to_Team_Leads` (records owned by role **LOA** → group, **Read/Write**).
- **Role gaps**: Karen de Fex and Andres Robles were assigned the LOA role 2026-06-11 (via API). **Alejandra Murillo and Luis Molinares still have NO role** — their owned items are not shared to the leads group. Alejandra is herself a lead (group membership covers her viewing, not her ownership).
- **Group members** (added 2026-06-11): Carlos Alvarez, Igleth Mercado, Monica Fernandez, Alejandra Murillo.
- **Known data gap**: ~33 open conditions are owned by It Support (admin-created via paste/template tools) — invisible to LOAs and leads in the report (widget still shows them via without-sharing controller). Fix = reassign ownership to the loan's LOA2 and have LOAs create conditions themselves going forward.
- **Deploy gotcha: OWD change + sharing rule cannot ship in the same deploy** — the OWD flips trigger a sharing recalc and the rule creation fails with "sharing operation already in progress" (and rollbackOnError reverts everything). Two deploys: object first, sharing rule second.

### Lock alert automations (added 2026-06-11, all v1 active in staging + prod)

| Flow | Trigger | Action |
|---|---|---|
| `Lock_Rate_Locked_Email_Alert` | Lock_Date__c + Loan_Processor_Email__c populated, open Borrower opp (transition-only) | Instantly emails the processor (`Loan_Processor_Email__c`) from the `sfintegrations@supremelending.com` OWEA; logged on the opp timeline. Re-fires on re-lock. |
| `Lock_Expiration_Work_Items` | Scheduled paths on `Lock_Exp_Date__c` (NOTE: field is `Lock_Exp_Date__c`, not Lock_Expiration_Date__c) | **-3 days**: creates "Lock is about to expire - <opp>" LOA2 work item due on expiration date. **+1 day** (loan still open): closes the about-to-expire item, creates "Lock has expired, please re-lock - <opp>" due run-date + 1. Entry requires open Borrower + LOA2 set + Closed_Loan=false, so pending schedules auto-cancel when the loan closes. Dup-guarded by Name prefix (this also means a manually created condition starting with the same words suppresses the automated item — intentional). |
| `Lock_Renewal_Close_Items` | `Lock_Exp_Date__c` IsChanged to a future date | Auto-closes open "Lock has expired" / "Lock is about to expire" work items (re-lock happened). |

**OPEN ITEM:** `Opportunity.Loan_Processor_Email__c` (Email, created 2026-06-11) is EMPTY until the Encompass integration maps the processor's email into it (TypeScript `fieldsToUpdate`). The Rate Locked email sends nothing until then. Staging-only Info warning about Automated Process User email address does not affect prod (prod setting already valid; FHA email flow precedent).

### Gotchas learned

- **FlowDefinition activeVersionNumber is per-org.** Staging and prod have different version numbers for the same flow; the local flowDefinition files currently hold PROD numbers. Re-query max version before activating in either org.
- **A failed deploy with `rollbackOnError` rolls back EVERYTHING in that deploy**, including components that reported success in `componentSuccesses`. (Bit us: 6 Opportunity fields "succeeded" then vanished because a report in the same deploy failed.)
- **Staging was missing prod fields** `LE_Sent/Due/Revised_Date__c`, `ICD_Date__c`, `Title_Commitment_Date__c`, `Hazard_Insurance_Date__c` — now deployed to staging (user-approved). Flows deployed while fields were missing land as InvalidDraft and must be redeployed after the fields exist.
- **A brand-new ReportFolder + its report must deploy in the SAME transaction**; folder-then-report in separate deploys hits "Cannot find folder" (and see rollback gotcha above).

## LOA2 milestone task automation (added 2026-06-04 / extended 2026-06-05 / 2026-06-08; **REWORKED 2026-06-10 — flows now create LOA Work Items, not Tasks. Trigger logic below still accurate; task-field details superseded by the section above**)

A data-driven set of eleven record-triggered flows that creates and auto-closes LOA2 tasks based on milestone date fields populating on the Opportunity. Replaces the "task closes → next task auto-creates" cycle (a side-effect of `SLA_Follow_Ups`) for LOA2 specifically. LOA1 cycling and Lead cycling in `SLA_Follow_Ups` remain unchanged.

### The 11 flows

| Flow | Trigger | What it does |
|---|---|---|
| `LOA2_Task_Issue_Disclosures` | Opportunity insert/update; `Application_Date__c` populated AND `LE_Sent_Date__c` blank | Creates "Issue Disclosures - <opp name>" task, ActivityDate = `LE_Due_Date__c` (fallback `Application_Date__c + 3`) |
| `LOA2_Task_Disclosures_FollowUp` | `LE_Sent_Date__c` populated AND `Disclosures_Signed_Date__c` blank | Auto-closes the "Issue Disclosures" task, creates "Disclosures Follow-Up - <opp name>" task, ActivityDate = `LE_Sent_Date__c + 2` |
| `LOA2_Task_Order_Appraisal` | `Disclosures_Signed_Date__c` populated AND `Appraisal_Ordered_Date__c` blank | Auto-closes the "Disclosures Follow-Up" task, creates "Order Appraisal - <opp name>" task, ActivityDate = `Disclosures_Signed_Date__c + 2`. **Subject is English ("Order Appraisal"), NOT Spanish ("Ordenar Appraisal") — renamed 2026-06-05.** |
| `LOA2_Task_Close_On_Appraisal_Ordered` | `Appraisal_Ordered_Date__c` populated | Auto-closes the "Order Appraisal" task |
| `LOA2_Task_Close_On_Disclosures_Signed` | `Disclosures_Signed_Date__c` populated | **Safety-net close flow (added 2026-07-06).** Closes ANY open "Issue Disclosures" AND "Disclosures Follow-Up" milestone work items on the opp, keyed on the actual completion date. Get-all + loop (`Items_To_Close` collection), sets `Status__c='Completed'`. Independent of the chained create-flows so a **simultaneous date load** (LE Sent + Disclosures Signed on the SAME save) can't orphan the earlier milestone items — see orphan note below. |
| `LOA2_Task_COC_Rate_Locked` | `Lock_Date__c` populated | Creates "COC Rate Locked - <opp name>" task, ActivityDate = `Lock_Date__c + 1` |
| `LOA2_Task_Close_On_COC_Cleared` | `LE_Revised_Date__c >= Lock_Date__c` OR `ICD_Date__c >= Lock_Date__c` | Auto-closes the "COC Rate Locked" task |
| `LOA2_Task_Send_to_Processing` | `Disclosures_Signed_Date__c` populated AND `Submitted_to_Processing_Date__c` blank | Creates "Send to Processing - <opp name>" task, ActivityDate = `Disclosures_Signed_Date__c + 2` |
| `LOA2_Task_Close_On_Submitted_To_Processing` | `Submitted_to_Processing_Date__c` populated | Auto-closes the "Send to Processing" task |
| `LOA2_Task_ICD_Request` | `Title_Commitment_Date__c` AND `Hazard_Insurance_Date__c` AND `Lock_Date__c` all populated AND `ICD_Date__c` blank | Creates "ICD Request - <opp name>" task, ActivityDate = **flow run date + 1 business day** (weekend-skipping CASE formula on `$Flow.CurrentDate`, since all conditions are met at run time). Added 2026-06-08. |
| `LOA2_Task_Close_On_ICD_Received` | `ICD_Date__c` populated | Auto-closes the "ICD Request" task. Added 2026-06-08. |
| `LOA2_FHA_Docs_Email_to_Nila` | `Disclosures_Signed_Date__c` populated AND `Loan_Type__c = 'FHA'` | **Reworked 2026-06-08 (v4): sends the email NATIVELY via the `emailSimple` Send Email action — no longer fires the workflow alert.** Recipients = `Homesisupport@supremelending.com` + LOA1 (`LOA1__r.Email`) + LOA2 (`LOA2__r.Email`) + Loan Officer (`Loan_Officers__r.Email__c`), built in the `Recipients` formula (blank-safe, comma-joined). Subject + body are inline in the action (merge fields `{!$Record.*}`), plain text (`sendRichBody=false`, `useLineBreaks=true`). **The Classic template `LOA2_FHA_Docs_Request` and the alert `LOA2_FHA_Docs_Request_to_Nila` are now DORMANT — email wording lives in the flow, edit it there.** |

### Orphaned "Issue Disclosures" / "Disclosures Follow-Up" — root cause + fix (2026-07-06)

The chained create-flows each close the PRIOR milestone item behind their own entry criteria. `LOA2_Task_Disclosures_FollowUp` (the only flow that closed "Issue Disclosures") requires `LE_Sent_Date__c` populated **AND `Disclosures_Signed_Date__c` blank**. When Encompass lands `LE_Sent_Date__c` and `Disclosures_Signed_Date__c` on the **same save** (common — both were 6/29 on Tule River opp `006Qg00000luUd3IAE`, both 6/25 on Doreen Rachal `006Qg00000ldOFYIA2`), that entry fails, the flow is skipped, and "Issue Disclosures" is never closed even though the loan advanced. Blast radius at fix time: **2** open items, both "Issue Disclosures" (closed manually). Durable fix = the dedicated `LOA2_Task_Close_On_Disclosures_Signed` flow above, which closes on the completion date itself and therefore can't be skipped by simultaneous loads. **Lesson: any "close prior item" logic gated behind the NEXT milestone's create-criteria is fragile to multi-field batch loads — pair it with a standalone `Close_On_<completion field>` flow.**

### Defensive patterns applied to all task-creating flows

Every task-creating flow applies these guards uniformly. Future flow additions should follow the same template.

1. **Closed-stage guard** — entry criteria includes `StageName != 'Closed Lost' AND StageName != 'Closed Won'`. Task creation does not fire on closed opportunities. Added after the Tule River incident where a Closed Lost opp received a new task.
2. **Borrower record type filter** — `RecordType.DeveloperName = 'Borrower'`. Only loan opps trigger LOA2 tasks.
3. **Transition-only firing** — `doesRequireRecordChangedToMeetCriteria = true` on all task-creating flows. The close-only flows (`Close_On_*`) use `IsChanged` operators in their filters instead, since the two mechanisms are mutually exclusive.
4. **Owner-assignment chain LOA2 → LOA1 → Opp Owner (updated 2026-08-05).** Every milestone-creating flow now has TWO active-user Record Lookups in the path — `Get_LOA2_User` (`User WHERE Id = $Record.LOA2__c AND IsActive = true`) then `Get_LOA1_User` (`User WHERE Id = $Record.LOA1__c AND IsActive = true`) — wired `...Get_LOA2_User → Get_LOA1_User → Get_Existing...`. The owner formula (`Task_Owner_Id` in the 6 original flows, `fOwnerId` in the 6 UW-stage flows) is `IF(NOT(ISBLANK({!Get_LOA2_User.Id})), {!$Record.LOA2__c}, IF(NOT(ISBLANK({!Get_LOA1_User.Id})), {!$Record.LOA1__c}, {!$Record.OwnerId}))`. So: active LOA2 → LOA2; else active LOA1 → LOA1; else Opportunity Owner — no `owner cannot be blank` error, no orphaned task. Applied across all 12 create flows and re-activated (2-phase) in PROD. (Was previously just LOA2-active → Opp Owner.) **Staging synced 2026-08-06 (v2 active).** Note: the start filter still requires `LOA2__c` populated, so LOA2 is always set; the chain only decides ownership when LOA2 is inactive.
5. **Duplicate-prevention** — `Get_Existing_*_Task` lookup filters by `WhatId = $Record.Id AND Subject LIKE '<prefix>%' AND IsClosed = false`. If found, the create branch is skipped. Same pattern as `LOA_First_Follow_Up`.
6. **Auto-close prior task** — chained flows (e.g., `Disclosures_FollowUp` closes the prior `Issue Disclosures`) update the looked-up task to `Status = 'Completed'` BEFORE creating the new one. Implementation pattern: Assignment node sets Status on the looked-up reference, then `recordUpdates` element uses `<inputReference>` only (no `<inputAssignments>` — the two are mutually exclusive in v65 metadata).
7. **AUTO_LAYOUT_CANVAS** — all 11 flows include `<processMetadataValues><name>CanvasMode</name><value><stringValue>AUTO_LAYOUT_CANVAS</stringValue></value></processMetadataValues>` so Flow Builder auto-arranges elements vertically instead of stacking them at (0,0). **Apply this to all new flows going forward.** Also applied retroactively to `SLA_Follow_Ups`.

### Business-day due-date formula (reusable)

`LOA2_Task_ICD_Request` is the first flow whose ActivityDate is "N business days from the run date" rather than "milestone date + N calendar days". When the task should be due relative to *when the flow fired* (because the milestone is the conjunction of several dates, not one), use this weekend-skipping Date formula on `$Flow.CurrentDate` (`DATE(1900,1,7)` is a Sunday so `MOD(...,7)` gives 0=Sun … 6=Sat). `LOA2_Task_ICD_Request` uses **+1 business day** (v2, 2026-06-08):

```
CASE(MOD({!$Flow.CurrentDate} - DATE(1900,1,7), 7),
5, {!$Flow.CurrentDate} + 3,   /* Fri -> Mon */
6, {!$Flow.CurrentDate} + 2,   /* Sat -> Mon */
{!$Flow.CurrentDate} + 1)      /* Sun-Thu -> +1 cal */
```

For +2 business days the CASE branches are: Thu `+4`, Fri `+4`, Sat `+3`, default `+2`.

It does NOT account for holidays — only weekends.

### Task fields stamped at creation

Every task created by these flows carries (added in waves: base set first, then `Agent_Role__c` 2026-06-05, then `Touch_Type__c` + `Assigned_Date__c` 2026-06-05):

| Field | Value | Why |
|---|---|---|
| `OwnerId` | LOA2 user (or Opp Owner if LOA2 inactive) | See fallback pattern above |
| `WhatId` | `$Record.Id` | Links task to the Opportunity |
| `Subject` | `"<English label> - <Opp Name>"` | English-only after 2026-06-05 rename of Order Appraisal |
| `ActivityDate` | Milestone-specific due date | See trigger table |
| `Status` | `Not Started` | Salesforce default |
| `Priority` | `Normal` | |
| `Agent_Role__c` | `LOA2` | So `SLA_Follow_Ups` LOA2-branch guard fires AND LOA2 dashboards/reports include the task |
| `Touch_Type__c` | `Follow Up` | 48h SLA window. Required for `SLA_Follow_Ups` to score the task at all. |
| `Assigned_Date__c` | `$Flow.CurrentDateTime` | Baseline for SLA business-hour computation |

### SLA scoring integration

When any of these tasks is marked Completed, `SLA_Follow_Ups` fires (entry: `Status` IsChanged to `Completed`, `Touch_Type__c` IsNotNull). It computes business hours from `Assigned_Date__c` to completion and writes `SLA__c` (`"Contacted - SLA Met"` / `"Contacted - SLA Missed"`) and `SLA_Missed_By__c` to the task. The LOA2 auto-cycle branch was removed in `SLA_Follow_Ups` v8 — completing one of these tasks does NOT spawn a generic "Follow Up - LOA2" task. The next task only comes from the next milestone advancing.

### Email send — now native in the flow (2026-06-08)

`LOA2_FHA_Docs_Email_to_Nila` was reworked to send via the `emailSimple` Send Email action instead of firing the workflow alert, because the recipient list needed the **Loan Officer**, whose email lives on the `Loan_Officer__c` custom object (`Loan_Officers__r.Email__c`) — a workflow email alert can only target Users, related-Contact types, or Email-type fields *on the Opportunity*, so it can't reach a related custom object's email. LOA1/LOA2 are User lookups (could have been alert "User" recipients), but the LO forced the native-send approach for all four in one email.

Recipients are assembled in the `Recipients` formula: always `Homesisupport@supremelending.com`, plus each of `{!$Record.LOA1__r.Email}`, `{!$Record.LOA2__r.Email}`, `{!$Record.Loan_Officers__r.Email__c}` wrapped in `IF(NOT(ISBLANK(...)))` so blanks don't create empty entries. Passed to the action's `emailAddresses` input. (`$Record` cross-object traversal in flow formulas works fine here.)

**emailSimple param-name gotchas in this org (cost a couple of InvalidDraft deploys):**
- The recipient input is **`emailAddresses`** (accepts a comma/semicolon-separated string), NOT `emailAddressesCommaOrSemicolonSeparated` (that name deploys as `success:true` but lands the flow in **InvalidDraft** — check `Status` via Tooling, don't trust the deploy's `success` flag). CC equivalent is **`ccRecipientAddressList`**.
- **`composeEmailContent`** is "not available in the referenced action" — omit it (harmless Info, but cleaner gone).
- For plain-text body with line breaks: `sendRichBody=false` + `useLineBreaks=true`. Merge fields `{!$Record.*}` resolve inside the inline `emailSubject`/`emailBody` stringValues.
- Pattern cribbed from existing working flows (`Notify_New_LOA_Assignment`, etc.) — when unsure of an action's param names, grep the repo's other flows for a working example.

**Email logging (v5, 2026-06-09):** the action now sets `logEmailOnSend=true` + `relatedRecordId={!$Record.Id}`, so each send is logged as an EmailMessage on the Opportunity's Activity Timeline (previously the send left no Salesforce record — the only way to confirm a send was Setup → Email Log Files). Now you can verify a send by looking at the opp's timeline.

**Sender = Org-Wide Address (v7, 2026-06-09) — Mimecast deliverability fix.** Originally `senderType=CurrentUser`, so the From address was whoever triggered the flow. When a `@supremelending.com` user (e.g. It Support `m.rodriguez@supremelending.com`) triggered it manually, the send bounced with **Mimecast `550 Anti-Spoofing policy - Inbound not allowed`** — Salesforce is external to Mimecast, so a message From the protected `supremelending.com` domain looks spoofed. The nightly `sf integrations` trigger delivered fine because that user's **User.Email is `sfintegrations@supremelending.com`** (username is `@citylendinginc.com` but the From uses the Email field), and that specific address is permitted through Mimecast. Fix: set `senderType=OrgWideEmailAddress` + `senderAddress=sfintegrations@supremelending.com` (an Org-Wide Email Address, `IsAllowAllProfiles=true`), so every send now goes out From that permitted address regardless of who/what triggers it. **Lesson: in this org, Salesforce-sent mail From `m.rodriguez@supremelending.com` (and likely other individual `@supremelending.com` users) bounces on Mimecast anti-spoofing; send from the `sfintegrations@supremelending.com` OWEA instead.** A broader fix (whitelisting Salesforce/SPF in Mimecast for the whole domain) was offered but not done — the OWEA address already delivers.

### Email template + Workflow Alert (now dormant — see above)

- **Template**: `unfiled$public/LOA2_FHA_Docs_Request` — Text email template (not HTML — text templates are deployable through metadata; HTML templates require Letterhead which is harder to source-control). Body rewritten 2026-06-08 ("Hi there, … Please assist with the FHA docs for this loan…"). The LOA2 line merges `{!Opportunity.LOA2_Name__c}` (formula off the `LOA2__c` lookup) so it shows the name and is never blank — see field table.
- **Alert**: `Opportunity.LOA2_FHA_Docs_Request_to_Nila` — Workflow Alert in `workflows/Opportunity.workflow-meta.xml`. Uses `<ccEmails>Homesisupport@supremelending.com</ccEmails>` (literal address, set 2026-06-08 — was test address `m.rodriguez@supremelending.com`) instead of `<recipients><type>email</type>...` which kept erroring on deploy. NOTE: the alert's API name still contains "to_Nila" from its original design, but it now routes to the Homesi support inbox.

### `SLA_Follow_Ups` changes (v8, 2026-06-04)

The flow that scores Tasks for SLA had a default branch that auto-created the next "Follow Up - LOA2" task when an LOA2 task closed — that's what created the unwanted cycle. Changes in v8:

1. **Removed the LOA2 default connector** — the LOA2 decision branch now ends after writing SLA fields, no auto-create downstream. LOA1 and Lead cycling left intact.
2. **Removed the `Get_Opportunity_LOA2` element** — no longer referenced. The `Is_Opportunity_Active` decision and `SubjectOpp` formula were simplified to drop the dependency.
3. **Switched CanvasMode FREE_FORM_CANVAS → AUTO_LAYOUT_CANVAS** so the post-cleanup layout reads top-to-bottom in Flow Builder.

### Known data hygiene issue (as of 2026-06-05)

25 open Borrower opportunities have a `LOA2__c` pointing to an inactive User (Aimmee Buendia ×13, Rolando De Leon ×7, Zulema Cantillo ×3, Paola Gomez ×1, Daniel Arevalo ×1). The inactive-user fallback in the flows means new tasks land on Opp Owner instead of erroring, but for clean SLA reporting and queue ownership LOA2 should be reassigned. 11 of the 25 are also in `Current_Status = "Archive Loan"` (effectively dead).

### Deploy pattern for these flows (2-phase)

Salesforce won't activate a flow version in the same deploy that creates it — the `FlowDefinition` reference resolves before the new `Flow` version is registered. Standard workflow:

1. **Deploy flows as Draft** — manifest with `<name>Flow</name>` listing the 5 task-creating flows.
2. **Query max version** — `SELECT DeveloperName, MAX(VersionNumber) FROM Flow WHERE DeveloperName IN (...) GROUP BY DeveloperName`.
3. **Write FlowDefinition files** — `<activeVersionNumber>` set to the new max for each flow.
4. **Deploy FlowDefinitions** — separate manifest with `<name>FlowDefinition</name>`.

Manifests used last deploy: `manifest/loa2_agent_role_deploy.xml` (step 1) and `manifest/loa2_agent_role_activate.xml` (step 4).

## Apex scripts in `scripts/`

| Script | Purpose |
|---|---|
| `update_opps_to_prequal_on_hold.apex` | One-off bulk update (historical) |
| `fix_chatter_flow_side_effects.apex` | One-time fix for tasks corrupted by the First_Touch_with_Chatter bug (idempotent) |
| `close_duplicate_tule_river_task.apex` | One-time close of the 4/30 Tule River duplicate task (idempotent) |
| `reclose_may15_reverted_opps.apex` | Re-closes the 564 opps the 2026-05-15 batch reverted out of Closed Lost. Idempotent — re-derives the set, only touches still-open opps. Run AFTER the Fix 1 flow guard is live. |

Run with: `sf apex run -f scripts/<name>.apex -o prod`

## sfdx-project.json

`sourceApiVersion` is **65.0** (bumped from 60.0 on 2026-04-29 to support flow `<offset>` element introduced in v65). When deploying flows authored at apiVersion 66.0, use a manifest with `<version>66.0</version>` since the project default is one version behind.

## Probabilistic risk model (future work — not yet built)

User has provided spec for a forward-looking risk field on the open pipeline. See chat history for full logic. Key elements:
- Out of Scope flag (timing-based: days remaining < days to funding from current milestone)
- Delayed flag (stagnation: days in current milestone > 2× expected)
- Brokered channel: flat 30-day rule
- Sources: `Last_Finished_Milestone__c` (need to verify exists), `Loan_Channel__c`, milestone date fields
- This is a SEPARATE feature from the Closing On Time KPI (which is for closed loans, retrospective).

## Read all Contacts for everyone — DONE via profile "View All" (2026-07-28, PROD). Sharing-rule approach was tried and REVERTED (caused an outage).

**Final working solution:** grant Contact **View All (read)** object permission on the human profiles. Only **2 of the 13** lacked it — **`Agent Loa On-Demand`** and **`Sales agent Profile`** (the other 11, incl. Agent/Agent Sales/Supervisors/Branch Managers/LO/LOA/Only_assignment, already had Contact View All). Set `viewAllRecords=true` + `allowRead=true`, left `modifyAllRecords=false` (read-all, not edit-all). Deployed as partial profile files (side folder `ctviewall/profiles/`, objectPermissions-only, so existing Create/Edit/Delete preserved). **View All ignores OWD** (works under Controlled-by-Parent), creates **no per-record shares**, and triggers **no sharing recalc** — so it can't cause the outage below. This is the right tool for "everyone reads all Contacts." (Note: `Agent Loa On-Demand` had Contact View All *removed* earlier per the task #4 lockdown; this re-adds READ-only View All, not Modify All.)

### ⚠️ Do NOT use an all-Contacts sharing rule (it caused a PROD outage 2026-07-28)
Attempted approach (reverted): flip Contact OWD → Private + owner-based sharing rule `Contact_All_Internal_Read` (sharedFrom allInternalUsers → sharedTo allInternalUsers, Read). Deploying "share every Contact with every internal user" kicks off a **massive ContactShare recalculation** (every contact × every internal user). While that recalc ran it **locked the sharing tables and Gacked unrelated saves org-wide** — Opportunity updates failed with `UNKNOWN_EXCEPTION`, and every Feed Item-triggered flow that updates a parent Opp/Lead (`Chatter_to_Contacted_Flow`, `Last_Action_with_Chatter`, `First_Touch_with_Chatter`) threw "unhandled fault" because their parent-record update Gacked. Tell-tale on any concurrent metadata deploy during it: *"The sharing calculation you requested can't be processed right now, because it interferes with another operation already in progress."* **Reverted** by deleting the sharing rule + flipping Contact OWD back to Controlled-by-Parent (done in Setup UI — see gotcha 1), then used the View All profile approach above. **Lesson: to give broad read on a high-volume object, use the "View All" object permission (profile/perm set), never a share-everything-with-everyone sharing rule.**

> **Correction 2026-09-29 (verified by metadata retrieve from prod):** the rule was **not** deleted. `Contact.Contact_All_Internal_Read` still exists, with `accessLevel` **Edit** (the label says Read). Contact OWD is back to Controlled by Parent, so the rule is dormant [Likely]; it would re-trigger the org-wide recalculation above if the Contact OWD were ever changed again. Delete it deliberately (not during business hours) or keep it on purpose. Tracked in `AUTOMATION_INVENTORY.md` §7.2.

### Historical detail of the reverted attempt (kept for the gotchas)
Contact OWD was **Controlled by Parent** (contact access rode on Account access) in both orgs. The attempt was to flip Contact OWD → **Private** and add an owner-based sharing rule.

- **Contact OWD** changed Controlled-by-Parent → **Private** (internal + external) via metadata `objects/Contact/Contact.object-meta.xml` `<sharingModel>Private</sharingModel>` + `<externalSharingModel>Private</externalSharingModel>` (deployed from side folder `ctowd/` — repo has no Contact object header, only `fields/`, so no merge/clobber risk).
- **Sharing rule** `force-app/main/default/sharingRules/Contact.sharingRules-meta.xml` → `Contact_All_Internal_Read`: SharingOwnerRule, `sharedFrom`=allInternalUsers, `sharedTo`=allInternalUsers, `accessLevel=Read`. Grants read to all contacts for all internal users. OWD stays Private; Account/Opp/Lead untouched.
- **Edit impact (accepted):** under Private + a Read-only rule, contact **edit** = owner + role-hierarchy managers + admins only. Anyone who previously edited a contact they don't own via *account* access loses edit. Contact ownership is concentrated (Camilo Delgado Uribe ~14.5k, sf integrations ~10.7k, Giovanni Osorio ~5.2k, It Support ~2.8k, long tail of agents). The `Update_Realtor_Last_Referral_Date` / `..._From_Lead` flows are **record-triggered, RunInMode=null (system context)** → they edit the Contact regardless of the running user's read-only access (confirmed), so they are unaffected.

### Gotchas
1. **Contact OWD CAN be changed via Metadata API** (`sharingModel`) — earlier belief that it's UI-only was wrong. BUT the change kicks off a **Contact sharing recalculation**, and during that window the Metadata API still reports the OLD value, so a **dependent sharing-rule deploy fails with "org wide default is 'Controlled By Parent'"** until recalc finishes. It is NOT a "sharing operation already in progress" error — it's a stale-config read. Staging took ~18 min to settle; prod settled in ~1 min. **Two-step deploy: (1) OWD→Private, (2) retry the sharing rule until it takes.** They cannot ship together.
2. **`EntityDefinition.InternalSharingModel` is unreliable for Contact** — it reported "Private" even while the object was actually Controlled by Parent. Trust the deploy error / Sharing Settings UI, not EntityDefinition.
3. **Live window risk:** between the OWD flip and the sharing rule landing, Contact read is *more* restricted (Private, no rule yet = owner/hierarchy only). Keep the gap short — deploy OWD, immediately retry the rule until it succeeds.
4. Sharing rules are impossible while OWD = Controlled by Parent (must flip to Private first).

## LOA2 UW-stage milestone work items — 8 new flows (2026-07-27, staging + PROD)

Adds the processing → UW → decision → resubmittal chain to the LOA2 milestone automation (same `Mortgage_Condition__c` LOA Work Item pattern: RT `LOA2_Milestone_Task` resolved via `Get_Milestone_RT`, `Agent_Role__c='LOA2'`, `Assigned_Date__c`, `Status__c='Not Started'`, inactive-LOA2→Opp Owner fallback formula, dup-guard by Name prefix, Borrower RT + not-Closed guards, `doesRequireRecordChangedToMeetCriteria=true`). **Due dates = business days** (weekend-skipping CASE on `$Flow.CurrentDate`): 24hr→+1bd, 48hr→+2bd, 3day→+3bd. **Work-item Name is Text(80)** so the full instruction sentence goes in **`Latest_Note__c`**; Name is a concise prefixed label (dup guard keys on the prefix).

8 flows (all record-triggered on Opportunity, Active in staging):
| Flow | Trigger (field populated unless noted) | Creates (Name prefix) / Closes | Due |
|---|---|---|---|
| `LOA2_Task_Appraisal_POD` | `Appraisal_Received_Date__c` | creates "Appraisal received - POD" + **emails `Loan_Processor_Email__c`** from `sfintegrations@supremelending.com` OWEA (gated on email present) | +3bd |
| `LOA2_Task_Close_Appraisal_POD` | `Appraisal_Proof_of_Delivery_Date__c` | closes "Appraisal received - POD" | — |
| `LOA2_Task_IPR_Wait` | `Submitted_to_Processing_Date__c` | creates "Waiting for Processor - IPR" | +1bd |
| `LOA2_Task_Submitted_To_UW` | `Submitted_to_UW_Date__c` | closes IPR + creates "File submitted to UW" | +2bd |
| `LOA2_Task_Initial_Decision` | `Initial_UW_Decision_Date__c` | closes Submitted-to-UW + creates "Initial decision received" | +2bd |
| `LOA2_Task_Resubmitted_To_UW` | `Resubmitted_Date__c` populated | closes Initial-decision + closes Resubmitted-to-processing + creates "File resubmitted to UW" | +2bd |
| `LOA2_Task_Resubmitted_To_Processing` | `Resubmitted_Date__c` **cleared** (`IsNull true`, **recordTriggerType=Update** so it never fires on create) | closes Resubmitted-to-UW + creates "Resubmitted to processing" | +2bd |
| `LOA2_Task_Close_On_CTC` | `Clear_to_Close_Date__c` | closes "File resubmitted to UW" | — |

**Design notes / gotchas:**
- **LOA2 gate added 2026-08-06 (v4 prod / v3 staging active):** all 6 UW-stage **create** flows now have `LOA2__c IsNull false` in their start filter (matching the 6 original milestone flows), so they only fire when the loan has an LOA2 assigned. Ownership still uses the LOA2(active)→LOA1(active)→Opp Owner fallback for the inactive-LOA2 case. The 2 UW **close** flows (`Close_Appraisal_POD`, `Close_On_CTC`) were deliberately left ungated so they can still close items on any loan. This was a reversal of the earlier "UW flows fire on every loan" behavior — driven by finding milestones owned by the Opp Owner (Josue Toro) on loans with no LOA2 (Lucila Gonzalez Sauz 776002059702).
- Closes use **filter-based `recordUpdates`** (Opportunity__c=$Record.Id AND Name StartsWith '<prefix>' AND Is_Complete__c=false → Status='Completed') — no Get/loop. `StartsWith` is valid in recordUpdates filters. Each close fires on its OWN completion field populating (not gated behind the next create's criteria), so it's NOT fragile to simultaneous batch loads (the disclosures-orphan lesson).
- Tasks 5/6 are a **toggle** on `Resubmitted_Date__c`: populated → close T6 + open T5 (Resubmitted_To_UW); cleared → close T5 + open T6 (Resubmitted_To_Processing). Cycles every resubmittal round until CTC. T6 flow MUST be `recordTriggerType=Update` (not CreateAndUpdate) or requireChange+IsNull-true would fire on every new Borrower opp.
- All fields already existed in **prod**; staging was missing `Appraisal_Proof_of_Delivery_Date__c`, `Initial_UW_Decision_Date__c`, `Resubmitted_Date__c` → created in staging (Date, Admin FLS) before flows.
- **Staging** auto-activated on deploy; **PROD landed them Draft** and required the **2-phase FlowDefinition activation** (deploy flows → deploy `flowDefinitions/*.flowDefinition-meta.xml` with `<activeVersionNumber>1</activeVersionNumber>` for each). All 8 now Active in prod (2026-07-28). Prod deploy omits testLevel (non-Apex; prod has 16 failing local tests that block RunLocalTests). The Task 1 email `Send_Email` throws a staging-only Info warning about the Automated Process User email — harmless, prod OWEA is valid (FHA email precedent). Gotcha reconfirmed: staging can auto-activate record-triggered flows on deploy while prod leaves them Draft → always verify `FlowDefinitionView.IsActive` after a prod flow deploy and run the FlowDefinition step if needed.

### ⚠️ PROD OUTAGE from these 8 flows (2026-07-28 → 2026-07-29) — root cause + fix
All 8 flows' entry criteria were authored as `RecordType.DeveloperName EqualTo 'Borrower'` — a **cross-object reference that record-triggered entry criteria do NOT support**, so it was stored as a null field (`null__NotFound`), deployed + activated clean, then threw at runtime on **every OPEN Opportunity save** (`UNKNOWN_EXCEPTION`, core `530106887`; ALL users incl. admin; UI + API). CLOSED opps were unaffected (the `StageName != Closed Won/Lost` guards short-circuited the AND before the null filter). Debug logs read `Status = Success` (failure is in the entry-criteria DAL, backend-only) — Salesforce Support decoded it. **Fix (2026-07-29):** changed all 8 to `RecordTypeId EqualTo 012Kb000000RpDEIA0` (Borrower Opp RT Id), redeployed as v2, reactivated (2-phase) — verified an open Borrower opp saves with all 8 active. Emergency-mitigated first by deploying FlowDefinitions with `activeVersionNumber=0` (restored saves in ~30s) before fixing. `Last_Action_with_Chatter` had been deactivated as a wrong guess during triage and was re-activated (v2). **Full write-up = gotcha #30. Staging still holds the buggy v1 (auto-activated 2026-07-28); fix there with staging's own Borrower RT Id if staging opp saves are ever needed.**

## Batch Assign Lead Role — mass reassign role/lookup fields on selected Leads (2026-07-27, staging + PROD)

A "Change Owner"-style bulk tool for Leads: select rows in a Lead list view → **Batch Assign Role** button → pick a role/field → pick the value → applies to all selected leads (≤200/run, the Lightning list-view selection cap). Admin-only.

- **Flow `Batch_Assign_Lead_Role`** (screen flow, Active): input var **`ids`** (Text collection — Salesforce auto-populates it with the selected list-view record Ids when the flow is launched from a `/flow/` URL list button). Screen 1 = radio `roleChoice` (Sales Agent / Co-Owner / Owner / Loan Officer / Referred By / NPPM) with 6 pickers on the SAME screen gated by `visibilityRule`. Admin guard: `getRunningUser` (User WHERE Id=$User.Id) → decision `decAdmin` on `getRunningUser.Profile.Name = 'System Administrator'` else `scr_NotAuthorized`. Get selected leads → loop → decision `decField` → per-role assignment sets the matching field (Referred By branch also stamps `Referred_Date__c = $Flow.CurrentDate`, required by VR `Referred_By_Required_For_BD_Borrower`) → Update.
- **Field/picker mapping:** Sales Agent `Sales_Agent__c` (User, filtered to profile **Agent Sales** via `getSalesProfile` + recordChoiceSet `ProfileId` filter), Co-Owner `Co_Owner__c` + Owner `OwnerId` (User, all active `UserType='Standard'`) — these three are **dynamic record-choice dropdowns**; Loan Officer `Loan_Officer__c`, Referred By `Referred_By__c` (Contact), NPPM `NPPM_Realtor__c` — these three are **`flowruntime:lookup` search pickers** bound to the Lead field. LOA1/LOA2/Processor do NOT exist on Lead (Opportunity-only).
- **Button = URL list button** (`WebLink Batch_Assign_Role`, `linkType=url`, `displayType=massActionButton`, `url=/flow/Batch_Assign_Lead_Role?retURL=/lightning/o/Lead/list`, requires `height` + `encodingKey=UTF-8` for openType sidebar). Placed on the Lead **List View** search layout via `<listViewButtons>Batch_Assign_Role</listViewButtons>`. Mirrors the existing `Change_Co_Owner` button (also a `/flow/` URL button).
- **Access model (2026-07-27):** the flow's `decAdmin` guard is `conditionLogic=or`: `getRunningUser.Profile.Name = 'System Administrator'` **OR** `$Permission.Batch_Assign_Lead_Role = true`. Access to non-admins is granted by assigning permission set **`Sales_Agent_Lead`** (label "Sales Agent Lead"), which enables custom permission **`Batch_Assign_Lead_Role`**. To grant/revoke anyone going forward: assign/unassign that permission set (Setup → Permission Sets → Sales Agent Lead → Manage Assignments) — no redeploy. Initially assigned in PROD to **Alejandra Murillo** + **Monica Fernandez** (both Agent Loa On-Demand profile). `$Permission.<apiName>` works as a Boolean in flow decision conditions. No "Run Flows" perm needed — LOAs already run flows.

### Gotchas (hard-won this build)
0. **Prod cutover (2026-08-06): the flow was left DRAFT in prod + ran in USER context — both had to be fixed for non-admins.** (a) `Batch_Assign_Lead_Role` was only ever **Draft** in prod (v1) — admins can run Draft flows so it "worked" for It Support, but Monica Fernandez got the full-page **"Insufficient Privileges"** (non-admins can't run inactive flows). Activate it (2-phase FlowDefinition). (b) After activation it threw an **unhandled fault** — the flow's `getLeads`/`getRunningUser`/`getSalesProfile` lookups had **no faultConnector** so the generic page showed instead of the built-in `scr_Error` screen; wiring all three to `scr_Error` surfaced the real message: `No such column 'ProfileId' on entity 'User'` on the `SELECT Id, ProfileId FROM User` lookup. **This is FLS-in-disguise: in USER context Monica's profile can't read `User.ProfileId`, and SOQL reports a field the running user can't see as "No such column" (not a permission error).** Same context would also block updating leads she doesn't own. **Fix: `<runInMode>SystemModeWithoutSharing</runInMode>`** (added right after `<processType>Flow</processType>`) so the profile lookup + lead updates run in system context. Safe here because the in-flow `decAdmin` guard (`getRunningUser.Profile.Name='System Administrator' OR $Permission.Batch_Assign_Lead_Role`) still gates WHO can run it — `$User.Id`/`$Permission` resolve to the real running user even in system context. Deploy emits an expected Info warning about system-mode data safety.
1. **A VF page hosting `<flow:interview>` renders the flow in CLASSIC runtime** — no conditional field visibility, no `flowruntime:lookup`. To get **Lightning runtime** from a list view, use a **URL list button to `/flow/FlowName`** (NOT a VF page). Salesforce auto-passes selected Ids to a flow Text-collection input var named exactly **`ids`**. (The VF page `BatchAssignLeadRole` + Apex `BatchAssignLeadController`/`_Test` built first are now VESTIGIAL — never deployed to prod; safe to delete from staging/repo.)
2. **Record-choice (`dynamicChoiceSets`) stores the `displayField` value, NOT the Id.** Setting `OwnerId = "sf integrations"` → `MALFORMED_ID`. Fix: add `<outputAssignments><assignToReference>varUserId</assignToReference><field>Id</field></outputAssignments>` to each choice set and reference the variable (not the dropdown field) downstream. `flowruntime:lookup` outputs `.recordId` (a real Id) — fine as-is.
3. **The repo's `objects/Lead/Lead.object-meta.xml` is STAGING-flavored** — its `actionOverrides` reference flexipage `Lead_Record_Realtor`, which does NOT exist in prod → deploying the Lead object to prod fails "Lead_Record_Realtor does not exist or is not a valid override for action View." The SF CLI **merges** that object header into ANY Lead component deploy. To deploy just Lead searchLayouts (or a webLink) to prod, **temporarily move `force-app/main/default/objects/Lead/Lead.object-meta.xml` out of the tree**, deploy the minimal `leadbtn/objects/Lead/Lead.object-meta.xml` (searchLayouts-only), then restore. `leadfix/` is a prior instance of this same side-folder pattern.
4. **`searchLayouts` is a single replace-all element** — deploying it overwrites the whole Lead List View layout (columns + buttons + excluded buttons). No metadata way to "add one button"; base the file on current org state. Prod's ChangeOwner standard button is intentionally excluded (`<excludedStandardButtons>ChangeOwner</excludedStandardButtons>`), which is why the custom role-assign buttons exist.
5. **Prod metadata-only deploys and the 16 failing local tests:** `RunLocalTests` runs ALL local tests; prod currently has **16 failing tests / 190** (pre-existing, unrelated), which roll back any deploy using RunLocalTests. For a **non-Apex** prod deploy, **omit the test level entirely** (do NOT pass `NoTestRun` — prod rejects it explicitly with "testLevel of NoTestRun cannot be used in production organizations"); omitting runs zero tests and succeeds.
