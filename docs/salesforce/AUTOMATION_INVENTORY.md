# Salesforce Automation Inventory — Simo Solutions Group / Homesi

**Org:** HomeSi (`00DKb000000OvoRMAS`) · production, alias `prod`
**Sandbox:** `homesi-staging` (`00DEm000008XXK7MAO`) — not inventoried; staging lags prod.
**Generated:** 2026-09-29 from the live production org, read-only (SOQL/Tooling queries + metadata retrieve).
**Regenerate with:** the procedure in the appendix. Do not hand-edit the tables; regenerate them.

> This is a *descriptive* inventory: what exists, when it fires and what it changes. It covers
> flows, validation / sharing / duplicate / matching / assignment rules and Apex triggers.
> Incident history and design rationale live in [`ORG_REFERENCE.md`](ORG_REFERENCE.md);
> field meanings in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).
>
> "What it does" comes from the flow's own Description when it has one (80 of 154). For the
> other 74 it was written on 2026-09-29 by reading the active flow metadata; those texts are
> marked in the table with a leading `*`. Descriptions are the builder's claim — §7 lists
> cases where the description and the active metadata disagree.

---

## 1. Summary

| Automation type | Count |
|---|---|
| Custom flows — active | **154** (83 more are inactive) |
| — record-triggered on Opportunity | 71 (25 before-save, 46 after-save) |
| — record-triggered on Lead | 36 (17 before-save, 19 after-save) |
| — Task | 12 (1 before-save, 8 after-save, 3 scheduled) |
| — other objects | 20 (see §3) |
| — screen flows · surveys · autolaunched without trigger | 12 · 2 · 1 |
| Managed-package flows (Salesforce-provided) | 82 (59 active) — not detailed, see §6 |
| Validation rules | 29 (24 active): Lead 12/15, Opportunity 10/12, Event 1/1, Work Item 1/1 |
| Sharing rules | 90: 88 criteria-based (Opportunity 45, Lead 41, Work Item 2) + 2 owner-based |
| Duplicate rules | 6 (1 active) · Matching rules 6 (5 active) |
| Lead assignment rules | 1 (inactive) · Auto-response 1 (sample, Case) · Escalation 0 · Workflow rules 0 |
| Apex triggers | 16 custom (15 active) + 33 managed (`tdc_tsw` 22, `ZVC` 11) |

**Opportunity carries 71 active flows plus 5 custom Apex triggers and the managed ones.** Any
change to Opportunity automation should assume interaction effects. Two record-triggered flows
of the same timing on the same object have **no guaranteed order** unless `Trigger order` is set
— see §8.

**Changes since the previous inventory (2026-08-25):** 38 active flows were missing from it
(incl. all 12 screen flows, `LaHaus_Note_History_*`, `Opt_In_Off`/`Opt_in_Off_Opp`,
`Set_Submitted_To_Processing_C40EEP`, `LOA2_Notify_Closing_Milestone`/`_Funding_Milestone`,
the Opportunity Team Member, Chatter and SMS flows). `Loan_Officer_default_by_Opp`,
`Loan_Officer_default_by_lead` and `Opt_Out_Email_flow` are now **inactive**. New validation
rules: `Block_Ineligible_Referred_By_Opp`, `Block_Ineligible_Referred_By_Lead`,
`Allowed_Values_subtype_for_event`, `Milestone_Name_Locked`.

---

## 2. How to read the flow tables

- **Timing:** `before-save` (fast field updates on the triggering record, no DML), `after-save`
  (can touch other records, send email, call Apex), `before-delete`, `scheduled`. `#n` is the
  flow's Trigger Order when one is set.
- **Fires when:** create/update scope, then the entry filters exactly as stored
  (`field operator value`; `[1 AND (2 OR 3)]` is custom logic), or the entry formula.
  _"only when criteria become newly true"_ = `doesRequireRecordChangedToMeetCriteria`
  (see §8.3 — it is **not** "this field changed").
- **Effects:** `sets` = fields written on the triggering record; `updates X (fields)` = other
  records updated; `creates` / `deletes`; `email`, `apex <class>`, `subflow`. Collections are
  shown as `Object[]`.
- Ids such as `012Kb000000RpDEIA0` are record types: Borrower Opportunity = `012Kb000000RpDEIA0`.
  Record-type Ids are org-specific (staging differs).

---

## 3. Flows — active, custom (154)

