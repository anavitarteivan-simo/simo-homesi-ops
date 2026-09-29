# Salesforce Automation Inventory — Simo Solutions Group / Homesi

**Org:** HomeSi (`00DKb000000OvoRMAS`) · production, alias `prod`
**Sandbox:** `homesi-staging`
**Generated:** 2026-08-25 from the live production org
**Regenerate with:** the SOQL in the appendix — do not hand-maintain this file

> This is a *descriptive* inventory: what exists and what fires it. For hard-won failure
> modes and incident history, see `CLAUDE.md`. For field definitions, see
> `02_Data_Dictionary.md`.

---

## 1. Summary

| Automation type | Count |
|---|---|
| Active record-triggered / scheduled flows | **120** |
| — on Opportunity | 68 |
| — on Lead | 35 |
| — on Task | 13 |
| — on Work Item (`Mortgage_Condition__c`) | 3 |
| — on Contact | 1 |
| Apex triggers (custom, unmanaged) | 17 |
| Apex triggers (managed packages) | 32 |
| Active validation rules — Opportunity | 9 of 11 |
| Active validation rules — Lead | 11 of 14 |

**Opportunity carries 68 active flows plus 6 Apex triggers.** Any change to Opportunity
automation should assume interaction effects. Two before-save flows on the same object have
**no guaranteed execution order** — see §6.

---

## 2. Opportunity — active flows (68)

### 2.1 LOA2 milestone work items + notifications (22)
Encompass writes a milestone date → flow emails LO + LOA2 + Loan Processor, then creates a
Work Item if an LOA2 is assigned. Full design in `CLAUDE.md` → "LOA milestone NOTIFICATION EMAILS".

| Flow | Trigger | v |
|---|---|---|
| `LOA2_Task_Issue_Disclosures` | `Application_Date__c` IsChanged | 11 |
| `LOA2_Task_Disclosures_FollowUp` | `LE_Sent_Date__c` IsChanged | 12 |
| `LOA2_Task_Order_Appraisal` | `Disclosures_Signed_Date__c` IsChanged | 11 |
| `LOA2_Task_Send_to_Processing` | `Disclosures_Signed_Date__c` IsChanged | 9 |
| `LOA2_Task_Appraisal_POD` | `Appraisal_Received_Date__c` IsChanged | 7 |
| `LOA2_Task_COC_Rate_Locked` | `Lock_Date__c` IsChanged | 7 |
| `LOA2_Task_ICD_Request` | Title Commitment + Hazard Ins + Lock Date all set | 5 |
| `LOA2_Task_IPR_Wait` | `Submitted_to_Processing_Date__c` IsChanged | 7 |
| `LOA2_Task_Submitted_To_UW` | `Submitted_to_UW_Date__c` IsChanged | 7 |
| `LOA2_Task_Initial_Decision` | `Initial_UW_Decision_Date__c` IsChanged | 7 |
| `LOA2_Task_Resubmitted_To_UW` | `Resubmitted_Date__c` IsChanged (populated) | 7 |
| `LOA2_Task_Resubmitted_To_Processing` | `Resubmitted_Date__c` IsChanged (cleared) | 5 |
| `LOA2_Task_Close_On_CTC` | `Clear_to_Close_Date__c` IsChanged | 5 |
| `LOA2_Task_Close_Appraisal_POD` | `Appraisal_Proof_of_Delivery_Date__c` | 2 |
| `LOA2_Task_Close_On_Appraisal_Ordered` | `Appraisal_Ordered_Date__c` | 5 |
| `LOA2_Task_Close_On_COC_Cleared` | Revised LE or ICD on/after Lock Date | 2 |
| `LOA2_Task_Close_On_Disclosures_Signed` | `Disclosures_Signed_Date__c` | 1 |
| `LOA2_Task_Close_On_ICD_Received` | `ICD_Date__c` | 2 |
| `LOA2_Task_Close_On_Submitted_To_Processing` | `Submitted_to_Processing_Date__c` | 2 |
| `LOA2_Notify_COC_LE` | `COC_LE_Trigger__c` IsChanged | 3 |
| `LOA2_Notify_COC_CD` | `COC_CD_Trigger__c` IsChanged | 3 |
| `LOA2_FHA_Docs_Email_to_Nila` | Disclosures signed + `Loan_Type__c` = FHA | 8 |

