# Salesforce Automation Inventory — Simo Solutions Group / Homesi

**Org:** HomeSi (`00DKb000000OvoRMAS`) · production, alias `prod`
**Sandbox:** `homesi-staging` (`00DEm000008XXK7MAO`) — not inventoried; staging lags prod.
**Generated:** 2026-09-29 from the live production org, read-only (SOQL/Tooling queries + metadata retrieve).
**Regenerate with:** `scripts/salesforce/automation-inventory/` (see the appendix). Do not hand-edit this file.

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

{{FLOWS}}

---

## 4. Rules

### 4.1 Validation rules (29)

Most rules honour `Bypass_Validation_Rules__c` and exclude the Automated Process user and the
integration user. Formulas are shown as stored (truncated at 300 characters).

{{VR}}

### 4.2 Sharing rules (90)

Org-wide defaults: **Lead, Opportunity, Account = Private; Contact = Controlled by Parent.**
86 of the 88 criteria rules give **Edit** (2 give Read) to a public group per branch / team.
Almost all match on `Branch__c`; a few match on `OwnerId` (a specific user's records), one on
`Loan_Officer_Text__c` (the text mirror kept by the `SyncLoanOfficerText` trigger), one on
`Affinity_Program__c` and one on Lead `Co_Owner__c`. Adding a branch means adding a rule on
**both** Lead and Opportunity. Record access for LOA roles comes from the Apex sharing
triggers in §5, not from these rules.

{{SHARING}}

⚠️ `Contact.Contact_All_Internal_Read` still exists in metadata with **Edit** access (its label
says "Read"), although [`ORG_REFERENCE.md`](ORG_REFERENCE.md) records it as deleted when the
Contact OWD change was reverted. While Contact stays *Controlled by Parent* it has no effect
[Likely]; it would take effect if the Contact OWD were ever changed. See §7.

### 4.3 Duplicate and matching rules

Only `Standard_Account_Duplicate_Rule` is active. Lead duplicate handling is done in Apex
(`LeadPhoneTrigger` → `DetectDuplicateHandler`) and the flow
`not_allow_to_create_non_borrowers_leads`, not by duplicate rules (see `ORG_REFERENCE.md`).

{{DUPMATCH}}

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

{{FINDINGS}}

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

Run [`scripts/salesforce/automation-inventory/`](../../scripts/salesforce/automation-inventory/README.md):
`./fetch.sh <workDir> prod` then `./run.sh <workDir> docs/salesforce/AUTOMATION_INVENTORY.md`.
Edit the prose in that folder's `template.md`, the findings in `findings.md` and the
descriptions of undocumented flows in `purposes.json` — never this file. What the scripts do,
all read-only against prod:

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
