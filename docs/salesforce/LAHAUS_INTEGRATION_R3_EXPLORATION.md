# La Haus AIA integration — round 3 test results: exploration

**Exploration only. No change was made to staging or prod, and no fix is proposed here.**
Source: the SLTeam test report "Integración La Haus AIA – Salesforce, Ronda 3" (2026-09-29, sandbox
`ruby-ruby-7485--staging`, REST v62.0 and Apex REST `/services/apexrest/lahaus/convert`). Facts below
were read live on 2026-10-01 from `homesi-staging` (org `00DEm000008XXK7MAO`) and `prod`
(`00DKb000000OvoRMAS`). Tags: **[Verified]** read live · **[Likely]** inference · **[Unverified]**.

## 1. What the report says (27 scenarios)

| Result | Scenarios |
|---|---|
| ✔ works | 13 — the whole Lead path (create, find by Id / conversation / phone, first message, profile, advisor, not interested, finished, unreachable, opt-out) |
| ✘ fails | 5 — Opportunity PATCH on a converted lead, first message / unreachable / opt-out on Opportunity, appointment on an unconverted Lead (convert) |
| ◐ partial | 6 — Work Item is created, the Opportunity update fails |
| ⚠ pending | 3 — new Lead with the email of an opt-out Lead, new Lead with the email of an active Lead, profile on Opportunity |

Reported root cause for the ✘ / ◐ rows: flow `Opt_in_Off_Opp` rejects every Opportunity insert/update
with `CANNOT_EXECUTE_FLOW_TRIGGER` ("Syntax error. Missing ')'"), which also aborts lead conversion
(Apex REST 422 and native `convertLead`). The Opportunity PATCH was reported fixed on 2026-09-30.

## 2. State of the flow in staging today [Verified 2026-10-01]

| | `Opt_in_Off_Opp` (Opportunity) | `Opt_In_Off` (Lead) |
|---|---|---|
| Staging | one version (v1), **Status `Obsolete` — no active version**; last modified 2026-09-30 22:53 UTC by Melquiadez Rodriguez | one version (v1), **`Obsolete`**; last modified 2026-09-17 |
| Prod | **Active**, v2 (modified 2026-09-14) | **Active**, v5 (modified 2026-09-14) |
| Entry formula | identical to prod's active version; parentheses balance | identical to prod's active version |

- The saved formula in staging is **not** syntactically broken any more, and matches prod. What is
  different is that the flow is **inactive** in staging. [Unverified] whether "fixed" meant corrected
  and then deactivated, or deactivated only; confirm with Melquiadez.
- Consequence: the Opportunity PATCH should no longer fail in staging, but **SMS opt-in / opt-out
  mutual exclusion is not enforced in staging** (it is in prod). Opt-out results in staging will not
  predict prod until the flow is active. Not tested: no write was made.

## 3. Items that are ours (everything except the Opportunity PATCH)

### 3.1 New Lead with the email/phone of an opt-out Lead → 400 [Verified]
- Source of the error: **flow `Search_lead_discarded_Don_t_want_to_be_contacted`**, a before-save flow
  on Lead **create** that raises a custom error. It is not a validation rule; the API code is
  `FIELD_CUSTOM_VALIDATION_EXCEPTION`.
- Logic: a Discarded Lead with `Reasons_for_discarding__c = "Don't want to be contacted"` and the
  same Email **or** Phone blocks creation; the message carries that Lead's URL. It is an existing,
  intentional business rule (flow dated 2025-06).
- **Staging and prod differ.** Staging v1 does not filter by branch. **Prod v3 also requires the same
  `Branch__c`.** The test used branch 716 on both Leads, so prod would block it too [Likely].

### 3.2 Duplicate handling: does prod block creation? [Verified]
- **No.** Every Lead and Contact duplicate rule is inactive in both orgs (only
  `Standard_Account_Duplicate_Rule` is active). `DUPLICATES_DETECTED` is never returned.
- The renaming seen in the test (`…C9-(DUPLICATE)`, Discarded, `Duplicate Lead`) is Apex
  `DetectDuplicateHandler`. It is **identical in staging and prod** (23,532 characters without
  comments, last modified 2026-08-05), so prod behaves the same as staging.