⚠️ `LOA2_FHA_Docs_Email_to_Nila` is **not** under Test Mode — it emails real recipients even
during notification testing.

### 2.2 Stage / Current Status engine (10)
The most interaction-prone cluster in the org. Read `CLAUDE.md` → "Stage protection" before editing.

| Flow | Type | v |
|---|---|---|
| `Update_current_Milestone_Loan_status_Opp` | before-save | 26 |
| `Sync_Current_Status_with_Stage` | before-save | 13 |
| `Auto_Update_Stage_Based_on_CurrentStatus` | after-save | 9 |
| `Update_current_status_by_new_or_closed_stage` | after-save | 4 |
| `Clear_Current_Status_On_Manual_Close` | after-save | 2 |
| `Reset_stage_by_hierarchy` | after-save | 1 |
| `Reset_current_status_by_hierarchy_Loan_Officer_V1` | before-save | 1 |
| `Update_Ratified_date_current_status` | before-save | 3 |
| `Update_Pre_approved_date_current_status` | after-save | 1 |
| `Valid_Status_Negotiation` (VR) | — | — |

### 2.3 Assignment, sharing, ownership (5)
`LOA_Assignment_First_Touch` (v6) · `Loan_Officer_default_by_Opp` (v2) ·
`Sync_Loan_Officer_Text` (v1) · `Set_Branch_Affinity_When_Affinity_Program` (v1) ·
`branch_default_when_Opp_create` (v13)

### 2.4 NPPM / Strategy (4)
`Set_NPPM_From_Referral_Chain` (v3) · `Update_Strategy_Opps` (v3) ·
`Create_NPPM_On_Realtor_Closed_Won` (v1) · `Update_Referred_Date_Opportunity` (v4)

### 2.5 Rate lock (3)
`Lock_Rate_Locked_Email_Alert` (v4) · `Lock_Expiration_Work_Items` (v1) · `Lock_Renewal_Close_Items` (v1)

### 2.6 Work item lifecycle (3)
`Close_LOA_Work_Items_On_Opp_Close` (v1) · `Complete_LOA1_Work_Items_On_Ratified` (v1) ·
`Copy_Stat_Risk_To_Healthiness` (v1)

### 2.7 Dates, history, data hygiene (13)
`Opportunity_Stage_Date_Tracker` (v12) · `Opportunity_Stage_Date_Tracker_Create` (v7) ·
`Append_Delay_Details_History` (v1) · `Append_Prod_Support_Note_History` (v1) ·
`Last_Action_Date_with_Last_Modified_Date` (v3) · `Original_Est_Closing_Date_Update` (v1) ·
`Update_Close_Date_for_Borrower_Opportunities` (v4) · `Clean_LoanID_OnOpportunity` (v1) ·
`Prevent_Duplicate_LoanGuid_Borrower_Opportunity` (v8) · `Set_Needs_Agent_Date_Opp` (v1) ·
`Assign_record_type_Opp_related_to_contact` (v6) · `hasTaxID` (v1) · `Opt_Out_Email_flow` (v3)

### 2.8 B2B / Realtor / recruitment (8)
`Update_Realtor_Last_Referral_Date` (v2) · `Update_Realtor_Branch_From_Opportunity` (v1) ·
`Update_Invite_Date_for_Realtor_Opportunities` (v2) · `Update_Lifecycle_on_base_the_Stage_Opportunities_B2B` (v1) ·
`Require_Note_Before_Proposal_Realtor_Oportunities` (v1) · `Recruitment_Rule_Opportunity` (v2) ·
`Recruitment_Rule_Opportunity_Contact_Sync` (v1) · `Opp_Keyword_Notes_Contact_Flow` (v2)

### 2.9 Cross-object writes (2)
`Update_Contact_Phone_from_Opportunity` (v6)

---

## 3. Lead — active flows (35)

**Conversion & sync:** `Send_data_to_Opp_when_Lead_is_converted` (v4) ·
`Copy_Chatter_Posts_From_Lead_To_Opportunity` (v2) · `SiMo_BPO_Lead_Convert_Sync` (v1) ·
`Repoint_FUR_On_Lead_Convert` (v1)

**NPPM / Strategy:** `Set_NPPM_From_Referral_Chain_Lead` (v1) · `Update_Strategy_Field` (v5) ·
`Update_Referred_Date` (v8) · `Update_Realtor_Last_Referral_Date_From_Lead` (v2) ·
`Update_Realtor_Opp_to_Negotiation_on_Referral` (v2)

