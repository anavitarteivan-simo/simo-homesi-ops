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