- It runs when a Lead is saved, matches Leads and Opportunities by email **or** phone within the same
  branch, and discards the incoming record. Updates keyed on the new Lead's conversation id can then
  land on a Discarded record. See `CONTACT_OWNERSHIP_AND_DEDUP.md` §5.

### 3.3 Test records created in staging [Verified — all still exist]
| Object | Ids | State |
|---|---|---|
| Leads | `00QEm00000gR869MAC` (Discarded), `gR1KpMAK` (New), `gRCJRMA4` (New), `gQlCpMAK` (New), `gR6nYMAS` (Discarded, `-(DUPLICATE)`), `gRD95MAG` (New) | branch 716, created 2026-09-29 |
| Work Items on their test Lead / Leads | `a1IEm00000AknHhMAJ`, `AknKvMAJ`, `AknMXMAZ`, `AknO9MAJ` | `Not Started`, role Sales Agent, owner "Docs Lahaus" |
| **Work Items on the TypeTest Opportunity (SLTeam asked for these to be deleted)** | `a1IEm00000AknRNMAZ`, `AknUbMAJ`, `AknXpMAJ`, `AknZRMAZ` | `Not Started`, role LOA1, owner Melquiadez Rodriguez, linked to `006Em00000ol6htIAA` |
- `TypeTest Interest` (Lead `00QEm00000eSr8nMAC`, Opportunity `006Em00000ol6htIAA`) is the only
  converted test Lead and is not ours to delete.

## 4. Staging vs prod differences found
- **Apex:** `LaHausConvertLead`, `LaHausConvertLeadRest` and `LaHausConvertLeadTest` are **already
  deployed in prod** (2026-09-25, by It Support). Staging also has `LaHausSend`, `LaHausSendTest` and
  `LaHausListButtonController`; prod does not.
- **Lead fields:** staging has 25 `LaHaus_*` fields, prod 19. Missing in prod: `LaHaus_Request`,
  `LaHaus_Response`, `LaHaus_Send_to_AI`, `LaHaus_Sent`, `LaHaus_Sent_By`, `LaHaus_Sent_Date`
  (look like the outbound "send to AI" feature [Unverified]). Opportunity has 19 in both.
  `Mortgage_Condition__c` has none.
- **Flows:** `Search_lead_discarded…` v1 (staging) vs v3 (prod); `Prevent_Duplicate_LoanGuid_Borrower_Opportunity`
  v6 vs v8; `Remove_duplicates_with_15_days` is active in staging and inactive in prod.
- The behaviours above mean a green staging run is **not** proof for prod.

## 5. Observations on the report
- Annex A (`ConvertedOpportunity.Owner.Type`) needs nothing from us: a User has no `Type`, and the
  vendor's integration already uses the working query.
- `LaHausConvertLeadRest` is a thin wrapper that returns 422 with the underlying message when the
  conversion fails; the 422s in the report are the flow error surfacing through it.

## 6. `LaHausConvertLead` (read live from staging, 2026-10-01) [Verified]
- Invocable Apex (`with sharing`) behind `LaHausConvertLeadRest`. Idempotent: an already converted Lead
  returns its Opportunity with `success = true`.
- **Requires `Branch__c`** (refuses with "Branch is required" otherwise).
- **Sets `Bypass_Validation_Rules__c = true` on the Lead before converting** (SLTeam decision
  2026-09-14) so the qualification rule (Loan Officer / Income / Debts / Rent) does not block it. The
  flag **stays true** on the converted Lead as an "AI-converted" marker.
- Converts one Lead per `convertLead` call with `allOrNone = true`; a failure should carry the real
  cause, but the report's 422 shows only Salesforce's generic "There was an error converting the lead",
  which is what a flow fault surfaces as.
- Uses the first converted `LeadStatus` (falls back to `Qualified`), `doNotCreateOpportunity = false`,
  no notification email, optional owner and Opportunity name.