**Status / lifecycle:** `Lead_Status_Date_Tracker` (v1) · `Date_of_update_status_movement` (v1) ·
`Update_Lead_Status_to_Working_on_Note_Change` (v3) · `No_Contacted_Reasons_for_discarding` (v1) ·
`Search_lead_discarded_Don_t_want_to_be_contacted` (v3) · `Update_change_owner_date` (v2)

**Assignment & routing:** `Loan_Officer_default_by_lead` (v2) · `branch_default_when_Lead_create` (v39) ·
`Sales_Agent_First_Follow_Up` (v2) · `change_owner_to_duplicate_leads_no_borrowers` (v1) ·
`not_allow_to_create_non_borrowers_leads` (v2)

**Importance / scoring:** `Set_Lead_Importance` (v1) · `Update_field_lead_importance` (v4) ·
`Realtor_AI_Profile` (v2)

**Source & marketing:** `add_lead_to_campaign` (v18) · `Jorge_Zuzunaga_New_Lead_Facebook` (v14) ·
`Social_Media_Leads_Alerts_and_Updates` (v1) · `Update_Lead_Sourc_only_for_Business_Developers` (v2) ·
`Update_the_on_off_field_based_on_the_lead_source_field` (v2)

**Other:** `Last_Action_Date_with_Last_Mod_Date_Leads` (v3) · `Update_Lead_Names_From_LastName` (v1) ·
`Broker_Position_to_Contact_Title` (v1) · `Notes_Review_for_Contact_Flow` (v1) ·
`Recruitment_Rule_Validation` (v2) · `Set_Needs_Agent_Date_Lead` (v1) · `Set_Has_AI_Followup_Request` (v1)

---

## 4. Task (13) · Work Item (3) · Contact (1)

**Task — record-triggered:** `SLA_Follow_Ups` (v9) · `First_Touch_with_Tasks` (v8) ·
`Assign_Every_task_to_a_Lead_or_Opp` (v4) · `Assign_subtype_to_tasks` (v4) ·
`Assignment_of_tasks_without_record` (v1) · `Update_Lead_Status_When_Task_Created` (v5) ·
`Notify_Task_EmailOpened_Status` (v2) · `Opt_In_and_Opt_Out_for_Zoom` (v1) · `Sync_Due_Date_for_Tasks` (v1)

**Task — scheduled:** `SLA_Aging_9AM` (v2) · `SLA_Aging_5PM` (v1) · `SLA_Task_Aging` (v1)

**Work Item (`Mortgage_Condition__c`):** `Sync_Mortgage_Condition_Completion` (v5) ·
`Set_LOA_Work_Item_Agent_Role` (v2) · `Resume_FUR_On_WorkItem_Complete` (v1)

**Contact — scheduled:** `clear_recordType_related` (v1)

---

## 5. Apex triggers

### 5.1 Custom (unmanaged) — 17

| Trigger | Object | Status | Purpose |
|---|---|---|---|
| `OpportunityCoOwnerSharing` | Opportunity | Active | Manual shares for LOA1/LOA2/Processor Jr/Loan Officer; rebuilds on owner change |
| `OpportunityAccountExecutiveOwner` | Opportunity | Active | Sets Owner from `Account_Executive__c` when Affinity Program |
| `OpportunityDataQualityTrigger` | Opportunity | Active | Data quality enforcement |
| `SyncLoanOfficerText` | Opportunity | Active | Keeps LO text field in sync |
| `UpdateAccountOpportunitiesCountTrigger` | Opportunity | Active | Rollup count to Account |
| `LeadCoOwnerSharing` | Lead | Active | Manual shares via Co-Owner / Loan Officer |
| `LeadDataQualityTrigger` | Lead | Active | Enqueues 1 Queueable per lead — **>50/txn is fatal** on bulk loads |
| `LeadPhoneTrigger` | Lead | Active | Phone normalisation / dedupe |
| `LeadLatinoLikelihoodTrigger` | Lead | Active | Demographic scoring |
| `FormatLeadFields` | Lead | Active | Field formatting |
| `LeadConversionTrigger` | Lead | **Inactive** | — |
| `FormatContactFields` | Contact | Active | Field formatting |
| `UpdateAccountEmployeeCountTrigger` | Contact | Active | Rollup count to Account |
| `EmailMessageStubContactCreator` | EmailMessage | Active | Creates stub Contacts so inbound replies are captured |
| `PreventChatterEditDelete` | FeedItem | Active | Locks Chatter posts |
| `LoanOfficerUserMatch` | `Loan_Officer__c` | Active | Resolves `Salesforce_User__c` by email match |

