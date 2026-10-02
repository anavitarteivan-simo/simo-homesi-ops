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

**Status update 2026-10-02:** 25 of the 27 scenarios are now confirmed working. The 13 ✔ rows from the report plus
the 12 that were reported back to La Haus as resolved (5 ✘, 6 ◐ and the ⚠ "profile on Opportunity"), which La Haus
validated again (§11.6). Still open: the 2 other ⚠ rows (email of an opt-out Lead, email of an active Lead), which
depend on business decisions.

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
**Deleted 2026-10-02** (all 14 records; re-read afterwards: 0 live `ZZEXPL` rows; they sit in the staging Recycle
Bin). Only the records above were deleted. SLTeam's own test records (7 Leads including `TypeTest Interest`, and
their 8 Work Items) were **not** touched.

### 11.3b Cleanup the vendor asked for (report §15, points 4 and 5) [Verified 2026-10-02]
- **Point 4 (required) — done on 2026-10-02:** the 4 Work Items created by the vendor on `TypeTest Interest`
  (`006Em00000ol6htIAA`) were deleted: `a1IEm00000AknRNMAZ`, `a1IEm00000AknUbMAJ`, `a1IEm00000AknXpMAJ`,
  `a1IEm00000AknZRMAZ` (all created 2026-09-29, role LOA1, owner Melquiadez Rodriguez). Re-read: the 4 are in the
  Recycle Bin, and the Opportunity and its Lead are unchanged (same `LastModifiedDate`, Lead still converted).
- **3 other Work Items remain on that Opportunity and were not touched** (not part of the request, not
  vendor-created): `a1IEm00000AK0KfMAL` ("TEST-G2 Control on converted Opp", 2026-08-13),
  `a1IEm00000APR7SMAX` ("AI Follow-Up - FUR-REACT-OPP", 2026-08-18) and `a1IEm00000AQdETMA1`
  ("AI Follow-Up - FUR-AMSS2BUFO0", 2026-08-19), all created by Melquiadez Rodriguez.
- **Point 5 (optional) — not done on purpose:** the vendor's 6 Leads and 4 Lead-linked Work Items stay, because the
  vendor said it may want them for the next round (and they hold useful cases: the opt-out Lead and the duplicate
  pair). To be confirmed with the vendor.

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