- Downstream `Require_LoanNumber_For_Update` (active in both orgs) blocks an Opportunity from moving
  past Needs Analysis without an Encompass loan. That likely makes the pending "LOA2 role on an
  Opportunity in Negotiation" test impossible to reach by API alone [Likely].

## 7. Integration user and permissions [Verified 2026-10-01]

| | Staging | Prod |
|---|---|---|
| User | `Docs Lahaus` `005Em00000lBm9XIAS` | `La Haus AI` `005Qg00000VHorNIAT` |
| Profile | **System Administrator**, no role, Standard user | **System Administrator**, no role, Standard user |
| Last login | 2026-09-29 | 2026-09-15 |
| Logins, last 30 days | 30 via **OAuth app "LaHaus AI" (Remote Access 2.0)** + 2 browser | 4 browser successes, 6 "Multi-factor required", 1 "Computer activation required"; **no API logins** |

- The vendor integration runs as a **System Administrator in both orgs**, so object permissions and
  profile-level restrictions do not apply to it.
- **FLS exists** for the System Administrator profile on every `LaHaus_*` field, read + edit
  [Verified via `FieldPermissions` rows]: staging Lead 25/25 and Opportunity 19/19, prod Lead 19/19 and
  Opportunity 19/19. So field access is not a cause of the failures.
- Several rules exempt administrators or the "Agent" profile, so this user skips automation meant for
  agents: e.g. `Prevent_Status_Update_for_Duplicate_Lead` (prod) applies only to `$Profile.Name = "Agent"`.
- Most prod Lead validation rules (`LeadSource_Required_Borrower`, `Referred_By_Required_For_BD_Borrower`,
  `branch_mandatory_validation_rule`, `Reason_for_Discarded`, `Check_Fields_For_Qualified_*`) are skipped when
  `Bypass_Validation_Rules__c` is true or the user is `Automated Process`. The integration sets the flag
  only inside the convert call, not on Lead create/update.
- **Prod is not live for La Haus:** 0 Leads and 0 Opportunities carry `LaHaus_Conversation_Id__c`
  (staging: 7 Leads, 0 Opportunities). 2 prod Leads have `LeadSource = 'La Haus AIA'` (staging 10);
  origin of those 2 not checked.

## 8. Validation rules that differ between orgs [Verified]
- Prod has Lead rules staging lacks: `Prevent_Status_Update_for_Duplicate_Lead`,
  `Block_Ineligible_Referred_By_Lead` (fixed list of Contact Ids), `LeadSource_Required_Borrower`,
  `Referred_By_Required_For_BD_Borrower`. Staging has `Lead_Source_Required_Non_BD_Users` and
  `Require_ReferredBy_B2B_for_BD`, which prod does not list.
- `Prevent_Changes_Closed_Opportunity` is **inactive in both orgs** (prod last modified 2025-05-14).
- `Require_LoanNumber_For_Update` is active in both.
- So lead creation and updates in prod are subject to rules never exercised in the staging runs.

- `Block_Ineligible_Referred_By_Lead` (prod) only fires when `Referred_By__c` is set or changes and
  equals one of 3 hard-coded Contact Ids; La Haus does not write `Referred_By__c`, so it is not relevant.

## 9. Active automation: staging is far from prod [Verified 2026-10-01]
Active record-triggered / scheduled flows (`FlowDefinitionView`, `IsActive = true`):

| Object | Staging | Prod | Only in staging | Only in prod | Different version |
|---|---|---|---|---|---|
| Opportunity | 51 | 71 | 7 | 27 | 37 |
| Lead | 40 | 36 | 11 | 7 | 17 |

- **`Opt_in_Off_Opp` (Opportunity) and `Opt_In_Off` (Lead) are active in prod only.** This matches §2.
- Opportunity flows only in prod include `Sync_Loan_Officer_Text`, `Sync_Current_Status_with_Stage`,
  `Update_Realtor_Branch_From_Opportunity`, `Recruitment_Rule_Opportunity_Contact_Sync` and several `LOA2_*` notify/close flows. Only in staging:
  `Require_Supreme_Loan_Number_on_Negotiation`, `Close_Loan`, `LOA1_and_LOA2_Automatic_Assignment`,
  `LOA_First_Follow_Up`, `Loan_Officer_default_by_Opp`, among others.