### 5.2 Managed packages — 32
- **`tdc_tsw` (360 SMS)** — 20 triggers incl. `OpportunityTrigger`, `LeadTrigger`, `ContactTrigger`, `AccountTrigger`, `CaseTrigger`, `userDeactivationTrigger`
- **`ZVC` (Zoom)** — 12 triggers incl. `TaskTrigger`, `EventTrigger`, `CampaignMemberTrigger`

Managed triggers coexist with custom ones on the same object; both fire.

---

## 6. ⚠️ Execution-order hazards

1. **Two before-save flows on one object have no guaranteed order.** `Update_Strategy_Opps` read
   `Referred_By_NPPM__c` before `Set_NPPM_From_Referral_Chain` wrote it. Fix was to write both
   fields in one flow.
2. **After-save recursion does not re-run before-save flows.** A correction living in a
   before-save flow cannot fix a value written by an after-save flow in the same transaction.
3. **`doesRequireRecordChangedToMeetCriteria` is not "this field changed."** It means the record
   didn't satisfy the *whole* criteria set before and does now. Combined with a filter that is
   true in a field's blank state, it fires on unrelated changes. Use explicit `IsChanged`.
4. **A failing email action in an after-save flow rolls back the record save.** Every
   `Send_Email` needs a `faultConnector`.
5. **Entry criteria cannot use cross-object references.** `RecordType.DeveloperName` deploys
   clean and throws at runtime. Use `RecordTypeId` + the Id. This caused a 2-day prod outage.

Full write-ups in `CLAUDE.md`.

---

## 7. Validation rules

**Opportunity — active (9):** `Closed_Won_Automation_Only` · `Funded_Loan_Cannot_Be_Closed_Lost` ·
`File_Open_Blocks_Manual_Closed_Lost` · `Require_LoanNumber_For_Update` · `Reason_for_loss` ·
`Ratified_check` · `Valid_Status_Negotiation` · `Referred_By_Required_For_BD_Borrower` ·
`NPPM_Required_When_Referred_By_NPPM`
*Inactive:* `Prevent_Changes_Closed_Opportunity`, `Stop_Stage_Reversion_IntegrationsUser`

**Lead — active (11):** `branch_mandatory_validation_rule` · `Check_Field_Lead_Importance_Borrower` ·
`Check_Fields_For_Qualified_Borrower` · `Check_Fields_For_Qualified_Broker` ·
`Check_Fields_For_Qualified_Loan_Officer` · `Check_Fields_For_Qualified_Realtor` ·
`LeadSource_Required_Borrower` · `NPPM_Required_When_Referred_By_NPPM` ·
`Prevent_Status_Update_for_Duplicate_Lead` · `Reason_for_Discarded` ·
`Referred_By_Required_For_BD_Borrower`
*Inactive:* `Lead_Source_Required_Non_BD_Users`, `Realtor_LeadSource_OutboundCalling_Valid`,
`Require_ReferredBy_B2B_for_BD`

Most VRs honour `Bypass_Validation_Rules__c` and exclude the Automated Process user and
`sfintegrations@citylendinginc.com`.

---

## Appendix — regeneration queries

```sql
-- Active flows for one object (repeat per object)
SELECT ApiName, TriggerType, VersionNumber
FROM FlowDefinitionView
WHERE IsActive = true AND TriggerObjectOrEventLabel = 'Opportunity'
ORDER BY ApiName

-- Apex triggers (Tooling API)
SELECT Name, TableEnumOrId, Status, NamespacePrefix FROM ApexTrigger ORDER BY TableEnumOrId, Name

-- Validation rules, one object at a time (Tooling API)
SELECT ValidationName, Active FROM ValidationRule
WHERE EntityDefinition.QualifiedApiName = 'Opportunity' ORDER BY ValidationName
```

Notes: `FlowDefinitionView` does not support `COUNT()`, and querying all objects with
`Description` at once exceeds practical response limits — page by object.