### 3.1 Opportunity (71)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Assign_record_type_Opp_related_to_contact` | after-save | on update; `RecordTypeId IsChanged true`; scheduled paths: `AsyncAfterCommit:` | * When an Opportunity's record type changes, asynchronously loops its contact roles and appends Realtor, Loan Officer or Broker to each Contact's RecordTypes_related__c multi-select. ⚠️ §7 | updates Contact (RecordTypes_related__c) ×6 |
| `Auto_Update_Stage_Based_on_CurrentStatus` | after-save | on update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Current_Status__c IsChanged true` | This new version avoids the integration user to reopen an opportunity if it is CLOSE WON or CLOSE LOST. | sets `StageName`, `Ratified_Date__c` |
| `Clear_Current_Status_On_Manual_Close` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Current_Status__c IsNull false`, `StageName EqualTo Closed Lost`, `StageName EqualTo Closed Won` [1 AND 2 AND (3 OR 4)]; _only when criteria become newly true_ | When an Opportunity Stage changes to Closed Lost or Closed Won and Current Status is still populated, blank Current_Status__c. Covers the manual-close gap where Sync_Current_Status_with_Stage is guarded out for closed stages and the data-driven close path did… | sets `Current_Status__c` |
| `Close_LOA_Work_Items_On_Opp_Close` | after-save | on update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName EqualTo Closed Won`, `StageName EqualTo Closed Lost`, `Current_Status__c EqualTo Archive Loan` [1 AND (2 OR 3 OR 4)] | When a Borrower Opportunity closes (Stage = Closed Won or Closed Lost) OR Current_Status__c is set to "Archive Loan" (incl. by another flow), set all open LOA Work Items (Mortgage_Condition__c, Is_Complete__c = false) on the opp to Status__c = "N/A". After-sa… | updates Mortgage_Condition__c[] |
| `Complete_LOA1_Work_Items_On_Ratified` | after-save | on update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Current_Status__c EqualTo Ratified`; _only when criteria become newly true_ | When a Borrower Opportunity's Current_Status__c transitions to "Ratified", mark all still-open LOA Work Items (Mortgage_Condition__c, Is_Complete__c=false) with Agent_Role__c = "LOA1" on that opp as Status__c = "Completed" (the LOA1 -> LOA2 handoff). Closed L… | updates Mortgage_Condition__c[] |
| `Copy_Stat_Risk_To_Healthiness` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Healthiness__c IsNull true`, `Stat_Closing_Risk__c IsNull false` | After-save on Borrower Opportunities: when Healthiness__c is blank and the Stat_Closing_Risk__c formula has a value, copy Stat Closing Risk into Healthiness. Values align 1:1 (On Track / Delayed / Out of Scope) after the 2026-07-13 rename of Healthy -> On Tra… | updates Opportunity (Healthiness__c) |
| `Create_NPPM_On_Realtor_Closed_Won` | after-save | on create/update; `NPPM__c EqualTo true`, `StageName EqualTo Closed Won`; _only when criteria become newly true_ | * When a Realtor Opportunity with NPPM__c = true becomes Closed Won, creates one NPPM__c record (name, brokerage, email, phone, role, owner, source opportunity) unless one already exists for it. | creates `NPPM__c` |
| `hasTaxID` | after-save | on create/update; `SSN_ITIN__c StartsWith 9` | * When an Opportunity is saved with SSN_ITIN__c starting with 9 (an ITIN), sets TaxID__c = true. | sets `TaxID__c` |
| `LOA_Assignment_First_Touch` | after-save | on create/update; `LOA__c IsChanged true`, `LOA__c IsNull false`, `LOA_2__c IsChanged true`, `LOA_2__c IsNull false`, `Processor_Jr_Text__c IsChanged true`, `Processor_Jr_Text__c IsNull false`, `LOA1__c IsChanged true`, `LOA1__c IsNull false`, `LOA2__c IsChanged true`, `LOA2__c IsNull false`, `Processor_Jr__c IsChanged true`, `Processor_Jr__c IsNull false`, `Loan_Processor__c IsChanged true`, `Loan_Processor__c IsNull false` [(1 AND 2) OR (3 AND 4) OR (5 AND 6) OR (7 AND 8) OR (9 AND 10) OR (11 AND 12) OR (13 AND 14)] | Merged flow combining LOA1_and_LOA2_Automatic_Assignment (text fields) and LOA_First_Follow_Up (lookup fields). For each role (LOA1, LOA2, Processor Jr): resolves the User (lookup field if set and active, else by Name from the text field), writes the lookup f… | sets `Loan_Processor_Assignment_Date__c`, `Loan_Processor_User__c`, `LOA1_Assignment_Date__c`, `LOA1__c`, `LOA2_Assignment_Date__c`, `LOA2__c`, `Processor_Jr_Assignment_Date__c`, `Processor_Jr__c`; updates Task (OwnerId); creates `Mortgage_Condition__c`; creates `Task` |
| `LOA2_FHA_Docs_Email_to_Nila` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Disclosures_Signed_Date__c IsNull false`, `Loan_Type__c EqualTo FHA`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`, `Branch__c NotEqualTo 703`, `Branch__c NotEqualTo 724`; _only when criteria become newly true_ | When Disclosures_Signed_Date__c populated AND Loan_Type__c is FHA, sends the FHA docs request email directly (native Send Email) to Homesisupport@supremelending.com + LOA1 + LOA2 + the Loan Officer (Loan_Officers__r.Email__c). Reworked 2026-06-08 from firing… | email |
| `LOA2_Notify_Closing_Milestone` | after-save | on create/update; `Closing_Milestone_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Closing_Milestone_Date__c IsNull false` | * When Closing_Milestone_Date__c is set on an Opportunity of record type 012Kb000000RpDEIA0, emails a 'Closing Milestone Finished' notice to the Loan Officer, LOA2 and Loan Processor. ⚠️ §7 | email |
| `LOA2_Notify_COC_CD` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `COC_CD_Trigger__c IsChanged true`, `COC_CD_Trigger__c IsNull false`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost` | Emails LO + LOA2 + Loan Processor when COC_CD_Trigger__c changes, signalling a possible Change of Circumstance. COC_CD_Trigger__c is a Number(18,0) counter written by Encompass, so IsChanged is the trigger - each increment is a new COC event. No work item is… | email |
| `LOA2_Notify_COC_LE` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `COC_LE_Trigger__c IsChanged true`, `COC_LE_Trigger__c IsNull false`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost` | Emails LO + LOA2 + Loan Processor when COC_LE_Trigger__c changes, signalling a possible Change of Circumstance. COC_LE_Trigger__c is a Number(18,0) counter written by Encompass, so IsChanged is the trigger - each increment is a new COC event. No work item is… | email |
| `LOA2_Notify_Funding_Milestone` | after-save | on create/update; `Funding_Milestone_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Funding_Milestone_Date__c IsNull false` | * When Funding_Milestone_Date__c is set on an Opportunity of record type 012Kb000000RpDEIA0, emails a 'Funding Milestone Completed' notice to the Loan Officer, LOA2 and Loan Processor. ⚠️ §7 | email |
| `LOA2_Task_Appraisal_POD` | after-save | on create/update; `Appraisal_Received_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost`, `Appraisal_Received_Date__c IsNull false` | * When Appraisal_Received_Date__c is set on an open Opportunity (RT 012Kb000000RpDEIA0), emails LO/LOA2/Processor and, if LOA2 is assigned, creates a 3-business-day 'Appraisal received - POD' Mortgage_Condition__c work item. ⚠️ §7 | creates `Mortgage_Condition__c`; email |
| `LOA2_Task_Close_Appraisal_POD` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Appraisal_Proof_of_Delivery_Date__c IsNull false`; _only when criteria become newly true_ | * When an Opportunity (RT 012Kb000000RpDEIA0) gets an Appraisal_Proof_of_Delivery_Date__c, marks its open 'Appraisal received - POD' Mortgage_Condition__c work items Completed. | updates Mortgage_Condition__c (Status__c) |
| `LOA2_Task_Close_On_Appraisal_Ordered` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Appraisal_Ordered_Date__c IsNull false`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`; _only when criteria become newly true_ | When Appraisal_Ordered_Date__c populated, closes any open Order Appraisal work item. | updates Mortgage_Condition__c (Status__c) |
| `LOA2_Task_Close_On_COC_Cleared` | after-save | on update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`, `LE_Revised_Date__c IsChanged true`, `LE_Revised_Date__c IsNull false`, `ICD_Date__c IsChanged true`, `ICD_Date__c IsNull false` [1 AND 2 AND 3 AND ((4 AND 5) OR (6 AND 7))] | When LE_Revised_Date__c or ICD_Date__c becomes populated AND is on/after Lock_Date__c, closes the open "COC Rate Locked" work item on the opp. | updates Mortgage_Condition__c (Status__c) |
| `LOA2_Task_Close_On_CTC` | after-save | on create/update; `Clear_to_Close_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Clear_to_Close_Date__c IsNull false`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost` | * When Clear_to_Close_Date__c is set on an open Opportunity (RT 012Kb000000RpDEIA0), emails a Clear-to-Close congratulation to LO/LOA2/Processor and completes open 'File resubmitted to UW' work items. ⚠️ §7 | updates Mortgage_Condition__c (Status__c); email |
| `LOA2_Task_Close_On_Disclosures_Signed` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Disclosures_Signed_Date__c IsNull false`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`; _only when criteria become newly true_ | When Disclosures_Signed_Date__c populates, closes any open "Issue Disclosures" AND "Disclosures Follow-Up" LOA2 milestone work items on the opp. Dedicated close flow keyed on the actual completion date so simultaneous date loads (LE Sent + Disclosures Signed… | updates Mortgage_Condition__c[] |
| `LOA2_Task_Close_On_ICD_Received` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `ICD_Date__c IsNull false`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`; _only when criteria become newly true_ | When ICD_Date__c is populated, closes any open "ICD Request" work item on the opp. | updates Mortgage_Condition__c (Status__c) |
| `LOA2_Task_Close_On_Submitted_To_Processing` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Submitted_to_Processing_Date__c IsNull false`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`; _only when criteria become newly true_ | When Submitted_to_Processing_Date__c is populated, closes any open "Send to Processing" work item on the opp. | updates Mortgage_Condition__c (Status__c) |
| `LOA2_Task_COC_Rate_Locked` | after-save | on create/update; `Lock_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Lock_Date__c IsNull false`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won` | Creates a "COC Rate Locked" work item for LOA2 when Lock_Date__c is populated. Due 24h (1 day) after lock date. LOA2 inactive falls back to Opp Owner. Duplicate-guarded. Skips closed opps. | creates `Mortgage_Condition__c` |
| `LOA2_Task_Disclosures_FollowUp` | after-save | on create/update; `LE_Sent_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `LE_Sent_Date__c IsNull false`, `Disclosures_Signed_Date__c IsNull true`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won` | When LE_Sent_Date__c populated and Disclosures_Signed_Date__c blank: closes Issue Disclosures work item, creates Disclosures Follow-Up work item due LE_Sent_Date__c + 2 days. | updates Mortgage_Condition__c (Status__c); creates `Mortgage_Condition__c`; email |
| `LOA2_Task_ICD_Request` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Title_Commitment_Date__c IsNull false`, `Hazard_Insurance_Date__c IsNull false`, `Lock_Date__c IsNull false`, `ICD_Date__c IsNull true`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`; _only when criteria become newly true_ | Creates an "ICD Request" work item for LOA2 when Title_Commitment_Date__c, Hazard_Insurance_Date__c and Lock_Date__c are all populated and ICD_Date__c is still blank. Due = flow run date + 1 business day. LOA2 inactive falls back to Opp Owner. Duplicate-guard… | creates `Mortgage_Condition__c` |
| `LOA2_Task_Initial_Decision` | after-save | on create/update; `Initial_UW_Decision_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost`, `Initial_UW_Decision_Date__c IsNull false` | * When Initial_UW_Decision_Date__c is set on an open Opportunity (RT 012Kb000000RpDEIA0), emails LO/LOA2/Processor and, if LOA2 is assigned, completes the 'File submitted to UW' item and creates a 2-business-day 'Initial decision received' w… ⚠️ §7 | updates Mortgage_Condition__c (Status__c); creates `Mortgage_Condition__c`; email |
| `LOA2_Task_IPR_Wait` | after-save | on create/update; `Submitted_to_Processing_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost`, `Submitted_to_Processing_Date__c IsNull false` | * When Submitted_to_Processing_Date__c is set on an open Opportunity (RT 012Kb000000RpDEIA0), emails LO/LOA2/Processor and, if LOA2 is assigned, creates a 1-business-day 'Waiting for Processor - IPR review' Mortgage_Condition__c work item. ⚠️ §7 | creates `Mortgage_Condition__c`; email |
| `LOA2_Task_Issue_Disclosures` | after-save | on create/update; `Application_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Application_Date__c IsNull false`, `LE_Sent_Date__c IsNull true`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won` | Creates Issue Disclosures work item for LOA2 when Application_Date__c populated and LE_Sent_Date__c blank. Due date = LE_Due_Date__c or Application_Date__c + 3. Duplicate-guarded. | creates `Mortgage_Condition__c`; email |
| `LOA2_Task_Order_Appraisal` | after-save | on create/update; `Disclosures_Signed_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Disclosures_Signed_Date__c IsNull false`, `Appraisal_Ordered_Date__c IsNull true`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won` | When Disclosures_Signed_Date__c populated and Appraisal_Ordered_Date__c blank: closes Disclosures Follow-Up work item, creates Order Appraisal work item due Disclosures_Signed_Date__c + 2 days. | updates Mortgage_Condition__c (Status__c); creates `Mortgage_Condition__c` |
| `LOA2_Task_Resubmitted_To_Processing` | after-save | on update; `LOA2__c IsNull false`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost`, `Resubmitted_Date__c IsChanged true`, `Resubmitted_Date__c IsNull true` | * On Opportunity update (RT 012Kb000000RpDEIA0, open, LOA2 assigned), completes open 'File resubmitted to UW' items and creates a 2-business-day 'Resubmitted to processing - awaiting LP conditions' work item. (fires when Resubmitted_Date__c… | updates Mortgage_Condition__c (Status__c); creates `Mortgage_Condition__c` |
| `LOA2_Task_Resubmitted_To_UW` | after-save | on create/update; `Resubmitted_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost`, `Resubmitted_Date__c IsNull false` | * When Resubmitted_Date__c is set on an open Opportunity (RT 012Kb000000RpDEIA0), emails LO/LOA2/Processor and, if LOA2 is assigned, completes Initial-decision and Resubmitted-to-processing items and creates a 2-business-day 'File resubmitte… ⚠️ §7 | updates Mortgage_Condition__c (Status__c) ×2; creates `Mortgage_Condition__c`; email |
| `LOA2_Task_Send_to_Processing` | after-save | on create/update; `Disclosures_Signed_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Disclosures_Signed_Date__c IsNull false`, `Submitted_to_Processing_Date__c IsNull true`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won` | Creates "Send to Processing" work item for LOA2 when Disclosures_Signed_Date__c is populated and Submitted_to_Processing_Date__c is still blank. Due Disclosures_Signed_Date + 2 days. LOA2 inactive falls back to Opp Owner. Duplicate-guarded. Skips closed opps. | creates `Mortgage_Condition__c`; email |
| `LOA2_Task_Submitted_To_UW` | after-save | on create/update; `Submitted_to_UW_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `StageName NotEqualTo Closed Won`, `StageName NotEqualTo Closed Lost`, `Submitted_to_UW_Date__c IsNull false` | * When Submitted_to_UW_Date__c is set on an open Opportunity (RT 012Kb000000RpDEIA0), emails LO/LOA2/Processor and, if LOA2 is assigned, completes the IPR Wait item and creates a 2-business-day 'File submitted to UW' work item. ⚠️ §7 | updates Mortgage_Condition__c (Status__c); creates `Mortgage_Condition__c`; email |
| `Lock_Expiration_Work_Items` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Lock_Exp_Date__c IsNull false`, `Closed_Loan__c EqualTo false`, `LOA2__c IsNull false`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won`; scheduled paths: `Three_Days_Before_Expiration: -3 Days RecordField Lock_Exp_Date__c`, `One_Day_After_Expiration: 1 Days RecordField Lock_Exp_Date__c` | Lock expiration work items, driven by scheduled paths on Lock_Exp_Date__c. 3 days BEFORE expiration: creates "Lock is about to expire" LOA2 work item due on the expiration date. 1 day AFTER expiration (loan still open): closes the about-to-expire item and cre… | updates Mortgage_Condition__c (Status__c); creates `Mortgage_Condition__c` ×2 |
| `Lock_Rate_Locked_Email_Alert` | after-save | on create/update; `Lock_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Lock_Date__c IsNull false`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won` | Rate Locked Alert (notification #5, reworked 2026-08-25): when Lock_Date__c CHANGES on an open Borrower opportunity, emails Loan Officer + LOA2 + Loan Processor. Sent from the sfintegrations@supremelending.com org-wide address (Mimecast anti-spoofing requires… | email |
| `Lock_Renewal_Close_Items` | after-save | on update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `Lock_Exp_Date__c IsChanged true` | When Lock_Exp_Date__c changes to a date in the future (re-lock), auto-closes any open "Lock has expired" and "Lock is about to expire" work items on the opportunity. Completed_Date__c is stamped by the sync flow. | updates Mortgage_Condition__c (Status__c) ×2 |
| `Opp_Keyword_Notes_Contact_Flow` | after-save | on create/update | * On Opportunity create/update by anyone except System Administrators, sets Contacted__c to true when Jungo_Notes__c contains keywords like itin, tax, credit, cash, zelle, trabajo or social. ⚠️ §7 | sets `Contacted__c` |
| `Opportunity_Stage_Date_Tracker` | after-save | on update; `StageName IsChanged true` | Automatically captures the date when an Opportunity changes its Stage (Qualification, Proposal, Negotiation, or Closed Won). | sets `Date_Meeting_Attended__c`, `StatusOfTheMeeting__c`, `Closed_Won_Date__c`, `DateInviteSent__c`, `Need_analysis_Date__c`, `Negotiation_Date__c`, `Pre_Qualified_Doc_requested_Date__c`, `Proposal_Date__c`, `Qualification_Date__c` |
| `Recruitment_Rule_Opportunity_Contact_Sync` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDHIA0`, `Recruitment_Role__c IsChanged true`, `ContactId IsNull false` [1 AND 2 AND 3] | * After-save on B2B Opportunities (RecordTypeId 012Kb000000RpDHIA0) with a Contact when Recruitment Role changes; copies Recruitment_Role__c onto the related Contact. | updates Contact (Recruitment_Role__c) |
| `Require_Note_Before_Proposal_Realtor_Oportunities` | after-save | on update; `StageName EqualTo Proposal`, `StageName IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDHIA0` | Block Realtor opportunities from moving to Proposal until a note or a Chatter post is added. | — |
| `Reset_stage_by_hierarchy` | after-save | on update; `StageName IsChanged true` | * After-save on Opportunity stage change; if the stage moves backwards (e.g. from Closed Won/Lost, Negotiation or Proposal to an earlier stage), it reverts StageName (and loss reason) to the prior value. ⚠️ §7 | sets `Reason_for_loss__c`, `StageName` |
| `Update_Contact_Phone_from_Opportunity` | after-save | on create/update; `Phone__c IsNull false`, `Phone__c IsChanged true`; scheduled paths: `AsyncAfterCommit:` | When the phone in Opportunity changes, update the phone of the related Contact. | updates Contact (Phone) |
| `Update_current_status_by_new_or_closed_stage` | after-save | on create/update; `StageName EqualTo Qualification`, `StageName EqualTo Closed Won`, `StageName EqualTo Closed Lost` (any) | * After-save on Opportunity at Qualification, Closed Won or Closed Lost; for RecordTypeId 012Kb000000RpDEIA0 at Qualification with no prior status, sets Current_Status__c to 'Pre-Qualified/Doc Requested'. ⚠️ §7 | sets `Current_Status__c` |
| `Update_Pre_approved_date_current_status` | after-save | on create/update; `Current_Status__c EqualTo Pre-Approved`, `RecordTypeId EqualTo 012Kb000000RpDEIA0` | * After-save on Opportunities of RecordTypeId 012Kb000000RpDEIA0 with Current Status Pre-Approved; stamps Pre_Approved_Date__c with today if it was previously blank. | sets `Pre_Approved_Date__c` |
| `Update_Realtor_Branch_From_Opportunity` | after-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDHIA0`, `Branch__c IsChanged true` [1 AND 2] | When a Realtor-record-type Opportunity is created or its Branch__c changes, this flow propagates the new Branch__c to the Primary OCR Contact (the realtor). Keeps Contact.Branch__c in sync with the realtor's origination Opp without needing the RealtorBranchBa… | updates Contact (Branch__c) |
| `Update_Realtor_Last_Referral_Date` | after-save | on create/update; `Referred_By__c IsNull false`, `Referred_Date__c IsNull false`, `Referred_By__c IsChanged true`, `Referred_Date__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0` [1 AND 2 AND (3 OR 4) AND 5] | Whenever an Opportunity is created or updated with Referred_By__c and Referred_Date__c set (and either field changed), this flow updates the related Contact (Realtor)'s Last_Referral_Date__c — but only if the new date is later than the current value. The Real… | updates Contact (Last_Referral_Date__c) |
| `Append_Delay_Details_History` | before-save | on create/update | Before-save flow on Opportunity. When Delay_Details__c (the writable "latest" delay note) changes and is non-blank, prepends a timestamped, user-stamped entry to Delay_Details_History__c (newest on top), same pattern as the Production Support / LOA Work Item… | sets `Delay_Details_History__c` |
| `Append_Prod_Support_Note_History` | before-save | on create/update | Before-save flow on Opportunity. When Prod_Support_Note__c (the writable Production Support "latest note") changes and is non-blank, prepends a timestamped, user-stamped entry to Prod_Support_Note_History__c (newest on top), like the LOA Work Item Latest Note… | sets `Prod_Support_Note_History__c` |
| `branch_default_when_Opp_create` | before-save | on create/update; `OwnerId IsChanged true`, `Branch__c EqualTo` (any) | * Before an Opportunity is saved with a changed owner or blank Branch__c, sets Branch__c to a branch code chosen by matching the owner's email against a hard-coded list. ⚠️ §7 | sets `Branch__c` |
| `Clean_LoanID_OnOpportunity` | before-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `LoanId__c StartsWith {`, `LoanId__c EndsWith }` [1 AND (2 OR 3)] | Automatically removes curly brackets { and } from the Loan ID field on Opportunity records whenever the field is created or updated. Ensures the Loan ID is always stored in a clean, consistent format. | sets `LoanId__c` |
| `LaHaus_Note_History_Opportunity` | before-save | on create/update; formula `AND( NOT(ISBLANK({!$Record.LaHaus_Last_Note__c})), OR( ISNEW(), ISCHANGED({!$Record.LaHaus_Last_Note__c}) ) )` | Prepend LaHaus_Last_Note__c to LaHaus_Note_History__c (newest on top). v4: an Opportunity born by lead conversion already carries the mapped history and must not re-append its last note. | sets `LaHaus_Note_History__c` |
| `Last_Action_Date_with_Last_Modified_Date` | before-save | on create/update | * Before any Opportunity is created or updated by a non-admin user, sets Last_Action_Date__c to today. | sets `Last_Action_Date__c` |
| `Opportunity_Stage_Date_Tracker_Create` | before-save | on create | * On Opportunity creation, sets StageName to 'Proposal' for Entity loans (Loan_Program__c = F30EEP); otherwise stamps today into Pre_Qualified_Doc_requested_Date__c, Qualification_Date__c and DateInviteSent__c. | sets `Pre_Qualified_Doc_requested_Date__c`, `Qualification_Date__c`, `DateInviteSent__c`, `StageName` |
| `Opt_in_Off_Opp` | before-save | on create/update; formula `OR( AND( {!$Record.tdc_tsw__SMS_Opt_out__c}, OR( ISNEW(), ISCHANGED({!$Record.tdc_tsw__SMS_Opt_out__c}) ) ), AND( {!$Record.SMS_Opt_In__c},…` | SMS opt-in and opt-out are mutually exclusive. v2: also runs on create (ISNEW), and opt-out wins when a record is born with both flags true. | sets `tdc_tsw__SMS_Opt_out__c`, `SMS_Opt_In__c` |
| `Original_Est_Closing_Date_Update` | before-save | on create/update; `Application_Date__c IsChanged true` | * Before an Opportunity is saved with a changed Application_Date__c, copies Est_Closing_Date__c into Org_Est_Closing_Date__c to preserve the original estimated closing date. | sets `Org_Est_Closing_Date__c` |
| `Prevent_Duplicate_LoanGuid_Borrower_Opportunity` | before-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDEIA0`, `LoanId__c IsNull false`, `Loan__c IsNull false` [1 AND (2 OR 3)] | This flow checks if there is another Borrower Opportunity with the same LoanGuid. If a match is found, it shows an error message and blocks the save | — |
| `Recruitment_Rule_Opportunity` | before-save | on create/update; formula `AND( {!$Record.RecordTypeId} = "012Kb000000RpDHIA0", OR( ISNEW(), ISCHANGED({!$Record.NPPM__c}), ISCHANGED({!$Record.Recruitment_Role__c})…` | * Before-save on B2B Opportunities (RecordTypeId 012Kb000000RpDHIA0) when created or NPPM/Recruitment Role changes; blocks the save unless Recruitment Role matches NPPM (checked: Realtor-BD/Realtor-NPPM; unchecked: blank/Realtor). | — |
| `Reset_current_status_by_hierarchy_Loan_Officer_V1` | before-save | on update; `Current_Status__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDGIA0` | Close Opportunity when current status is Hired by Loan Officer | sets `StageName` |
| `Set_Branch_Affinity_When_Affinity_Program` | before-save | on create/update; `Affinity_Program__c EqualTo true`, `Branch__c NotEqualTo Affinity` | When Affinity_Program__c is true, force Branch__c = 'Affinity' (always overwrite). Before-save, Opportunity. Gated so it only assigns when Branch is not already Affinity. | sets `Branch__c` |
| `Set_Needs_Agent_Date_Opp` | before-save | on update; `Needs_Agent__c IsChanged true` | Maintains Needs_Agent_Date__c as a waiting-since stamp on Opportunity. Writes the timestamp only when Needs Agent goes true AND the date is blank, so repeat escalations do not reset the clock. Clears the date when Needs Agent goes false. Before-save, so no ex… | sets `Needs_Agent_Date__c` |
| `Set_NPPM_From_Referral_Chain` | before-save | on create/update; formula `AND( {!$Record.RecordTypeId} = "012Kb000000RpDEIA0", NOT(ISBLANK({!$Record.Referred_By__c})), OR( ISNEW(), ISCHANGED({!$Record.Referred_By_…` | Borrower Opportunity: derives NPPM_Realtor__c, Referred_By_NPPM__c and Strategy__c from the referral chain using record Ids only (no name/email matching). Handles BOTH referral shapes. 1-HOP (direct): the Referred_By contact IS an NPPM - their Realtor Opp is… | sets `NPPM_Realtor__c`, `Referred_By_NPPM__c`, `Strategy__c` |
| `Set_Submitted_To_Processing_C40EEP` | before-save | on create/update; `Loan_Program__c EqualTo C40EEP`, `Loan_Processor__c IsChanged true`, `Loan_Processor__c IsNull false`, `Submitted_to_Processing_Date__c IsNull true` | C40EEP loans only: stamps Submitted to Processing Date with today when a Loan Processor is first assigned. See the flowDefinition header for the full rationale and the downstream email consequence. | sets `Submitted_to_Processing_Date__c` |
| `Sync_Current_Status_with_Stage` | before-save | on update; `StageName IsChanged true`, `StageName NotEqualTo Closed Lost`, `StageName NotEqualTo Closed Won` | Keeps Current Status aligned with the Opportunity Stage Name when users manually update the Stage. Currently updates Current_Status__c to “NEGOTIATION” when the Stage changes to “Negotiation.” Future logic for other Stages can be added within the same Flow if… | sets `Current_Status__c`, `Pre_Approved_Date__c`, `Ratified_Date__c` |
| `Sync_Loan_Officer_Text` | before-save | on create/update | Mirrors the related Loan Officer record's Name into Opportunity.Loan_Officer_Text__c on every create/update. Powers criteria-based sharing rules and other settings that need a plain-text loan officer name on the Opportunity itself. | sets `Loan_Officer_Text__c` |
| `Update_Close_Date_for_Borrower_Opportunities` | before-save | on create/update; `Loan_Amount__c IsChanged true`, `RecordTypeId EqualTo 012Kb000000RpDEIA0` [1 AND 2] | This flow updates the Opportunity Close Date when the Disbursement Date changes, and updates the Amount field when the Loan Amount changes. | sets `Amount` |
| `Update_current_Milestone_Loan_status_Opp` | before-save | on create/update; formula `AND( {!$Record.RecordType.DeveloperName} = "Borrower", NOT(ISPICKVAL({!$Record.StageName}, "Closed Won")), OR( NOT(ISPICKVAL({!$Record.Stag…` | Derives Opportunity Stage and Current Status from dates, loan program, and loan status. Replaces the prior milestone-based stage derivation. Priority router; first match wins. v26: entry criteria moved to a formula so a Closed Lost opp can re-enter when Encom… | sets `Reason_for_loss__c`, `Explain_reason_for_loss__c`, `StageName`, `Current_Status__c`, `Pre_Qualified_Doc_requested_Date__c`, `Qualification_Date__c`, `DateInviteSent__c`, `CloseDate` |
| `Update_Invite_Date_for_Realtor_Opportunities` | before-save | on update; `RecordTypeId EqualTo 012Kb000000RpDHIA0`, `StatusOfTheMeeting__c IsChanged true` | The date fields are updated automatically when the meeting status is set to any value for realtor-type opportunities. | sets `Date_Meeting_Attended__c`, `DateInviteAccepted__c`, `DateInviteSent__c`, `DateMeetingRejected__c` |
| `Update_Lifecycle_on_base_the_Stage_Opportunities_B2B` | before-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDHIA0` | * Before-save on B2B Opportunities (RecordTypeId 012Kb000000RpDHIA0); sets LIfecycle_stage__c from StageName: Qualification/Needs Analysis=MQL, Proposal=SQL, Negotiation=OPP, Closed Won=Customer. | sets `LIfecycle_stage__c` |
| `Update_Ratified_date_current_status` | before-save | on create/update; `Application_Date__c IsNull false`, `RecordTypeId EqualTo 012Kb000000RpDEIA0` | * Before-save on Opportunities of RecordTypeId 012Kb000000RpDEIA0 with an Application Date; sets Ratified_Date__c to Sales_Contract_Ratified_Date__c if present, otherwise to Application_Date__c. | sets `Ratified_Date__c` |
| `Update_Referred_Date_Opportunity` | before-save | on create/update; formula `NOT(ISBLANK({!$Record.Referred_By__c})) \|\| ISCHANGED({!$Record.Referred_By__c})` | Stamp Referred Date on Opportunity when Referred By is added without a date, and clear Referred Date when Referred By is removed. If an automation/import (LOS, Lead conversion mapping, etc.) provides both Referred By and Referred Date together, the explicit d… | sets `Referred_Date__c` |
| `Update_Strategy_Opps` | before-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDHIA0`, `Referred_By__c IsChanged true`, `OwnerId IsChanged true`, `Affinity_Program__c IsChanged true`, `Referred_By_NPPM__c IsChanged true` [1 OR 2 OR 3 OR 4 OR 5] | Sets Opportunity.Strategy__c. Affinity if Affinity_Program = true; NPPM if "Was this referred by an NPPM?" = Yes or the owner is a Realtor-NPPM/Realtor-BD; otherwise B2B Strategy (default). Reworked 2026-07-17 to drive NPPM off the Referred_By_NPPM__c field i… | sets `Strategy__c` |

### 3.2 Lead (36)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `add_lead_to_campaign` | after-save | on create | * When a Lead with leadCapture__c = true is created, sets Company/LeadSource=Facebook/Media=Paid/record type, adds it to the campaign named in Campaign_name__c (Responded), and assigns the owner based on campaign name. ⚠️ §7 | sets `Company`, `LeadSource`, `Media__c`, `RecordTypeId`, `OwnerId`, `Co_Owner__c`, `Referred_By__c`; updates User (Round_Robin__c); creates `CampaignMember` |
| `Broker_Position_to_Contact_Title` | after-save | on update; `IsConverted EqualTo true`, `RecordTypeId EqualTo 012Kb000000RpDBIA0` | This flow triggers when a Broker lead is converted. It automatically copies the value from the Position picklist (POC or LO) to the Title field on the created Contact, ensuring consistent information transfer between the Lead and Contact records. | updates Contact (Title) |
| `change_owner_to_duplicate_leads_no_borrowers` | after-save | on update; `Status EqualTo Discarded`, `Reasons_for_discarding__c EqualTo Duplicate Lead`, `RecordTypeId NotEqualTo 012Kb000000RpDAIA0`, `Original_Lead__c IsNull false`, `Original_Opportunity__c IsNull false` [1 AND 2 AND 3 AND (4 OR 5)] | * When a non-borrower Lead is updated to Status Discarded with reason 'Duplicate Lead' and has an original Lead or Opportunity, reassigns its owner to one fixed user. ⚠️ §7 | sets `OwnerId` |
| `Copy_Chatter_Posts_From_Lead_To_Opportunity` | after-save | on update; `IsConverted EqualTo true`; _only when criteria become newly true_ | Copies the texts of a Lead's Chatter posts when it becomes an Opportunity. | creates `FeedItem[]`; creates `ContentDocumentLink[]`; apex FormatChatterPost |
| `Date_of_update_status_movement` | after-save | on update; `Status IsChanged true` | * When a Lead's Status changes, stamps Status_movement_date__c with the current date/time. | sets `Status_movement_date__c` |
| `Jorge_Zuzunaga_New_Lead_Facebook` | after-save | on create/update; `LeadSource EqualTo Facebook`, `leadCapture__c EqualTo true`; _only when criteria become newly true_ | Email notification when a new lead arrives from Salesforce | email ×4 |
| `Lead_Status_Date_Tracker` | after-save | on create/update | * On Lead create/update, stamps today's date into New_Date__c, Working_Date__c, On_hold_Date__c, discarded_date__c or Qualified_Date__c the first time the Lead reaches that Status. | sets `discarded_date__c`, `New_Date__c`, `On_hold_Date__c`, `Qualified_Date__c`, `Working_Date__c` |
| `No_Contacted_Reasons_for_discarding` | after-save | on create/update; `Reasons_for_discarding__c EqualTo Unresponsive`, `Notes__c Contains no contest` (any) | * On Lead create/update, when Reasons_for_discarding__c is 'Unresponsive' or Notes__c contains 'no contest', sets Contacted__c to false. ⚠️ §7 | sets `Contacted__c` |
| `not_allow_to_create_non_borrowers_leads` | after-save | on create; `RecordTypeId NotEqualTo 012Kb000000RpDAIA0`, `Status EqualTo Discarded`, `Reasons_for_discarding__c EqualTo Duplicate Lead`, `Original_Lead__c IsNull false`, `Original_Opportunity__c IsNull false` [1 AND 2 AND 3 AND (4 OR 5)] | * Blocks creation of a non-Borrower (RT not 012Kb000000RpDAIA0) Lead that is Discarded as 'Duplicate Lead' with an Original Lead/Opportunity, showing an error with a link to the original record. ⚠️ §7 | — |
| `Notes_Review_for_Contact_Flow` | after-save | on create/update | * On every Lead create/update, sets Contacted__c to true when Notes__c or Jungo_Notes__c contains keywords like itin, tax, credit, cash, zelle, trabajo or social. ⚠️ §7 | sets `Contacted__c` |
| `Realtor_AI_Profile` | after-save | on update; `RecordTypeId EqualTo 012Kb000000RpDDIA0`, `AI_Trigger__c EqualTo true`, `RecordTypeId EqualTo 012Kb000000RpDCIA0` [(1 OR 3) and 2]; _only when criteria become newly true_; scheduled paths: `AsyncAfterCommit:` | * When AI_Trigger__c becomes true on a Lead of record type 012Kb000000RpDDIA0 or 012Kb000000RpDCIA0, sets AI_Status__c to Pending and asynchronously posts the Lead's contact details to a Make.com webhook. ⚠️ §7 | sets `AI_Run_Started__c`, `AI_Status__c`; externalService SendingRequestToMake.SendingPostRequest |
| `Repoint_FUR_On_Lead_Convert` | after-save | on update; `IsConverted EqualTo true`, `ConvertedOpportunityId IsNull false`; _only when criteria become newly true_ | On Lead conversion, re-point open Borrower Follow-Up requests and work items from the Lead to the newly created Opportunity. | updates Follow_Up_Request__c (Lead__c, Opportunity__c); updates Mortgage_Condition__c (Lead__c, Opportunity__c) |
| `Sales_Agent_First_Follow_Up` | after-save | on update; `Sales_Agent__c IsChanged true`, `Sales_Agent__c IsNull false` | * After-save on Lead when Sales_Agent__c is set/changed; creates an open 'First Touch' Task for the sales agent due next business day and stamps Sales_Agent_Assignment_Date__c. | sets `Sales_Agent_Assignment_Date__c`; creates `Task`; apex NextBusinessDay |
| `Send_data_to_Opp_when_Lead_is_converted` | after-save | on update; `ConvertedOpportunityId IsChanged true` | v5: also carries DoNotCall, HasOptedOutOfEmail, SMS opt-out and Website from the Lead to the Opportunity at conversion. Replaces Opt_Out_Email_flow. | updates Opportunity (Email__c, Name, Phone__c, DoNotCall__c, HasOptedOutOfEmail__c, tdc_tsw__SMS_Opt_out__c, website__c, RecordTypeId); creates `OpportunityTeamMember` |
| `SiMo_BPO_Lead_Convert_Sync` | after-save | on update; `ConvertedOpportunityId IsChanged true` | When a SiMo BPO Lead is converted, stamp the resulting Opportunity with the SiMo BPO record type (so it stays in the SimoSolutions Customer.io sync) and carry the Lead Title (Realtor / Loan Officer origin marker) into Opportunity.Title__c. | updates Opportunity (RecordTypeId, Title__c) |
| `Social_Media_Leads_Alerts_and_Updates` | after-save | on create/update | * After-save on Lead; emails a new-Facebook-lead alert when campaign becomes 'bullmortgage_leadgen', and sets Referred_By__c to a fixed Contact when campaign becomes 'monica_manosalva_jcgr'. ⚠️ §7 | sets `Referred_By__c`; email |
| `Update_field_lead_importance` | after-save | on update | * After-save on every Lead update; sets Lead_Importance__c to Low for RecordTypeId 012Kb000000RpDAIA0 Leads Discarded for Lack of Income or Unqualified Contact Information when importance is blank. | sets `Lead_Importance__c` |
| `Update_Realtor_Last_Referral_Date_From_Lead` | after-save | on create/update; formula `NOT(ISBLANK({!$Record.Referred_By__c})) && NOT(ISBLANK({!$Record.Referred_Date__c})) && {!$Record.RecordTypeId} = "012Kb000000RpDAIA0" && (…` | Whenever a Borrower Lead is created or updated with Referred_By__c and Referred_Date__c set (and on update, either field changed), this flow updates the related Contact (Realtor)'s Last_Referral_Date__c — but only if the new date is later than the current val… | updates Contact (Last_Referral_Date__c) |
| `Update_Realtor_Opp_to_Negotiation_on_Referral` | after-save | on create/update; `Referred_By__c IsNull false`, `RecordTypeId EqualTo 012Kb000000RpDAIA0`; _only when criteria become newly true_ | When a Lead’s Referred_By__c (lookup to a Realtor Contact with an active Opportunity) is populated, find that Realtor‐type Opportunity and change its Stage to “Negotiation.” | updates Opportunity (StageName) |
| `branch_default_when_Lead_create` | before-save | on create/update; `OwnerId IsChanged true`, `Branch__c EqualTo` (any) | * Before a Lead is saved with a changed owner or blank Branch__c, sets Branch__c to a branch code chosen by matching the owner's email against a hard-coded list. ⚠️ §7 | sets `Branch__c` |
| `LaHaus_Note_History_Lead` | before-save | on create/update; formula `AND( NOT(ISBLANK({!$Record.LaHaus_Last_Note__c})), OR( ISNEW(), ISCHANGED({!$Record.LaHaus_Last_Note__c}) ) )` | When La Haus AIA writes LaHaus_Last_Note__c, prepend it with a timestamp to LaHaus_Note_History__c (newest on top). Before-save, no DML. v3: also fires on create (ISNEW), not only on change. | sets `LaHaus_Note_History__c` |
| `Last_Action_Date_with_Last_Mod_Date_Leads` | before-save | on create/update | * Before any Lead is created or updated by a non-admin user, sets Last_Action_Date__c to today. | sets `Last_Action_Date__c` |
| `Opt_In_Off` | before-save | on create/update; formula `OR( AND( {!$Record.tdc_tsw__SMS_Opt_out__c}, OR( ISNEW(), ISCHANGED({!$Record.tdc_tsw__SMS_Opt_out__c}) ) ), AND( {!$Record.SMS_Opt_In__c},…` | SMS opt-in and opt-out are mutually exclusive. v5: also runs on create (ISNEW), and opt-out wins when a record is born with both flags true. | sets `tdc_tsw__SMS_Opt_out__c`, `SMS_Opt_In__c` |
| `Recruitment_Rule_Validation` | before-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDDIA0` | * Before-save on Leads of RecordTypeId 012Kb000000RpDDIA0 (create/update); blocks the save unless Recruitment Role matches NPPM (checked: Realtor-BD/Realtor-NPPM; unchecked: blank/Realtor). | — |
| `Search_lead_discarded_Don_t_want_to_be_contacted` | before-save | on create | * Before-save on Lead create; blocks the new Lead with an error if a Discarded Lead with reason 'Don't want to be contacted' exists in the same branch with the same email or phone. | — |
| `Set_Has_AI_Followup_Request` | before-save | on create/update | * Before-save on every Lead create/update; sets Has_AI_Followup_Request__c true when AI_Followup_Request__c is filled, otherwise false. | sets `Has_AI_Followup_Request__c` |
| `Set_Lead_Importance` | before-save | on create/update; `LeadSource EqualTo Facebook`, `RecordTypeId EqualTo 012Kb000000RpDAIA0`, `Income__c GreaterThan 70000.0`, `Lead_Importance__c EqualTo Low`, `Lead_Importance__c IsNull true` [1 AND 2 AND  3 AND( 4 OR 5)]; _only when criteria become newly true_ | * Before-save on Facebook-sourced Leads of RecordTypeId 012Kb000000RpDAIA0 with Income over 70,000 and Lead Importance blank or Low; raises Lead_Importance__c to Medium. | sets `Lead_Importance__c` |
| `Set_Needs_Agent_Date_Lead` | before-save | on update; `Needs_Agent__c IsChanged true` | Maintains Needs_Agent_Date__c as a waiting-since stamp on Lead. Writes the timestamp only when Needs Agent goes true AND the date is blank, so repeat escalations do not reset the clock. Clears the date when Needs Agent goes false. Before-save, so no extra DML… | sets `Needs_Agent_Date__c` |
| `Set_NPPM_From_Referral_Chain_Lead` | before-save | on create/update; formula `AND( {!$Record.RecordTypeId} = "012Kb000000RpDAIA0", NOT(ISBLANK({!$Record.Referred_By__c})), OR( ISNEW(), ISCHANGED({!$Record.Referred_By_…` | Borrower LEAD twin of Set_NPPM_From_Referral_Chain (Opportunity). Derives NPPM_Realtor__c, Referred_By_NPPM__c and Strategy__c from the referral chain using record Ids only. Handles BOTH shapes: 1-HOP (the Referred_By contact IS an NPPM - checked FIRST, becau… | sets `NPPM_Realtor__c`, `Referred_By_NPPM__c`, `Strategy__c` |
| `Update_change_owner_date` | before-save | on create/update; `OwnerId IsChanged true`, `change_owner_date__c IsNull true` (any) | * Before-save on Lead when the owner changes or change_owner_date__c is blank; stamps change_owner_date__c with the current datetime. | sets `change_owner_date__c` |
| `Update_Lead_Names_From_LastName` | before-save | on create/update; formula `AND( ISPICKVAL({!$Record.LeadSource}, "Facebook"), {!$Record.RecordTypeId} = "012Kb000000RpDAIA0", ISBLANK({!$Record.FirstName}), FIND(" ",…`; _only when criteria become newly true_ | Automatically updates the First Name and Last Name fields of a Lead when the First Name is blank and the Lead Source is 'Facebook'. This Flow separates the first word from the Last Name field to populate the First Name field, leaving the remaining part in the… | sets `FirstName`, `LastName` |
| `Update_Lead_Sourc_only_for_Business_Developers` | before-save | on create/update; `Title_Owner__c EqualTo Business Developer`; _only when criteria become newly true_ | Lead Borrower: Referral Lead Realtor: Outbound Calling | sets `LeadSource` |
| `Update_Lead_Status_to_Working_on_Note_Change` | before-save | on create/update; `Status EqualTo New`, `Notes__c IsChanged true` | Update Lead Status to Working on Note Change | sets `Lead_Importance__c`, `Status` |
| `Update_Referred_Date` | before-save | on create/update; formula `NOT(ISBLANK({!$Record.Referred_By__c})) \|\| ISCHANGED({!$Record.Referred_By__c})` | Stamp Referred Date when Referred By is added to a Lead without a date, and clear Referred Date when Referred By is removed. If an automation/import provides both Referred By and Referred Date together, the explicit date is preserved (the flow leaves it alone… | sets `Referred_Date__c` |
| `Update_Strategy_Field` | before-save | on create/update; `RecordTypeId EqualTo 012Kb000000RpDAIA0` | Sets Lead.Strategy__c on Borrower leads. NPPM if "Was this referred by an NPPM?" = Yes, or the owner is a Realtor-NPPM/Realtor-BD. Otherwise B2B Strategy (default). Reworked 2026-07-17 to drive NPPM off the Referred_By_NPPM__c field instead of the Referred By… | sets `Strategy__c` |
| `Update_the_on_off_field_based_on_the_lead_source_field` | before-save | on create/update; `LeadSource IsChanged true` | There are two options: Online or offline. | sets `ON_OFF__c` |

### 3.3 Task (12)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Assign_Every_task_to_a_Lead_or_Opp` | after-save | on create/update; `WhoId StartsWith 00Q`, `WhatId StartsWith 006`, `Subtype__c EqualTo Call`, `RecordType_related__c IsNull true`, `Branch__c IsNull true` [3 and ( 4 or 5 or not (1 or 2) )] | * When a Call task is saved without a related record type or branch (or not linked to a Lead/Opportunity), finds the Lead or open Opportunity (by Id or by the phone number at the end of the subject) and sets WhoId/WhatId, Branch__c and Recor… ⚠️ §7 | sets `Branch__c`, `RecordType_related__c`, `WhatId`, `WhoId` |
| `Assign_subtype_to_tasks` | after-save | on create/update; `Subtype__c EqualTo`, `Subtype__c EqualTo Task Other` (any) | * When a Task is saved with a blank or 'Task Other' Subtype__c, sets Subtype__c (SMS, Call, Email Sent/Failed/Opened/Link Clicked/Marked as Spam/Unsubscribed, Meeting or Task Other) from the subject text and standard TaskSubtype. | sets `Subtype__c` |
| `Assignment_of_tasks_without_record` | after-save | on create/update; `WhoId IsNull true`, `WhatId IsNull true`; _only when criteria become newly true_; scheduled paths: `AsyncAfterCommit:` | * When a Task is created or updated with neither WhoId nor WhatId, asynchronously sends the Task Id to the external service AssignmentRecord.ValidationTask so it can be linked to a record. | externalService AssignmentRecord.ValidationTask |
| `First_Touch_with_Tasks` | after-save | on create; `WhatId StartsWith 006`, `WhoId StartsWith 00Q` (any) | * When a non-admin user creates a Task on a Lead or Opportunity, sets Last_Action_Date__c to today on that Lead or Opportunity. ⚠️ §7 | updates Lead (Last_Action_Date__c); updates Opportunity (Last_Action_Date__c) |
| `Notify_Task_EmailOpened_Status` | after-save | on create; `WhoId IsNull false`, `WhoId StartsWith 00Q` | It helps keep the broker’s communication preferences up to date. | updates Lead (HasOptedOutOfEmail) |
| `Opt_In_and_Opt_Out_for_Zoom` | after-save | on create/update; `Subject Contains Messages between`, `Subtype__c EqualTo SMS`, `Description IsChanged true`; scheduled paths: `AsyncAfterCommit:` | * When an SMS Task whose subject contains 'Messages between' has its Description changed, asynchronously calls Apex TaskMessageProcessorFlow to apply opt-in/opt-out consent to the related Lead/Opportunity. ⚠️ §7 | apex TaskMessageProcessorFlow |
| `SLA_Follow_Ups` | after-save | on update; `Status IsChanged true`, `Status EqualTo Completed`, `Touch_Type__c IsNull false` | * After-save when a touch Task is marked Completed; records SLA met/missed (24h first touch, 48h follow-up) and hours missed, then for non-document tasks on unconverted Leads creates a new Follow Up Task due in 2 business days. | sets `SLA_Missed_By__c`, `SLA__c`; creates `Task`; apex NextBusinessDay; apex SalesAgentSLA_BusinessHours |
| `Update_Lead_Status_When_Task_Created` | after-save | on create; `WhoId IsNull false`, `WhoId StartsWith 00Q`, `Subject NotEqualTo Email: 6 ventajas competitivas para aprovechar el auge Latino en vivienda`, `Subject NotEqualTo Email: Las 7 herramientas de HOMESÍ que te posicionan frente al mercado latino que crece fuerte` | * After-save on new Task tied to a Lead (excluding two marketing email subjects); if the branch Lead is New and owned by the task creator, sets Lead Status to Working. | updates Lead (Status) |
| `Sync_Due_Date_for_Tasks` | before-save | on create/update; `Due_Date_Time__c IsChanged true`, `ActivityDate IsChanged true` (any) | * Before-save on Task when Due_Date_Time__c or ActivityDate changes; keeps them in sync, copying the due datetime into ActivityDate or rebuilding Due_Date_Time__c from ActivityDate plus existing or current time. | sets `Due_Date_Time__c`, `ActivityDate` |
| `SLA_Aging_5PM` | scheduled | runs Daily 17:00:00.000Z; `Status EqualTo Open`, `Touch_Type__c IsNull false`, `Assigned_Date__c IsNull false` | * Scheduled daily at 17:00 over open touch Tasks with an Assigned Date; computes business hours since assignment and sets SLA__c to an aging bucket (Under 24/24+/48+/72+ Hours), clearing SLA_Missed_By__c. ⚠️ §7 | sets `SLA_Missed_By__c`, `SLA__c`; apex SalesAgentSLA_BusinessHours |
| `SLA_Aging_9AM` | scheduled | runs Daily 09:00:00.000Z; `Status EqualTo Open`, `Touch_Type__c IsNull false`, `Assigned_Date__c IsNull false` | * Scheduled daily at 09:00 over open touch Tasks with an Assigned Date; computes business hours since assignment and sets SLA__c to an aging bucket (Under 24/24+/48+/72+ Hours), clearing SLA_Missed_By__c. ⚠️ §7 | sets `SLA_Missed_By__c`, `SLA__c`; apex SalesAgentSLA_BusinessHours |
| `SLA_Task_Aging` | scheduled | runs Daily 13:00:00.000Z; `Status EqualTo Open`, `Touch_Type__c IsNull false`, `Assigned_Date__c IsNull false` | * Scheduled daily at 13:00 over open touch Tasks with an Assigned Date; computes business hours since assignment and sets SLA__c to an aging bucket (Under 24/24+/48+/72+ Hours), clearing SLA_Missed_By__c. ⚠️ §7 | sets `SLA_Missed_By__c`, `SLA__c`; apex SalesAgentSLA_BusinessHours |

### 3.4 Mortgage_Condition__c (3)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Resume_FUR_On_WorkItem_Complete` | after-save | on update; `Is_Complete__c EqualTo true`, `Follow_Up_Request__c IsNull false`, `Name StartsWith AI Follow-Up`; _only when criteria become newly true_ | When an AI Follow-Up work item is completed, resume the linked Borrower Follow-Up: advance one cadence step, set Next Touch to +1 business day, clear the escalation, and unflag Needs Agent on the parent record. | updates Lead (Needs_Agent__c); updates Opportunity (Needs_Agent__c); updates Follow_Up_Request__c (Cadence_Step__c, Escalation_Reason__c, Next_Touch_At__c, Status__c) |
| `Set_LOA_Work_Item_Agent_Role` | before-save | on create; `Opportunity__c IsNull false` | Before-save flow on Mortgage_Condition__c (LOA Work Item). On CREATE, stamps Agent_Role__c based on the parent Opportunity's Current Status: Ratified => LOA2, otherwise => LOA1. Excludes the automated LOA2 milestone record type (those are always LOA2). Added… | sets `Agent_Role__c` |
| `Sync_Mortgage_Condition_Completion` | before-save | on create/update | Before-save flow that keeps Is_Complete__c in sync with Status__c on Mortgage_Condition__c (LOA Work Item), stamps Completed_Date__c the first time an item reaches a completed status, and copies manual Name edits (e.g. report inline editing) back to Condition… | sets `Notes__c`, `Is_Complete__c`, `Completed_Date__c`, `Condition_Name_LTA__c` |

### 3.5 OpportunityTeamMember (4)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Notify_New_LOA_Assignment` | after-save | on create/update; `LOA_Assignment_Date__c IsNull true`, `TeamMemberRole EqualTo LOA`; _only when criteria become newly true_ | This flow sends an email and creates a follow-up task when a new LOA is added to an opportunity team. | sets `LOA_Assignment_Date__c`; creates `Task`; email |
| `Update_team_member_users_create_update` | after-save | on create/update | * After-save on OpportunityTeamMember create/update; clears and rebuilds the parent Opportunity's Opportunity_Team__c rich-text list of team member names and roles. | updates Opportunity (Opportunity_Team__c) ×2 |
| `Notify_Removal_from_Opportunity_Team` | before-delete | on delete; `TeamMemberRole EqualTo LOA` | * Before an LOA-role Opportunity Team member whose User Division contains 'Support on Demand' is removed, deletes their Tasks on that Opportunity with 'Loan' in the subject and emails them a removal notice. ⚠️ §7 | deletes `Task[]`; email |
| `Update_team_member_users_delete` | before-delete | on delete | * Before an Opportunity Team Member is deleted, rebuilds the parent Opportunity's Opportunity_Team__c text from the remaining members (clears it when none remain). ⚠️ §7 | updates Opportunity (Opportunity_Team__c) ×2 |

### 3.6 OpportunityContactRole (2)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Assign_record_type_Opp_related_to_contactRole` | after-save | on create; scheduled paths: `AsyncAfterCommit:` | * When an OpportunityContactRole is created, asynchronously appends the Opportunity's record type (Realtor, Loan Officer or Broker) to the Contact's RecordTypes_related__c multi-select. ⚠️ §7 | updates Contact (RecordTypes_related__c) ×6 |
| `OldData_contact_Role` | scheduled | runs Once 12:37:00.000Z | * One-time scheduled batch (2025-04-14) over OpportunityContactRole that appends Realtor, Loan Officer or Broker to the related Contact's RecordTypes_related__c based on the Opportunity record type. ⚠️ §7 | updates Contact (RecordTypes_related__c) ×3 |

### 3.7 FeedItem (3)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Chatter_to_Contacted_Flow` | after-save | on create/update | * When a Chatter post on a Lead or Opportunity is created or edited and its body contains a keyword (credit, tax, itin, trabajo, etc.), sets Contacted__c = true on that Lead or Opportunity. ⚠️ §7 | updates Lead (Contacted__c); updates Opportunity (Contacted__c) |
| `First_Touch_with_Chatter` | after-save | on create; `ParentId StartsWith 006`, `ParentId StartsWith 00Q`, `ParentId StartsWith 00T` (any) | * When a Chatter post is created on an Opportunity, Lead or Task: for an open 'Document Follow Up' task it moves the due date 2 business days out and sets Touch Type = Follow Up; otherwise it completes the poster's oldest open touch task on… | updates Task (ActivityDate, Due_Date_Time__c, Touch_Type__c); updates Task (Status); apex NextBusinessDay |
| `Last_Action_with_Chatter` | after-save | on create; `ParentId StartsWith 006`, `ParentId StartsWith 00Q` (any) | * When a Chatter post is created on an Opportunity or Lead by a non-admin user, stamps today's date into that record's Last_Action_Date__c. | updates Lead (Last_Action_Date__c); updates Opportunity (Last_Action_Date__c) |

### 3.8 tdc_tsw__Message__c (2)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Send_notification_sms_360` | after-save | on create; `Name EqualTo Incoming`, `tdc_tsw__Related_Object__c NotEqualTo tdc_tsw__Group_Chat__c` | * After-save on each new incoming SMS 360 message (tdc_tsw__Message__c, non-group-chat); sends a 'New message' bell notification to the related Lead owner (plus co-owner) or Opportunity owner. ⚠️ §7 | notification |
| `Sync_Latest_SMS_On_Lead_Opportunity` | after-save | on create; `tdc_tsw__Related_Object_Id__c IsNull false`, `tdc_tsw__Related_Object_Id__c StartsWith 00Q`, `tdc_tsw__Related_Object_Id__c StartsWith 006` [1 AND ( 2 OR 3 )] | 360 Automation Team - Updates the latest SMS (incoming or outgoing) on both Lead and Opportunity. | sets `tdc_tsw__Lead__c`, `tdc_tsw__Opportunity__c`, `tdc_tsw__Related_Object_Id__c`, `tdc_tsw__Related_Object__c`, `OwnerId`; updates Task (Description) ×4; updates Lead (Lead_Importance__c, Latest_Message__c, Last_activity_sms_app__c); updates Opportunity (Latest_Message__c, Last_activity_sms_app__c); creates `Task` ×4 |

### 3.9 Follow_Up_Request__c (1)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Clear_Next_Touch_On_FUR_Stop` | before-save | on create/update; formula `AND( NOT(ISBLANK({!$Record.Next_Touch_At__c})), OR( TEXT({!$Record.Status__c}) = "Cancelled", TEXT({!$Record.Status__c}) = "Completed", TEX…` | Enforces the invariant: if a Borrower Follow-Up is not in a sendable status, Next Touch At must be blank. Before-save, so a human setting Status to Cancelled (or any non-sendable status) automatically drops it out of the cadence with no second step. | sets `Next_Touch_At__c` |

### 3.10 Event (1)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Last_Action_with_Event` | after-save | on create; `WhatId StartsWith 006`, `WhoId StartsWith 00Q` (any) | * When a calendar Event is created against an Opportunity (WhatId) or Lead (WhoId) by a non-admin user, stamps today's date into that record's Last_Action_Date__c. ⚠️ §7 | updates Lead (Last_Action_Date__c); updates Opportunity (Last_Action_Date__c) |

### 3.11 Contact (1)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `clear_recordType_related` | scheduled | runs Once 12:24:00.000Z | * Scheduled flow that ran once on 2025-04-14 and blanked RecordTypes_related__c on every Contact. ⚠️ §7 | sets `RecordTypes_related__c` |

### 3.12 No object (3)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Discarded_Lead_Follow_Up_Automation` | scheduled | runs Daily 08:00:00.000Z | This flow triggers when a Lead is marked as 'Discarded' due to being 'Unresponsive'. After 90 days, it automatically creates a follow-up Task, sends a reminder email to the Lead, and updates the Lead's status back to 'New'. Include a Decision to have the Flow… | updates User (Daily_Reactivated_Leads__c) ×2; updates Lead[]; creates `Task[]`; email |
| `Review_when_someone_opening_an_email` | scheduled | runs Daily 16:00:00.000Z | Only Leads | updates EmailMessage[]; notification |
| `Review_when_someone_Opening_an_Email_Opp` | scheduled | runs Daily 15:00:00.000Z | Only Opportunities | updates EmailMessage[]; notification |

### 3.13 Screen flows (12)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Add_Conditions_from_List` | Flow | — | Allows LOAs to paste a multi-line list of mortgage conditions. Each line becomes one Mortgage_Condition__c on the Opportunity. Bullet points, numbers, and dashes are stripped automatically. | apex ConditionListParser; 3 screen(s) |
| `Add_Work_Items` | Flow | — | Guided "New" experience for LOA Work Items. Asks whether to add a single Task or a list of Mortgage Conditions; an Opportunity is mandatory for both (no orphan items). Task path creates one condition-record-type work item owned by the running user. Conditions… | creates `Mortgage_Condition__c`; 5 screen(s) |
| `Batch_Assign_Lead_Role` | Flow | — | * Screen flow launched from a Lead list view (admins or users with the Batch_Assign_Lead_Role permission) that sets Sales Agent, Co-Owner, Owner, Loan Officer, Referred By (plus date) or NPPM Realtor on up to 200 selected Leads, running in s… | updates Lead[]; 5 screen(s) |
| `change_owner_Opps` | Flow | — | * Screen flow that takes a list of selected Opportunity Ids, lets the user pick an active User, and sets that user as OwnerId on all of them. | updates Opportunity[]; 2 screen(s) |
| `change_stage_Opps` | Flow | — | * Screen flow that takes a list of selected Opportunity Ids, lets the user pick an Opportunity stage, and sets that StageName on all of them. | updates Opportunity[]; 2 screen(s) |
| `Create_Borrower_Lead_from_Realtor_Opportunity` | Flow | — | * Screen flow on an Opportunity that collects a borrower's name, 10-digit phone and email, then creates a Borrower Lead (source Referral) with the Opportunity's owner and branch, referred by its primary contact role. | creates `Lead`; 3 screen(s) |
| `Create_Lead_from_Opportunity` | Flow | — | * Screen flow on a Closed Lost Opportunity that, after confirmation and an email duplicate check, creates a Recruitment-branch Lead (hard-coded record type Id) copying name, contact, NMLS, PPS and productivity-link data. | creates `Lead` ×2; 7 screen(s) |
| `Generate_Checklist_from_Template` | Flow | — | Generates Mortgage Condition checklist items on a Borrower Opportunity from a selected template. | creates `Mortgage_Condition__c[]`; 3 screen(s) |
| `Get_Realtor_Insights` | Flow | — | * Screen flow (label 'Get Agent Insights') on a Lead that, after the user confirms, sets AI_Trigger__c = true to start AI research on that agent. | updates Lead (AI_Trigger__c); 1 screen(s) |
| `Mass_Update_Lead_Co_Owner` | Flow | — | Allows users to select multiple Leads, choose a new Co-Owner, confirm, and update all selected records in bulk. | updates Lead[]; 3 screen(s) |
| `Prequalification_Form` | Flow | — | * Bilingual screen flow where staff capture a borrower prequalification; it creates or updates the Borrower Lead (matched by email or phone), writes the required-documents list, and creates a 'Collect documents' Mortgage_Condition__c work it… | updates Lead (Prequal_Required_Documents__c, CoBorrower_Required_Documents__c, Branch__c, RecordTypeId, Company, LeadSource, CoBorrower_ID_Type__c, FirstName, LastName, Phone, Email, PostalCode, Citizenship__c, Is_Employment_Authorization_Card_current__c, Property_Use__c, Marital_Status__c, Credit_Score__c, Prequal_Savings__c, Purchase_Price__c, Prequal_Occupation__c, Prequal_Employment_Type__c, Prequal_Pay_Type__c, Prequal_Pay_Frequency__c, Prequal_Income_Range__c, Prequal_Time_With_Employer__c, Prequal_Time_Self_Employed__c, Prequal_Tax_Years_Filed__c, Prequal_IRS_Payment_Plan__c, Prequal_IRS_Payment_Amount__c, Prequal_Housing_Status__c, Prequal_Housing_Other__c, Rent__c, Prequal_Time_Renting__c, Rent_payment_method__c, Prequal_Rent_Method_Other__c, Prequal_Rent_Paid_To__c, Prequal_Rent_Paid_To_Other__c, Prequal_Mortgage_Amount__c, CoBorrower_FirstName__c, CoBorrower_LastName__c, CoBorrower_Phone__c, CoBorrower_Email__c, CoBorrower_DOB__c, CoBorrower_Marital_Status__c, CoBorrower_SSN_ITIN__c, CoBorrower_Occupation__c, CoBorrower_Employment_Type__c, CoBorrower_Pay_Type__c, CoBorrower_Income__c, CoBorrower_Time_Employed__c, CoBorrower_Credit_Score__c, Prequal_Docs_Expected_Date__c, Prequal_Best_Day_To_Contact__c, Prequal_Best_Time_To_Contact__c, Notes__c, Id) ×2; creates `Mortgage_Condition__c`; creates `Lead`; 9 screen(s) |
| `Send_email_to_multiple_Opp` | Flow | — | Send email to multiple Opps using Email Template. Skips opportunities with no primary contact and any send that faults, counts them, and reports sent + skipped at the end (hardened 2026-07-10 to stop the unhandled-fault error when a selected opp has no Opport… | email; 2 screen(s) |

### 3.14 Autolaunched (called by other automation) (1)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `Update_Referred_Info_on_Leads` | AutoLaunchedFlow | — | Populates the Referred_Info__c field with the referring User’s name and the Opportunity stage. | updates Lead[] |

### 3.15 Surveys (2)

| Flow | Timing | Fires when | What it does | Effects |
|---|---|---|---|---|
| `customer_satisfaction` | Survey | — | * Salesforce Survey asking customers to rate the service from 1 (Bad) to 5 (Good) and leave optional comments; it changes no records itself. | 1 screen(s) |
| `net_promoter_score` | Survey | — | * Salesforce Survey that asks a 0-10 'how likely are you to recommend us' NPS question plus an optional free-text comment; it changes no records itself. | 1 screen(s) |

---

## 4. Rules

### 4.1 Validation rules (29)

Most rules honour `Bypass_Validation_Rules__c` and exclude the Automated Process user and the
integration user. Formulas are shown as stored (truncated at 300 characters).

#### 4.1.1 Event (1 active / 1)

| Rule | Active | Blocks the save when | Error shown |
|---|---|---|---|
| `Allowed_Values_subtype_for_event` | yes | `NOT( OR( ISPICKVAL(Subtype__c, "Meeting"), ISPICKVAL(Subtype__c, "Task Reminder"), ISPICKVAL(Subtype__c, "Visited") ) )` | Only the values 'Meeting', 'Task Reminder' or 'Visited' are allowed for events. _(on Subtype__c)_ |

#### 4.1.2 Lead (12 active / 15)

| Rule | Active | Blocks the save when | Error shown |
|---|---|---|---|
| `Block_Ineligible_Referred_By_Lead` | yes | `AND( OR( ISNEW(), ISCHANGED( Referred_By__c ) ), OR( CASESAFEID(Referred_By__c) = CASESAFEID("003Qg00000mxBDoIAM"), CASESAFEID(Referred_By__c) = CASESAFEID("003Kb00001XmUWpIAN"), CASESAFEID(Referred_By__c) = CASESAFEID("003Kb00001XmT8XIAV") ) )` | This contact can't be selected in Referred By. _(on Referred_By__c)_ |
| `branch_mandatory_validation_rule` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', ISPICKVAL(Branch__c, ""), OR( ISCHANGED(Branch__c), AND( ISCHANGED(Status), OR( ISPICKVAL(Status, "Discarded"), ISPICKVAL(Status, "On-hold"), ISPICKVAL(Status, "Working"), ISPICKVAL(Status, "Qualified") ) ) ) )` | You must select a branch before changing this lead's status or clearing the Branch field. _(on Branch__c)_ |
| `Check_Field_Lead_Importance_Borrower` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', RecordType.Name = "Borrower", OR( ISPICKVAL(Status, "Discarded"), ISPICKVAL(Status, "On-hold"), ISPICKVAL(Status, "Working") ), ISBLANK(TEXT(Lead_Importance__c )) )` | Lead Importance is a required field for Borrower record type _(on Lead_Importance__c)_ |
| `Check_Fields_For_Qualified_Borrower` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', ISPICKVAL(Status, "Qualified"), RecordType.Name = "Borrower", OR( AND( ISBLANK(TEXT(Income__c)), ISBLANK(TEXT(Prequal_Income_Range__c)) ), ISBLANK(TEXT(Debts__c)), AND( ISPICKVAL(Prequal_Housing_Status__c, "Renting"), ISBL…` | Loan Officer, Income, Debts, and Rent are required fields for Qualified Borrower record type |
| `Check_Fields_For_Qualified_Broker` | yes | `AND( RecordType.Name = "Broker", ISPICKVAL(Status, "Qualified"), NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', OR( ISBLANK(NMLS_Company__c), ISPICKVAL(Position_Recruitment__c, "") ) )` | Lead conversion blocked. Please ensure that both the NMLS Company and Position fields are completed. |
| `Check_Fields_For_Qualified_Loan_Officer` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', ISPICKVAL(Status, "Qualified"), RecordType.Name = "Loan Officer", OR( ISPICKVAL( State__c ,""), ISBLANK( City__c ) ) )` | State and City are required for Qualified Loan Officer record type. |
| `Check_Fields_For_Qualified_Realtor` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', $User.Title <> "Loan Officer", ISPICKVAL(Status, "Qualified"), RecordType.Name = "Realtor", OR( ISPICKVAL( State__c , ""), ISBLANK( Company ) ), IF( NOT(ISPICKVAL(LeadSource, "MMI")), OR( ISBLANK( Productivity_Link_FKA_MMI…` | For a Qualified Realtor record, the State field is required. If the Lead Source is not 'MMI', then the fields 'Productivity Link (FKA MMI Link)', 'PPS', 'BS So… |
| `LeadSource_Required_Borrower` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> "Automated Process", RecordType.Name = "Borrower", ISPICKVAL(LeadSource, "") )` | Lead Source is required. _(on LeadSource)_ |
| `NPPM_Required_When_Referred_By_NPPM` | yes | `AND( RecordType.DeveloperName = 'Borrower', ISPICKVAL(Referred_By_NPPM__c, 'Yes'), ISBLANK(NPPM_Realtor__c), NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', $User.Username <> 'sfintegrations@citylendinginc.com' )` | Since this was referred by an NPPM, please select the NPPM before saving. _(on NPPM_Realtor__c)_ |
| `Prevent_Status_Update_for_Duplicate_Lead` | yes | `AND( ISPICKVAL(Reasons_for_discarding__c, "Duplicate Lead"), $Profile.Name = "Agent", OR( ISPICKVAL(Status, "New"), ISPICKVAL(Status, "Working"), ISPICKVAL(Status, "On Hold") ) )` | You cannot change the status to New, Working, or On Hold for a Lead marked as a duplicate. Please contact your supervisor or admin. |
| `Reason_for_Discarded` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', ISPICKVAL(Status, 'Discarded'), ISBLANK(TEXT( Reasons_for_discarding__c )) )` | Please select a reason for discarding the lead _(on Reasons_for_discarding__c)_ |
| `Referred_By_Required_For_BD_Borrower` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> "Automated Process", RecordType.Name = "Borrower", OR( AND( $User.Title = "Business Developer", OR( ISBLANK(Referred_By__c), ISBLANK(Referred_Date__c) ) ), AND( NOT(ISBLANK(Referred_By__c)), ISBLANK(Referred_Date__c) ) ) )` | For Borrower leads, if Referred By is set then Referred Date is required. Business Developers must populate both fields. |
| `Lead_Source_Required_Non_BD_Users` | no | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> "Automated Process", RecordType.Name = "Borrower", NOT( OR( $User.Title = "Business Developer", $User.Title = "Salesforce Developer", $User.Title = "Salesforce Administrator", $User.Title = "Marketing Team" ) ), ISPICKVAL(LeadSource, "") )` | Please select at least one value for the Lead Source field before saving. |
| `Realtor_LeadSource_OutboundCalling_Valid` | no | `AND( ISNEW(), NOT(Bypass_Validation_Rules__c), $User.Username <> "Automated Process", CONTAINS($User.Title, "Business Developer"), RecordType.DeveloperName = "Realtor", NOT(ISPICKVAL(LeadSource, "Outbound Calling")) )` | For Realtor, Lead Source must be Outbound Calling. |
| `Require_ReferredBy_B2B_for_BD` | no | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', RecordType.Name = "Borrower", $User.Title = "Business Developer", OR( ISBLANK(Referred_By__c), NOT( OR( ISPICKVAL(LeadSource, "Referral"), ISPICKVAL(LeadSource, "B2B STRATEGY") ) ) ) )` | Please select “Referral” as the Lead Source and make sure the “Referred By” field is not empty. The lead must be referred by a Realtor or Broker. |

#### 4.1.3 Mortgage_Condition__c (1 active / 1)

| Rule | Active | Blocks the save when | Error shown |
|---|---|---|---|
| `Milestone_Name_Locked` | yes | `AND( RecordType.DeveloperName = 'LOA2_Milestone_Task', NOT(ISNEW()), ISCHANGED(Name) )` | Milestone work item names are managed by automation and cannot be changed. Edit Status, Due Date, or Notes instead. |

#### 4.1.4 Opportunity (10 active / 12)

| Rule | Active | Blocks the save when | Error shown |
|---|---|---|---|
| `Block_Ineligible_Referred_By_Opp` | yes | `AND( OR( ISNEW(), ISCHANGED( Referred_By__c ) ), OR( CASESAFEID(Referred_By__c) = CASESAFEID("003Qg00000mxBDoIAM"), CASESAFEID(Referred_By__c) = CASESAFEID("003Kb00001XmUWpIAN"), CASESAFEID(Referred_By__c) = CASESAFEID("003Kb00001XmT8XIAV") ) )` | This contact can't be selected in Referred By. _(on Referred_By__c)_ |
| `Closed_Won_Automation_Only` | yes | `AND( RecordType.DeveloperName = "Borrower", OR(ISNEW(), ISCHANGED(StageName)), ISPICKVAL(StageName, "Closed Won"), NOT(Closed_Loan__c) )` | Closed Won is set automatically when the loan funds (Closed Loan = true). It can't be set manually. _(on StageName)_ |
| `File_Open_Blocks_Manual_Closed_Lost` | yes | `AND( RecordType.DeveloperName = "Borrower", OR(ISNEW(), ISCHANGED(StageName)), ISPICKVAL(StageName, "Closed Lost"), NOT(ISBLANK(File_Open_Date__c)), NOT( OR( Loan_Status__c = "Application approved but not accepted", Loan_Status__c = "Application denied", Loan_Status__c = "Application withdrawn", Lo…` | This borrower already has a loan file open in Encompass. Closed Lost is set automatically from the Encompass loan status and can't be set manually. If the loan… _(on StageName)_ |
| `Funded_Loan_Cannot_Be_Closed_Lost` | yes | `AND( RecordType.DeveloperName = "Borrower", OR(ISNEW(), ISCHANGED(StageName)), ISPICKVAL(StageName, "Closed Lost"), Closed_Loan__c )` | This loan has funded (Closed Loan = true) and can't be marked Closed Lost. _(on StageName)_ |
| `NPPM_Required_When_Referred_By_NPPM` | yes | `AND( RecordType.DeveloperName = 'Borrower', ISPICKVAL(Referred_By_NPPM__c, 'Yes'), ISBLANK(NPPM_Realtor__c), NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', $User.Username <> 'sfintegrations@citylendinginc.com' )` | Since this was referred by an NPPM, please select the NPPM before saving. _(on NPPM_Realtor__c)_ |
| `Ratified_check` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', RecordType.DeveloperName = "Borrower", ISPICKVAL(Current_Status__c, "Ratified"), ISBLANK(Application_Date__c) )` | This Current Status value is only allowed if the Loan Application is triggered. _(on Current_Status__c)_ |
| `Reason_for_loss` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', ISPICKVAL(StageName, 'Closed Lost'), ISBLANK(TEXT( Reason_for_loss__c )) )` | Please select one reason for the loss of the opportunity _(on Reason_for_loss__c)_ |
| `Referred_By_Required_For_BD_Borrower` | yes | `AND( NOT(ISNEW()), OR( ISCHANGED(Referred_By__c), ISCHANGED(Referred_Date__c) ), NOT(Bypass_Validation_Rules__c), $User.Username <> "Automated Process", RecordType.Name = "Borrower", OR( AND( $User.Title = "Business Developer", OR( ISBLANK(Referred_By__c), ISBLANK(Referred_Date__c) ) ), AND( NOT(IS…` | For Borrower opportunities, if Referred By is set then Referred Date is required. Business Developers must populate both fields. |
| `Require_LoanNumber_For_Update` | yes | `AND( NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', $User.Username <> 'sfintegrations@citylendinginc.com', RecordType.Name = "Borrower", ISBLANK(Loan__c), OR( AND( ISCHANGED(StageName), NOT( OR( ISPICKVAL(StageName, "Qualification"), ISPICKVAL(StageName, "Needs Analysis"),…` | Before changing the Opportunity Stage or Current Status, you must enter the Loan #. Please retrieve this information from Encompass to correctly link the loan… |
| `Valid_Status_Negotiation` | yes | `AND( NOT(ISPICKVAL(StageName, "Close Won")), NOT(ISPICKVAL(StageName, "Closed Lost")), NOT(Bypass_Validation_Rules__c), $User.Username <> 'Automated Process', ISPICKVAL(StageName, "Negotiation") = FALSE, OR( ISPICKVAL(Current_Status__c, "Pricing"), ISPICKVAL(Current_Status__c, "Transition"), ISPICK…` | These Current Status values are only allowed when the Stage is in Negotiation. _(on Current_Status__c)_ |
| `Prevent_Changes_Closed_Opportunity` | no | `AND( OR( ISPICKVAL(PRIORVALUE(StageName), "Closed Won"), ISPICKVAL(PRIORVALUE(StageName), "Closed Lost") ), NOT($Profile.Name = "System Administrator"), OR( ISCHANGED(StageName), ISCHANGED(Amount), ISCHANGED(OwnerId), ISCHANGED(Branch__c), ISCHANGED(LeadSource), ISCHANGED(State__c), ISCHANGED(Loan_…` | ⚠️ According to business rules, closed Opportunities cannot be modified. If you need assistance, please contact your Salesforce administrator. |
| `Stop_Stage_Reversion_IntegrationsUser` | no | `AND( ISCHANGED(StageName), $User.Username = "sfintegrations@citylendinginc.com", CASE(StageName, "Qualification", 1, "Needs Analysis", 2, "Proposal", 3, "Negotiation", 4, "Closed Won", 5, "Closed Lost", 6, 0 ) < CASE(PRIORVALUE(StageName), "Qualification", 1, "Needs Analysis", 2, "Proposal", 3, "Ne…` | Stage cannot go to a previous step |

### 4.2 Sharing rules (90)

Org-wide defaults: **Lead, Opportunity, Account = Private; Contact = Controlled by Parent.**
86 of the 88 criteria rules give **Edit** (2 give Read) to a public group per branch / team.
Almost all match on `Branch__c`; a few match on `OwnerId` (a specific user's records), one on
`Loan_Officer_Text__c` (the text mirror kept by the `SyncLoanOfficerText` trigger), one on
`Affinity_Program__c` and one on Lead `Co_Owner__c`. Adding a branch means adding a rule on
**both** Lead and Opportunity. Record access for LOA roles comes from the Apex sharing
triggers in §5, not from these rules.

| Object | Rule | Type | Access | Shared to | Records matched by |
|---|---|---|---|---|---|
| Contact | `Contact_All_Internal_Read` | owner | Edit | allInternalUsers | owned by allInternalUsers |
| Lead | `AA084` | criteria | Edit | group AA084 | `1) Branch__c equals AA084; 2) Branch__c equals 701; 3) Branch__c equals 702; 4) Branch__c equals 721 — logic 1 OR 2 OR 3 OR 4` |
| Lead | `AA089_Rosi_y_Felipe` | criteria | Edit | group AA089 | `Branch__c equals AA089` |
| Lead | `All_Branches` | criteria | Edit | group All_Branches | `Branch__c notEqual 184` |
| Lead | `B_747` | criteria | Edit | group B_747 | `Branch__c equals 747` |
| Lead | `Branch` | criteria | Edit | group MainJA | `1) Branch__c equals MainJA; 2) Branch__c equals 760 — logic 1 OR 2` |
| Lead | `Branch_710` | criteria | Edit | group Branch_710 | `Branch__c equals 710` |
| Lead | `Branch_770` | criteria | Edit | group B_770 | `Branch__c equals 770` |
| Lead | `Branch_776` | criteria | Edit | group Branch_776 | `Branch__c equals 776` |
| Lead | `Branch_AB061_Arie_Batanero` | criteria | Edit | group AB061_Arie_Batanero | `Branch__c equals AB061` |
| Lead | `Branch_AP065_Ana_Pe_a` | criteria | Edit | group AP065_Ana_Pe_a | `1) Branch__c equals AP065; 2) Branch__c equals 703 — logic 1 OR 2` |
| Lead | `Branch_AT083_Armando_Tejeda` | criteria | Edit | group AT083_Armando_Tejeda | `1) Branch__c equals AT083; 2) Branch__c equals 707 — logic 1 OR 2` |
| Lead | `Branch_DC050` | criteria | Edit | group DC050 | `1) Branch__c equals DC050; 2) Branch__c equals 716 — logic 1 OR 2` |
| Lead | `Branch_DC070_Sundee_Tomaso` | criteria | Edit | group DC070_Sundee_Tomaso | `1) Branch__c equals DC070; 2) Branch__c equals 716 — logic 1 OR 2` |
| Lead | `Branch_DE066_Denise_Case` | criteria | Edit | group DE066_Denise_Case | `1) Branch__c equals DE066; 2) Branch__c equals 718 — logic 1 OR 2` |
| Lead | `Branch_EM064_Mariano_Claudio` | criteria | Edit | group EM064_Mariano_Claudio | `1) Branch__c equals EM064; 2) Branch__c equals 724 — logic 1 OR 2` |
| Lead | `Branch_GR037_Abel_Berrocal` | criteria | Edit | group GR037_Abel_Berrocal | `1) Branch__c equals GR037; 2) Branch__c equals 728 — logic 1 OR 2` |
| Lead | `Branch_JCGR57` | criteria | Edit | group JCGR57 | `1) Branch__c equals JCGR57; 2) Branch__c equals 733 — logic 1 OR 2` |
| Lead | `Branch_JCGR81` | criteria | Edit | group JCGR81_Victoria_Zambrano | `Branch__c equals JCGR81` |
| Lead | `Branch_JV053_Jesus_Vasquez` | criteria | Edit | group JV053_Jesus_Vasquez | `Branch__c equals JV053` |
| Lead | `Branch_MainCM_Carmen_M` | criteria | Edit | group MainCM_Carmen_M | `Branch__c equals MainCM` |
| Lead | `Branch_MainER_Erick_Rivera` | criteria | Edit | group MainER_Erick_Rivera | `Branch__c equals MainER,747` |
| Lead | `Branch_Recruitment` | criteria | Edit | group Recruitment | `Branch__c equals Recruitment` |
| Lead | `Branch_RJ068_Rafael_Jubiz` | criteria | Edit | group RJ068_Rafael_Jubiz | `Branch__c equals RJ068` |
| Lead | `Brnach_MainJC_Jorge_C` | criteria | Edit | group MainJC_Jorge_C | `Branch__c equals MainJC` |
| Lead | `CC074` | criteria | Edit | group CC074 | `Branch__c equals CC074` |
| Lead | `Corporate` | criteria | Edit | group Corporate | `1) Branch__c equals Corporate; 2) Branch__c equals 716 — logic 1 OR 2` |
| Lead | `DA077` | criteria | Edit | group DA077 | `Branch__c equals DA077` |
| Lead | `DC076` | criteria | Edit | group DC076 | `Branch__c equals DC076` |
| Lead | `DO072` | criteria | Edit | group DO072 | `Branch__c equals DO072` |
| Lead | `Giancarlo_Leads` | criteria | Edit | group ListView_Giancarlo | `Co_Owner__c equals 005Qg00000QoTMPIA3` |
| Lead | `JA054_Rafael_Lugo` | criteria | Edit | group JA054_Rafael_Lugo | `Branch__c equals JA054` |
| Lead | `JCB08_Sergio_Vermejo` | criteria | Edit | group JCB08_Sergio_Vermejo | `Branch__c equals JCB08` |
| Lead | `Jose_Arango_Files` | criteria | Edit | group Jose_Arango_Files | `OwnerId equals 005Qg00000TSXLKIA5` |
| Lead | `KGFR82` | criteria | Edit | group B_741 | `1) Branch__c equals KGFR82; 2) Branch__c equals 741 — logic 1 OR 2` |
| Lead | `LOA_on_Demand` | criteria | Edit | group LOA_on_Demand | `Branch__c notEqual 184` |
| Lead | `Luis_Silva_files` | criteria | Edit | group Luis_Silva_Files | `OwnerId equals 005Qg00000TSf5xIAD` |
| Lead | `Nathan_Martinez_File` | criteria | Edit | group Nathan_Martinez_Files | `OwnerId equals 005Qg00000PIh05IAD` |
| Lead | `Nathan_Matinez_Files` | criteria | Edit | group Danna_Ferrer | `OwnerId equals 005Qg00000PIh05IAD` |
| Lead | `UA069_Andres_Ulises` | criteria | Edit | group UA069_Andres_Ulises | `Branch__c equals UA069` |
| Lead | `View_Leads_Giovanni` | criteria | Edit | group View_Leads_Giovanni | `OwnerId equals 005Kb00000B1ZE0` |
| Lead | `YA090_Yoshi_y_Adrian` | criteria | Edit | group YA090_Yoshi_y_Adrian | `Branch__c equals YA090` |
| Mortgage_Condition__c | `Danna_Work_Items_To_Group` | criteria | Edit | group Danna_Ferrer | `OwnerId equals 005Qg00000SUsfZIAT` |
| Mortgage_Condition__c | `Javier_Sees_Adriana_Romero_WI` | criteria | Read | group Javier_Penaloza | `OwnerId equals 005Qg00000Jasa1IAB` |
| Mortgage_Condition__c | `LOA_work_items_to_Team_Leads` | owner | Edit | group LOA_Team_Leads | owned by role LOA |
| Opportunity | `AA084` | criteria | Edit | group AA084 | `Branch__c equals 701,721,702,AA084` |
| Opportunity | `AA089` | criteria | Edit | group AA089 | `Branch__c equals AA089` |
| Opportunity | `All_Branches` | criteria | Edit | group All_Branches | `Branch__c notEqual 141` |
| Opportunity | `B_747` | criteria | Edit | group B_747 | `Branch__c equals 747` |
| Opportunity | `Branch_710` | criteria | Edit | group Branch_710 | `Branch__c equals 710` |
| Opportunity | `Branch_770` | criteria | Edit | group B_770 | `Branch__c equals 770` |
| Opportunity | `Branch_776` | criteria | Edit | group Branch_776 | `Branch__c equals 776` |
| Opportunity | `Branch_AB061_Arie_Batanero` | criteria | Edit | group AB061_Arie_Batanero | `Branch__c equals AB061` |
| Opportunity | `Branch_AP065_Ana_Pe_a` | criteria | Edit | group AP065_Ana_Pe_a | `Branch__c equals AP065,703` |
| Opportunity | `Branch_AT083_Armando_Tejeda` | criteria | Edit | group AT083_Armando_Tejeda | `1) Branch__c equals AT083; 2) Branch__c equals 707 — logic 1 OR 2` |
| Opportunity | `Branch_DC050` | criteria | Edit | group DC050 | `1) Branch__c equals DC050; 2) Branch__c equals 716 — logic 1 OR 2` |
| Opportunity | `Branch_DC070_Sundee_Tomaso` | criteria | Edit | group DC070_Sundee_Tomaso | `1) Branch__c equals DC070; 2) Branch__c equals 716 — logic 1 OR 2` |
| Opportunity | `Branch_DE066_Denise_Case` | criteria | Edit | group DE066_Denise_Case | `1) Branch__c equals DE066; 2) Branch__c equals 718 — logic 1 OR 2` |
| Opportunity | `Branch_EM064_Mariano_Claudio` | criteria | Edit | group EM064_Mariano_Claudio | `1) Branch__c equals EM064; 2) Branch__c equals 724 — logic 1 OR 2` |
| Opportunity | `Branch_GR037_Abel_Berrocal` | criteria | Edit | group GR037_Abel_Berrocal | `Branch__c equals GR037,728` |
| Opportunity | `Branch_JCGR57` | criteria | Edit | group JCGR57 | `Branch__c equals JCGR57,733` |
| Opportunity | `Branch_JCGR81` | criteria | Edit | group JCGR81_Victoria_Zambrano | `Branch__c equals JCGR81` |
| Opportunity | `Branch_JV053_Jesus_Vasquez` | criteria | Edit | group JV053_Jesus_Vasquez | `Branch__c equals JV053` |
| Opportunity | `Branch_MainCM_Carmen_M` | criteria | Edit | group MainCM_Carmen_M | `Branch__c equals MainCM` |
| Opportunity | `Branch_MainER_Erick_Rivera` | criteria | Edit | group MainER_Erick_Rivera | `Branch__c equals MainER,747` |
| Opportunity | `Branch_MainJA` | criteria | Edit | group MainJA | `1) Branch__c equals MainJA; 2) Branch__c equals 760 — logic 1 OR 2` |
| Opportunity | `Branch_MainJC_Jorge_C` | criteria | Edit | group MainJC_Jorge_C | `Branch__c equals MainJC` |
| Opportunity | `Branch_Recruitment` | criteria | Edit | group Recruitment | `Branch__c equals Recruitment` |
| Opportunity | `Branch_RJ068_Rafael_Jubiz` | criteria | Edit | group RJ068_Rafael_Jubiz | `Branch__c equals RJ068` |
| Opportunity | `Branch_TPO` | criteria | Edit | group TPO | `Affinity_Program__c equals True` |
| Opportunity | `CC074` | criteria | Edit | group CC074 | `Branch__c equals CC074` |
| Opportunity | `Corporate` | criteria | Edit | group Corporate | `1) Branch__c equals Corporate; 2) Branch__c equals 716 — logic 1 OR 2` |
| Opportunity | `DA077` | criteria | Edit | group DA077 | `Branch__c equals DA077` |
| Opportunity | `DC076` | criteria | Edit | group DC076 | `Branch__c equals DC076` |
| Opportunity | `DO072` | criteria | Edit | group DO072 | `Branch__c equals DO072` |
| Opportunity | `JA054_Rafael_Lugo` | criteria | Edit | group JA054_Rafael_Lugo | `Branch__c equals JA054` |
| Opportunity | `JCB08_Sergio_Vermejo` | criteria | Edit | group JCB08_Sergio_Vermejo | `Branch__c equals JCB08` |
| Opportunity | `Jose_Arango_Files` | criteria | Edit | group Jose_Arango_Files | `OwnerId equals 005Qg00000TSXLKIA5` |
| Opportunity | `KGFR82` | criteria | Edit | group B_741 | `1) Branch__c equals KGFR82; 2) Branch__c equals 741 — logic 1 OR 2` |
| Opportunity | `LOA_on_Demand` | criteria | Edit | group LOA_on_Demand | `Branch__c notEqual 141` |
| Opportunity | `Luis_Silva_files` | criteria | Edit | group Luis_Silva_Files | `OwnerId equals 005Qg00000TSf5xIAD` |
| Opportunity | `Nathan_Martinez_File` | criteria | Edit | group Danna_Ferrer | `OwnerId equals 005Qg00000PIh05IAD` |
| Opportunity | `Nathan_Martinez_Files` | criteria | Edit | group Nathan_Martinez_Files | `OwnerId equals 005Qg00000PIh05IAD` |
| Opportunity | `Opps_Where_Danna_Is_LOA1` | criteria | Edit | group Danna_Ferrer | `LOA1__c equals 005Qg00000SUsfZIAT` |
| Opportunity | `Opps_Where_Danna_Is_LOA2` | criteria | Edit | group Danna_Ferrer | `LOA2__c equals 005Qg00000SUsfZIAT` |
| Opportunity | `Production_Support_Adriana_Branches` | criteria | Edit | group Production_Support_Adriana | `Branch__c equals 777,711,716,728,733,707,703,760,710,776,Affinity,747,770,724` |
| Opportunity | `Production_Support_Nila_Branches` | criteria | Edit | group Production_Support_Nila | `Branch__c equals 760,707` |
| Opportunity | `Recruitment_Maria_T` | criteria | Read | group Maria_T_ListView | `Loan_Officer_Text__c equals Haydee Tito-Pace,Jose Arango,Luis Silva,Kelvin Flores,Adriana Szczech,Jonathan Valenzuela,Zulmarys Molina,Adriana Gonzalez` |
| Opportunity | `UA069_Andres_Ulises` | criteria | Edit | group UA069_Andres_Ulises | `Branch__c equals UA069` |
| Opportunity | `YA090_Yoshi_y_Adrian` | criteria | Edit | group YA090_Yoshi_y_Adrian | `Branch__c equals YA090` |

⚠️ `Contact.Contact_All_Internal_Read` still exists in metadata with **Edit** access (its label
says "Read"), although [`ORG_REFERENCE.md`](ORG_REFERENCE.md) records it as deleted when the
Contact OWD change was reverted. While Contact stays *Controlled by Parent* it has no effect
[Likely]; it would take effect if the Contact OWD were ever changed. See §7.

### 4.3 Duplicate and matching rules

Only `Standard_Account_Duplicate_Rule` is active. Lead duplicate handling is done in Apex
(`LeadPhoneTrigger` → `DetectDuplicateHandler`) and the flow
`not_allow_to_create_non_borrowers_leads`, not by duplicate rules (see `ORG_REFERENCE.md`).

**Duplicate rules**

| Rule | Active | On create | On edit | Matching rule |
|---|---|---|---|---|
| `Account.Standard_Account_Duplicate_Rule` | yes | Allow | Allow |  |
| `Contact.Contact_Duplicate_Rule_by_email` | no | Allow | Block |  |
| `Contact.Standard_Contact_Duplicate_Rule` | no | Allow | Allow |  |
| `Contact.Standard_Rule_for_Contacts_with_Duplicate_Leads` | no | Allow | Allow |  |
| `Lead.Standard_Lead_Duplicate_Rule` | no | Allow | Allow |  |
| `Lead.Standard_Rule_for_Leads_with_Duplicate_Contacts` | no | Allow | Allow |  |

**Matching rules**

| Object | Rule | Status | Fields (method) |
|---|---|---|---|
| Account | `NMLS_Company` | Active | NMLS_Company__c:Exact |
| Contact | `Contact_Matching_Rule_by_email` | Active | Email:Exact |
| Lead | `Email_Duplicate` | Active | Email:Exact, Branch__c:Exact |

### 4.4 Other rule types

| Type | Rules | Notes |
|---|---|---|
| Lead assignment rules | `Meta_JCGR` — **inactive**, 0 entries | Lead routing is done by flows (`branch_default_when_Lead_create`, …) |
| Auto-response rules | `Case.Sample Case Auto-Response Rule` | Salesforce sample; Case is not used |
| Escalation rules | none | |
| Workflow rules (legacy) | none | All automation is Flow or Apex |

---

## 5. Apex triggers

### 5.1 Custom (unmanaged) — 16

| Trigger | Object | Status | Events | Purpose |
|---|---|---|---|---|
| `OpportunityCoOwnerSharing` | Opportunity | Active | after insert/update | Manual shares for LOA1/LOA2/Processor Jr/Loan Processor User/Loan Officer; rebuilds on owner change |
| `OpportunityAccountExecutiveOwner` | Opportunity | Active | before insert/update | Sets Owner from `Account_Executive__c` when Affinity Program |
| `OpportunityDataQualityTrigger` | Opportunity | Active | before update | Enqueues phone validation (skips Encompass-sourced opps) |
| `SyncLoanOfficerText` | Opportunity | Active | before insert/update | Mirrors the Loan Officer name into `Loan_Officer_Text__c` (used by sharing rules) |
| `UpdateAccountOpportunitiesCountTrigger` | Opportunity | Active | after insert/update/delete | Rollup count to Account |
| `LeadCoOwnerSharing` | Lead | Active | after insert/update | Manual shares via Co-Owner / Loan Officer |
| `LeadDataQualityTrigger` | Lead | Active | before insert/update | Enqueues 1 Queueable per lead — **>50 per transaction is fatal** on bulk loads |
| `LeadPhoneTrigger` | Lead | Active | before insert/update | Phone normalisation / dedupe |
| `LeadLatinoLikelihoodTrigger` | Lead | Active | before insert/update | Demographic scoring |
| `FormatLeadFields` | Lead | Active | before insert/update | Field formatting |
| `LeadConversionTrigger` | Lead | **Inactive** | after update | — |
| `FormatContactFields` | Contact | Active | before insert/update | Field formatting |
| `UpdateAccountEmployeeCountTrigger` | Contact | Active | after insert/update/delete | Rollup count to Account |
| `EmailMessageStubContactCreator` | EmailMessage | Active | after insert | Creates stub Contacts so inbound replies are captured |
| `PreventChatterEditDelete` | FeedItem | Active | before update/delete | Locks Chatter posts |
| `LoanOfficerUserMatch` | `Loan_Officer__c` | Active | before insert/update | Resolves `Salesforce_User__c` by email match |

The Encompass sync enters through the Apex REST class `OpportunityUpdater` (not a trigger);
see [`ORG_REFERENCE.md`](ORG_REFERENCE.md) → Encompass integration and gotcha #31.

### 5.2 Managed packages — 33

- **`tdc_tsw` (360 SMS)** — 22 triggers incl. `OpportunityTrigger`, `LeadTrigger`, `ContactTrigger`, `AccountTrigger`, `CaseTrigger`, `userDeactivationTrigger`
- **`ZVC` (Zoom)** — 11 triggers incl. `TaskTrigger`, `EventTrigger`, `CampaignMemberTrigger`

Managed triggers coexist with custom ones on the same object; both fire. Their code is hidden.

---

## 6. Managed-package flows (82, 59 active)

Salesforce-provided flows in namespaces such as `runtime_appointmentbooking` (16),
`standard_approvals` (9), `cms_orch` (6), `svc_itom_intelligence` (4), `sfdc_fieldservice`,
omnichannel, `sales_sfa_flows`, and one `tdc_tsw` (360 SMS) flow. They are maintained by the
package owners and are not documented here. List them with the first appendix query filtered
on `NamespacePrefix != null`.

---

## 7. Findings to review (2026-09-29)

Found while building this inventory. **Nothing was changed**; each needs a decision.

Tags: **[Verified]** re-checked directly in the prod metadata · **[Likely]** read from the prod
metadata by the inventory pass, not re-checked. Flows flagged here show ⚠️ §7 in §3.

**7.1 Save-rollback risk — email sent without a fault path (after-save)** [Verified]
A failed send rolls back the whole record save (§8.4).
- `LOA2_Notify_COC_CD`, `LOA2_Notify_COC_LE` — **their descriptions say "Send_Email has a
  faultConnector"; the active prod versions have none.** Either the fault path was lost in a
  deploy or it was never built.
- `LOA2_FHA_Docs_Email_to_Nila`, `Notify_New_LOA_Assignment`,
  `Social_Media_Leads_Alerts_and_Updates`, `Jorge_Zuzunaga_New_Lead_Facebook` (4 sends).
- Other actions without a fault path: `add_lead_to_campaign` (campaign-member create) and
  `Realtor_AI_Profile` (external callout) [Likely]. `Opt_In_and_Opt_Out_for_Zoom` has a fault
  path that swallows the error, so a consent change can be lost silently [Likely].

**7.2 Metadata that disagrees with the docs** [Verified]
- `Contact.Contact_All_Internal_Read` sharing rule still exists, with **Edit** (label says
  Read). `ORG_REFERENCE.md` says it was deleted when the Contact OWD change was reverted. It is
  dormant while Contact is Controlled by Parent [Likely]; delete it or document it on purpose.
- `Broker_Position_to_Contact_Title` (latest version = InvalidDraft) and
  `Update_team_member_users_delete` (latest version = Obsolete test that only sets
  `Title = 'test'`) have a newer, non-active version. A careless "activate latest" would break
  them.

**7.3 Logic that looks wrong**
- `Assign_Every_task_to_a_Lead_or_Opp` — a decision checks `$Record.WhoId StartsWith 006`
  (the Opportunity prefix; `WhoId` is a Lead/Contact) [Verified].
- `Assign_record_type_Opp_related_to_contact` and `…_contactRole` — the Broker and Loan Officer
  "already exists" checks test for `Realtor` (copy-paste) [Likely].
- `Send_notification_sms_360` — the co-owner check reads `Lead__r.Co_Owner__c` while the rest
  of the flow uses `tdc_tsw__Lead__r`, so co-owner routing may never fire [Likely].
- `Update_current_status_by_new_or_closed_stage` — Closed Won/Lost enter the flow but no branch
  handles them [Likely].
- `Reset_stage_by_hierarchy` — runs only when the editing user's email equals a hard-coded
  integration address, although its element labels say "No is administrator" [Likely].
- `Chatter_to_Contacted_Flow`, `Notes_Review_for_Contact_Flow`, `Opp_Keyword_Notes_Contact_Flow`
  — keyword lists contain short fragments (`ia`, `ash`, `cia`, `tax`) that match almost any text;
  the two Notes flows have no entry criteria, so they evaluate on every save.
  `No_Contacted_Reasons_for_discarding` writes the same field as `Notes_Review_for_Contact_Flow`
  [Likely].

**7.4 Hard-coded people, mailboxes and Ids** (break when someone leaves or changes role)
- `change_owner_to_duplicate_leads_no_borrowers` — new owner is user `005Kb00000B1ZEtIAN`
  (Team Marketing city) [Verified].
- `add_lead_to_campaign`, `branch_default_when_Lead_create`, `branch_default_when_Opp_create` —
  owner / branch mapping driven by hard-coded user emails; the Lead version also maps a branch
  value `ab` [Likely].
- `Social_Media_Leads_Alerts_and_Updates` — emails a hard-coded personal address and sets
  Referred By to a hard-coded Contact Id [Likely].
- `Notify_Removal_from_Opportunity_Team` — CCs two hard-coded addresses on an external
  company's domain [Likely].
- The LOA2 milestone notification flows (`LOA2_Notify_*_Milestone`, `LOA2_Task_Appraisal_POD`,
  `…_Close_On_CTC`, `…_Initial_Decision`, `…_IPR_Wait`, `…_Resubmitted_To_UW`,
  `…_Submitted_To_UW`) always add two hard-coded Production Support addresses outside test mode
  [Likely]. Test mode (`Notification_Settings__c.Test_Mode__c`) still redirects everything.
- `not_allow_to_create_non_borrowers_leads` — error links hard-code the prod domain [Likely].

**7.5 Dead or duplicated automation still active**
- `clear_recordType_related` (Contact, scheduled) and `OldData_contact_Role` (scheduled,
  2025-04-14) are one-off backfills that already ran [Likely].
- `SLA_Aging_9AM`, `SLA_Aging_5PM`, `SLA_Task_Aging` are identical except for run time and label
  [Verified] — three runs a day of the same job; confirm that is intended.

---

## 8. ⚠️ Execution-order hazards

1. **Two record-triggered flows of the same timing on one object have no guaranteed order**
   unless Trigger Order is set. `Update_Strategy_Opps` read `Referred_By_NPPM__c` before
   `Set_NPPM_From_Referral_Chain` wrote it. Fix was to write both fields in one flow.
   Opportunity has 25 before-save and 46 after-save flows.
2. **After-save recursion does not re-run before-save flows.** A correction living in a
   before-save flow cannot fix a value written by an after-save flow in the same transaction.
3. **`doesRequireRecordChangedToMeetCriteria` is not "this field changed."** It means the record
   didn't satisfy the *whole* criteria set before and does now. Combined with a filter that is
   true in a field's blank state, it fires on unrelated changes. Use explicit `IsChanged`.
4. **A failing email action in an after-save flow rolls back the record save.** Every
   `Send_Email` needs a `faultConnector`. Six active flows do not have one — see §7.
5. **Entry criteria cannot use cross-object references.** `RecordType.DeveloperName` deploys
   clean and throws at runtime. Use `RecordTypeId` + the Id. This caused a 2-day prod outage
   ([`PROD_OUTAGE_RCA_2DAY.md`](PROD_OUTAGE_RCA_2DAY.md)). No active flow uses one today.
6. **Integration writes look like automation.** The Encompass sync (`sf integrations`) rewrites
   many Opportunity fields on every upload, re-firing the flows that watch them (e.g. the LOA
   text fields → `LOA_Assignment_First_Touch`). Field history cannot tell a payload write from a
   flow write — check the sync code first (gotcha #31).

---

## Appendix — how to regenerate

All steps are read-only against prod. Work outside the repo (e.g. a temp SFDX project).

```bash
# 1. Inventory (flows incl. inactive/managed, rules, triggers)
sf data query -o prod --json -q "SELECT DurableId, ApiName, Label, ProcessType, TriggerType, RecordTriggerType, TriggerObjectOrEventLabel, IsActive, ActiveVersionId, LatestVersionId, NamespacePrefix, LastModifiedDate, LastModifiedBy FROM FlowDefinitionView ORDER BY ApiName"
sf data query -o prod --json --use-tooling-api -q "SELECT Id, ValidationName, EntityDefinitionId, Active, NamespacePrefix FROM ValidationRule"
sf data query -o prod --json --use-tooling-api -q "SELECT Name, TableEnumOrId, Status, NamespacePrefix FROM ApexTrigger ORDER BY TableEnumOrId, Name"
sf data query -o prod --json -q "SELECT DeveloperName, SobjectType, IsActive FROM DuplicateRule"
sf data query -o prod --json -q "SELECT DeveloperName, SobjectType, RuleStatus FROM MatchingRule"
sf org list metadata -o prod -m SharingCriteriaRule --json   # also SharingOwnerRule, AutoResponseRule, EscalationRule

# 2. Metadata for the active custom flows + rules
sf project retrieve start --metadata Flow:<ApiName> ... ValidationRule:<Object>.<Name> ... \
  SharingRules:Lead SharingRules:Opportunity SharingRules:Mortgage_Condition__c SharingRules:Contact \
  AssignmentRules:Lead MatchingRules:Account MatchingRules:Contact MatchingRules:Lead DuplicateRule:<Obj>.<Name> \
  --target-org prod
```

**Gotchas hit while generating:**
- A retrieve returns the flow's **latest** version, not necessarily the active one. Check every
  retrieved file for `<status>Active</status>`; for the others, read the active version with
  `SELECT Metadata FROM Flow WHERE Id = '<ActiveVersionId>'` (Tooling API, one row per query).
  On 2026-09-29 this applied to `Broker_Position_to_Contact_Title` (latest = InvalidDraft) and
  `Update_team_member_users_delete` (latest = Obsolete).
- The ValidationRule Tooling query with `EntityDefinition.QualifiedApiName` for all objects fails
  with an internal error; select `EntityDefinitionId` instead and resolve custom object Ids
  (`01I…`) through `EntityDefinition`.
- `FlowDefinitionView` does not support `COUNT()`.