- Lead flows only in staging include `LaHaus_Outbound_Send` (the outbound "send to AI" feature, whose 6
  Lead fields are also missing in prod), `Detectar_Lead_Duplicado_por_Email`,
  `Remove_duplicates_with_15_days` and `Send_SMS_new_Leads`. Only in prod: `SiMo_BPO_Lead_Convert_Sync`,
  `Opt_In_Off`, `Update_Lead_Sourc_only_for_Business_Developers`, among others.
- Dozens of shared flows run different versions (e.g. `Send_data_to_Opp_when_Lead_is_converted` v4 in
  staging vs v5 in prod, `branch_default_when_Lead_create` v19 vs v39).
- Conclusion: **a green staging run is weak evidence for prod.** The two orgs run different automation
  on both objects the integration writes to.

## 10. Evidence that conversion works in prod [Verified]
- On 2026-09-14 (`It Support`) a Lead was created and converted in **prod** with Opportunity
  `ZZTEST BypassLive` (`006Qg00000qyMZDIA2`, Qualification, created 19:26:38 UTC). Prod's
  `Opt_in_Off_Opp` v2 had been modified at 16:05 UTC that day and is active, so lead conversion succeeds
  in prod with that flow active.
- **Leftover test data in prod:** that Lead (`00QQg00000nHYNdMAO`, converted, branch 716) and its
  Opportunity, plus a second unconverted Lead (`00QQg00000nHIxDMAW`, New, no branch). Both have
  `LeadSource = 'La Haus AIA'`, owner `It Support`. These are the 2 prod Leads counted in §7. Not
  deleted: needs a decision.

## 11. Write tests in `homesi-staging` (2026-10-01, by Ivan Anavitarte, System Administrator) [Verified]
Authorised explicitly by the user for staging only. Test records are prefixed `ZZEXPL`; none touches
SLTeam's own records or prod. The new-lead SMS flow (`Send_SMS_new_Leads`) only fires for
`LeadSource = Facebook` and branch `JCGR57`, so these tests send nothing.