## 11.5 Changes applied to `homesi-staging` (change log) [Verified]
| Date | Change | Ids | Verified by |
|---|---|---|---|
| 2026-10-02 | **Aligned flow `Search_lead_discarded_Don_t_want_to_be_contacted` with prod v3** (adds the `Branch__c` filter). New staging version 2 active, v1 `Obsolete`. The error-message link keeps the sandbox host. Two-phase deploy (gotcha #24). | Draft deploy `0AfEm00000Zt2HxKAJ`; activation deploy `0AfEm00000Zt2cvKAB`; active version `301Em00000gxQHvIAM` was v1, now v2 | Re-read the **active** version: lookup logic `(1 OR 2) AND 3 AND 4 AND 5` with `Branch__c`. Behaviour test with `ZZEXPL` leads: same email and same branch → blocked; same email, other branch → allowed (as in prod). Test leads deleted. |
| 2026-10-02 | **Reactivated `Opt_in_Off_Opp` (Opportunity) and `Opt_In_Off` (Lead) in staging** (B1). Both had one version (v1, `Obsolete`); their logic is identical to prod's active v2 / v5 (compared after dropping layout-only keys; the only differences were empty lists vs absent keys). Before-save, assignments only, no external calls. | Activation deploy `0AfEm00000ZtITCKA3` | Re-read: both `IsActive = true`, v1 `Active`. Behaviour: see §11.7. |
- **Rollback of the Search flow change:** reactivate version 1 (a `FlowDefinition` with `activeVersionNumber` 1, deployed to staging).
- **Rollback of B1:** deploy a `FlowDefinition` for each opt flow that leaves no active version (or deactivate in Setup).
- Metadata and manifests: PR on branch `salesforce/lahaus-staging-flow-alignment`
  (`salesforce/manifest/lahaus-staging-flow-alignment*.xml`).
- Not changed: `Require_Supreme_Loan_Number_on_Negotiation` (still active in staging only); it waits for an answer.

## 11.6 La Haus re-validation [relayed by the team, 2026-10-02]
- We told La Haus that the Opportunity route and "Visita agendada" on Lead could be re-validated, based on the
  staging write tests in §11 (conversion 200 with `alreadyConverted: false`; Opportunity updates passing).
- **La Haus replied that the scenarios reported as resolved passed.** That is **12 scenarios**: Lead converted →
  Opportunity; first message (Opportunity); profile (Opportunity); advisor, not interested and conversation finished
  (Opportunity, 3); unreachable (Opportunity); opt-out (Opportunity); and "Visita agendada" creation and reschedule on
  Lead and on Opportunity (4).
- Earlier message said "13 of the 14"; the correct count is **12 of the 14** non-green scenarios. The other 2 are the
  ⚠ rows in §3, which are still open.
- Source: the reply was relayed by the team; there is no new La Haus report document, so the details of their run
  (payloads, ids) were not seen [Unverified beyond the confirmation].
- **Still open, not part of the confirmation:** email of an opt-out Lead (Compliance), email of an active Lead
  (Business Owner), the Work Item role LOA2 in Negotiation (LOA Team Lead; the org sets the role, and Negotiation needs
  a loan number). Consultations C1 to C6 in the plan were drafted and are pending answers.

## 11.7 SMS opt-out field access and opt flows: validation (2026-10-02) [Verified]
**Field access.** On 2026-10-01 `FieldPermissions` had 0 rows for `tdc_tsw__SMS_Opt_out__c` in staging; on 2026-10-02
it had 35 rows on Lead and 35 on Opportunity (System Administrator, Agent, Agent Sales and Branch Manager, read + edit),
and the field is `createable` / `updateable` on Lead, Opportunity and Contact for a System Administrator. A write and a
read-back on a test Lead and Opportunity succeeded. The Setup Audit Trail shows **no entry** for this change in the
last 3 days, so **who or what granted it is not proven**. 360 SMS support said it extended the sandbox trial because
the sandbox was suspended, which is the likely cause [Unverified]. 360 asked for Login Access to the sandbox; it was
**not granted**, because the sandbox holds unmasked customer data (~11k Contacts, ~36k Leads; sample emails are
gmail/hotmail/yahoo addresses) and the access was no longer needed.

**Opt-in / opt-out exclusion with both flows active** (test records, all deleted afterwards):
| Object | Case | Expected | Result |
|---|---|---|---|
| Opportunity | create with opt-in and opt-out both true | opt-out wins: opt-in false | ✔ false / true |
| Opportunity | create with opt-in only | unchanged | ✔ true / false |
| Opportunity | then set opt-out true | opt-in cleared | ✔ false / true |
| Opportunity | then set opt-in true | opt-in wins on update, opt-out cleared | ✔ true / false |
| Lead | the same four cases | same | ✔ ✔ ✔ ✔ |

**La Haus route with the flows active** (the failure of 2026-09-29): Lead created, `POST /lahaus/convert` → 200,
`alreadyConverted: false`; then on the new Opportunity the first-message fields, profile picklists, appointment type and
date, `StageName = Needs Analysis`, `DoNotCall__c` + `HasOptedOutOfEmail__c` and `tdc_tsw__SMS_Opt_out__c = true` all
updated with no error. So the flows no longer block conversion or Opportunity writes.

Note: we never tried to activate the flows *before* the field became accessible, so it is **not known** whether the
field access was required for activation. It was required to test the SMS flags through the API.

## 12. Not explored yet
- Which of the staging-only and prod-only flows would change a conversion outcome.
- Contents of `LaHaus_Outbound_Send` and `LaHaus_Note_History_*` flows.
- Who deactivated or edited the staging flows on 2026-09-30 22:53 UTC (needs Melquiadez).

## 13. Where we stand and how to resume (2026-10-02)

### 13.1 State of `homesi-staging` after this work [Verified]
- `Search_lead_discarded_Don_t_want_to_be_contacted`: version 2 active (adds the `Branch__c` filter, same as prod v3).
- `Opt_in_Off_Opp` and `Opt_In_Off`: v1 active again (same logic as prod's v2 / v5).
- `tdc_tsw__SMS_Opt_out__c` is accessible (see §11.7). 360 SMS support asked for Login Access to the sandbox; it was **not
  granted** (the sandbox holds unmasked customer data).
- Not changed on purpose: `Require_Supreme_Loan_Number_on_Negotiation` (active in staging only).
- Fixture left **for La Haus**, do not delete: Lead `00QEm00000gYGzpMAG` ("Pruebas LaHaus AIA E"), converted with **no
  Opportunity**, phone +1 305 555 0199 (`Phone_360SMS__c` = `13055550199`), Contact `003Em00001Sl2nJIAR`, Account
  `001Em00001iG9ezIAC`. No open Opportunity has that phone, so the vendor's open-Opportunity lookup returns nothing.
- Our `ZZEXPL` test records were all deleted. The vendor's own test records (7 Leads, their Work Items and the new
  Lead D / Opportunity D set from their 2026-10-02 run) stay until they say.

### 13.2 Open PRs
- #10 `salesforce/lahaus-staging-flow-alignment`: the staging flow metadata (Search flow v2, opt flows activation). Already
  deployed to staging; the PR is the record. Not for prod as-is (the flow file is committed as `Draft`).
- #11 `docs/lahaus-r3-followup`: this doc's follow-up. Neither is merged.

### 13.3 Waiting for answers (all routed through Melquiadez; he escalates if needed)
| # | Question sent | If the answer is... | Then |
|---|---|---|---|
| 1 | What happened to `Opt_in_Off_Opp` on 2026-09-30 22:53 UTC | corrected, then deactivated / only deactivated | Only documentation; staging already has it active |
| 2 | Work Item role (`Set_LOA_Work_Item_Agent_Role`): keep? | keep | Tell La Haus to stop expecting LOA2 in Negotiation (already told them the rule) |
|   |  | change | Change the flow (needs LOA Team Lead sign-off); staging first |
| 3 | ~~Block a new Lead when a Discarded "don't want to be contacted" Lead exists: keep?~~ **DECIDED 2026-10-02: the rule stays; not a question for Melquiadez, only La Haus is informed** | done | See §13.5 |
| 4 | ~~Duplicate Lead overwrites the original's phone: intended?~~ **DECIDED 2026-10-02 (Melquiadez): it is the designed behaviour, no change** | done | See §13.5. May be revisited later |
| 5 | `Require_Supreme_Loan_Number_on_Negotiation` (staging only): align with prod? | align | Deactivate it in staging via a `FlowDefinition` deploy |
| 6 | ~~`Bypass_Validation_Rules__c` stays true on converted Leads: keep or reset?~~ Melquiadez chose "reset after converting" on 2026-10-02, but **it cannot be done**: a converted Lead cannot be updated (`CANNOT_UPDATE_CONVERTED_LEAD`, tested in staging). | **blocked: tell Melquiadez** | See §13.5 and §13.6 |
| 7 | ~~La Haus opt-out should also set the SMS opt-out?~~ **DECIDED 2026-10-02 (Melquiadez): yes, La Haus sends it too** | done | See §13.5; tell La Haus the field works in staging |
| 8 | Prod go-live date; 6 `LaHaus_*` Lead fields missing in prod | date set | Run `/prod-preflight`; deploy the fields with FLS first (gotchas in `salesforce/CLAUDE.md`) |
| 9 | Dedicated profile for the integrator (today System Administrator in both orgs) | yes | Plan a profile / permission set; check which flows skip administrators |
| 10 | Delete the 2 `ZZTEST` prod records (`00QQg00000nHYNdMAO` + its Opportunity `006Qg00000qyMZDIA2`, `00QQg00000nHIxDMAW`) | yes | Prod delete with explicit confirmation; read before deleting |
| 11 | What 360 did to enable the SMS field; is the Outgoing/Incoming sync needed? | answer | Reply to the 360 ticket (draft already prepared); do not grant Login Access |
| 12 | Review of PR #10 and #11 | approved | Merge them (separate, confirmed step) |

### 13.5 Decisions taken
| Date | Decision | Consequence |
|---|---|---|
| 2026-10-02 | **Keep the rule** `Search_lead_discarded_Don_t_want_to_be_contacted` (a before-save flow that blocks creating a Lead when a Discarded "Don't want to be contacted" Lead has the same email or phone and the same `Branch__c`). The rule already existed and is not changed. | The business does not need to approve anything. La Haus is told that the 400 (`FIELD_CUSTOM_VALIDATION_EXCEPTION`) is a final answer: do not create the Lead, do not retry, do not update the discarded Lead, and record on their side that the customer must not be contacted. This closes La Haus question 1 in their report; Melquiadez is informed, not asked. |
| 2026-10-02 | **Duplicate Leads stay as designed** (decision by Melquiadez): inside the same `Branch__c`, the new Lead becomes `-(DUPLICATE)` and Discarded, and the original receives the new Lead's phone. It only applies within the same branch. He suggests re-visiting the behaviour later if it keeps working this way. | No org change. La Haus can still add its own email lookup before creating, but it is not required. Low-priority review item for later. |
| 2026-10-02 | **Reset `Bypass_Validation_Rules__c` after converting** (decision by Melquiadez) is **not feasible**; see §13.6. | No code change was made. Waiting for Melquiadez to confirm the alternative (keep the flag on converted Leads). |
| 2026-10-02 | **La Haus must also send the SMS opt-out** (`tdc_tsw__SMS_Opt_out__c`) on opt-out (decision by Melquiadez, who believed the field does not work in sandbox until prod). | The field **does** work in staging since 2026-10-02 (§11.7), so La Haus can test it now. The opt flows clear the opt-in when the opt-out is true. |


### 13.6 Why the bypass flag cannot be reset after conversion [Verified in staging 2026-10-02]
- A Lead that is already converted **cannot be updated**: `Database.update` on it returns `CANNOT_UPDATE_CONVERTED_LEAD`
  ("cannot reference converted lead"), as a System Administrator, with no validation rule involved. The probe (a test Lead
  converted by Apex, then `Bypass_Validation_Rules__c = false`) was deleted afterwards.
- Resetting the flag **before** the conversion does not work either: the conversion save itself evaluates the Lead
  validation rules. In prod `Check_Fields_For_Qualified_Borrower` is **active** and, for a Borrower Lead with
  `Status = Qualified`, requires Loan Officer, Income, Debts (and Rent if renting) unless the flag is true; La Haus Leads do
  not have those fields. In staging that rule is **inactive**, so a staging test of any reset would pass and fail in prod.
- Practical effect of leaving the flag true on a converted Lead: it cannot be edited any more, so no validation rule can fire
  on it again. The flag is not copied to the Opportunity (it is false there after conversion, checked in staging).
- The cost of leaving it is that the flag no longer separates "converted by La Haus" from normal Leads other than by value;
  `LeadSource = 'La Haus AIA'` and `LaHaus_Conversation_Id__c` still identify them.
- Options: (A) keep the flag as is (recommended: no change, no risk); (B) change the Lead validation rules so they do not
  run after conversion, and then reset it; that is a prod validation-rule change for the business to approve and is not worth it
  for a flag that no longer has any effect.

### 13.4 Still to do on our side
- Tell La Haus that the rule stays and how to handle the 400 (§13.5); message drafted.
- Ask La Haus to re-run the Opportunity route with the opt flows active, and to re-check the opt-out Lead case (same branch
  still returns 400; another branch now creates the Lead). Already drafted; send status unknown.
- Reply to the 360 ticket (no Login Access; ask what changed and whether the sync is still needed).
- 3 Work Items on `TypeTest Interest` are FUR tests by Melquiadez (`a1IEm00000AK0KfMAL`, `APR7SMAX`, `AQdETMA1`); not ours.
- If La Haus later asks for an open Opportunity with the fixture's phone, create it with `Phone__c` = `+13055550199`.