| Test | Result |
|---|---|
| Create an Opportunity directly (the request SLTeam reported failing) | **OK** — the write no longer fails |
| Create a Borrower Lead shaped like La Haus (branch 716, source "La Haus AIA") | OK |
| `POST /services/apexrest/lahaus/convert` on that Lead | **200, `alreadyConverted: false`**, Opportunity + Contact + Account created. The Opportunity gets owner = `ownerId` sent (Docs Lahaus). |
| Update that Opportunity: first-message fields, profile picklists (`3-6 months`, `300k-500k`, `FL`), `LaHaus_Appointment_Type__c = Virtual Meeting` + date, `StageName = Needs Analysis`, `DoNotCall__c` + `HasOptedOutOfEmail__c` | **All OK** |
| Vendor's phone lookup (`Phone_360SMS__c`, `IsClosed = false`) | Returns the converted Opportunity: `Phone_360SMS__c` is the digits of the phone |
| Move the Opportunity to Negotiation | **Blocked by two rules** (below) |
| Create a Work Item asking for `LOA2` | **Stored as `LOA1`** (below) |
| New Lead with the email of a Discarded "Don't want to be contacted" Lead | 400, flow custom error. **Also blocked with a different branch** (701), so staging has no branch filter; prod v3 would allow that case |
| Two active Leads, same email, same branch | Both inserted. The second becomes `…-(DUPLICATE)`, Discarded, `Duplicate Lead`, **keeps its own conversation id**; the first keeps its original conversation id but its **Phone is overwritten** with the second's |
| Lead converted without an Opportunity (fixture for the vendor's pending test) | Created with Apex: `ConvertedOpportunityId = null` |

### 11.1 Why Negotiation is hard to reach by API
1. **Validation rule `Require_LoanNumber_For_Update`** (active in both orgs): a Borrower Opportunity without
   `Loan__c` cannot change stage to anything other than Qualification / Needs Analysis / Closed Lost, and cannot
   get `Current_Status__c = Ratified`. Skipped when `Bypass_Validation_Rules__c = true`.
2. **Flow `Require_Supreme_Loan_Number_on_Negotiation`** (active v4 in **staging only**; inactive in prod): moving a
   Borrower Opportunity to Negotiation needs `Loan__c` or `Supreme_Loan_Number__c`.
   Both had to be satisfied to reach Negotiation in the test.

### 11.2 The Work Item role is set by the org, not by the vendor [Verified in both orgs]
`Set_LOA_Work_Item_Agent_Role` (before-save, on **create** of a Work Item with `Opportunity__c`) overwrites
`Agent_Role__c`: `Current_Status__c = Ratified` → `LOA2`; a name starting `First Touch - LOA1` → `LOA1`; anything
else → `LOA1`; the automated LOA2 milestone record type is excluded. It ignores the Opportunity **stage**.
Tests: role `LOA2` requested on a Negotiation Opportunity → stored `LOA1`; role `LOA1` requested on a Ratified
Opportunity → stored `LOA2`. The vendor's expectation ("LOA2 on a Negotiation Opportunity") conflicts with this
rule in prod as well as in staging.

### 11.3 Test records created (for cleanup)
| Object | Ids |
|---|---|
| Opportunity | `006Em00000rkabRIAQ` (direct), `006Em00000rjzglIAA` (converted; ended in Negotiation / Ratified with the bypass flag) |
| Lead | `00QEm00000gWF3lMAG` (converted), `00QEm00000gWFWnMAO` (Discarded opt-out), `00QEm00000gWFYPMA4`, `00QEm00000gWFa1MAG` (duplicate pair), `00QEm00000gWFbdMAG` (converted, no Opportunity) |
| Contact / Account (from conversions) | `003Em00001ShB6GIAV` / `001Em00001iClhuIAC`, `003Em00001ShXL3IAN` / `001Em00001iD3vtIAC` |
| Work Item | `a1IEm00000AlRrpMAF`, `a1IEm00000AlRtRMAV`, `a1IEm00000AlRv3MAF` |
Not deleted yet.

### 11.4 The `tdc_tsw__SMS_Opt_out__c` field (360 SMS package) [Verified 2026-10-01]
- The field **exists** on Lead, Opportunity and Contact in **both** staging and prod (Tooling API
  `CustomField`, namespace `tdc_tsw`; the same 15 package fields on the three objects in each org).
- **Staging:** the field is not visible to a System Administrator (`describe` does not list it; a write fails with
  "No such column ... on sobject of type Opportunity"), and **`FieldPermissions` has 0 rows for it**: no profile or
  permission set has field access.
- **Prod:** `FieldPermissions` has **86 rows** for the field on Lead and Opportunity, including **System
  Administrator and Agent Sales, read + edit**. This is the "already active in prod" that Melquiadez described.
  Oddity: my own prod session (System Administrator) still does not see the
  field in `describe` (469 fields listed), so whether an API write works in prod was **not** confirmed [Unverified];
  nothing was written to prod.
- The flows that read it (`Opt_in_Off_Opp`, `Opt_In_Off`, `Send_data_to_Opp_when_Lead_is_converted`) run in system
  context, so they are not affected either way.
- 360 SMS versions: `360 SMS` 1.323.9 in both orgs; prod also has `360 SMS Grid View` 1.53; `Zoom For
  Lightning` 2.28 (staging) vs 2.29 (prod).
- Melquiadez's pointer: ask 360 SMS support (`support@360degreeapps.zohodesk.com`) how to expose the field.
  [Unverified] whether FLS on this packaged field can instead be granted with a permission set.

## 12. Not explored yet
- Whether reactivating `Opt_in_Off_Opp` / `Opt_In_Off` in staging breaks anything (a metadata change; the
  `tdc_tsw__SMS_Opt_out__c` field is not visible to this user, so the SMS flags could not be tested).
- Which of the staging-only and prod-only flows would change a conversion outcome.
- Contents of `LaHaus_Outbound_Send` and `LaHaus_Note_History_*` flows.
- Who deactivated or edited the staging flows on 2026-09-30 22:53 UTC (needs Melquiadez).
