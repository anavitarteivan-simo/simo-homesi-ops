# Data Dictionary — Simo Solutions Group / Homesi

**Org:** HomeSi (`00DKb000000OvoRMAS`) · **Generated:** 2026-08-25

> **Scope note — read this first.** Opportunity has ~65 tracked custom fields in the repo and
> Lead has ~374. A raw dump of every field is low-signal. This document is **curated by
> significance** and organised around the question no schema query can answer:
> **who writes this field?** That is the single most useful fact when debugging or building.
> The appendix has the query to produce an exhaustive list when you need one.

**Writer legend:** 🔌 Encompass integration · ⚙️ Flow · 🧩 Apex · 👤 User · 🧮 Formula/rollup

---

## 1. Core objects

| Object | API name | Role |
|---|---|---|
| Opportunity | `Opportunity` | The **loan**. Borrower record type is the mortgage; other RTs are recruitment pipelines |
| Lead | `Lead` | Pre-conversion borrower / realtor / LO / broker |
| Contact | `Contact` | Realtors, agents, borrowers, third parties |
| Work Item | `Mortgage_Condition__c` | LOA task, mortgage condition, or milestone. Label "Work Item" |
| NPPM | `NPPM__c` | Realtor partner in the NPPM programme |
| Loan Officer | `Loan_Officer__c` | LO roster (~1,600), links to a Salesforce User |

### Record type Ids (identical in prod and staging)

| Object | Record type | Id |
|---|---|---|
| Lead | Borrower | `012Kb000000RpDAIA0` |
| Lead | Broker | `012Kb000000RpDBIA0` |
| Lead | Loan Officer | `012Kb000000RpDCIA0` |
| Lead | Realtor | `012Kb000000RpDDIA0` |
| Lead | SiMo BPO | `012Qg000003xvgTIAQ` |
| Opportunity | **Borrower** | `012Kb000000RpDEIA0` |
| Opportunity | Realtor | `012Kb000000RpDHIA0` |
| Opportunity | SiMo BPO | `012Qg000003xvgUIAQ` |
| Work Item | Mortgage Condition | `012Qg000003tTm2IAE` |
| Work Item | LOA2 Milestone Task | `012Qg000003tTm1IAE` |
| Work Item | Task | `012Qg000003uX4PIAU` |

⚠️ Staging has a 6th record type, **Refinance**, on Lead and Opportunity that prod does not.

---

## 2. Opportunity — milestone dates (all 🔌 Encompass)

**These are the spine of the LOA2 automation.** Every one is written by Encompass, never by a
user, and each drives a work item and a notification email.

| Field | Label | Drives |
|---|---|---|
| `Application_Date__c` | Application Date | Notification #1, Issue Disclosures |
| `LE_Sent_Date__c` | LE Sent Date | #2, Disclosures Follow-Up |
| `LE_Due_Date__c` | LE Due Date | Due date for Issue Disclosures |
| `LE_Revised_Date__c` | LE Revised Date | Closes COC Rate Locked |
| `Disclosures_Signed_Date__c` | Disclosures Signed | #6, Order Appraisal, Send to Processing |
| `Appraisal_Ordered_Date__c` | Appraisal Ordered | Closes Order Appraisal |
| `Appraisal_Received_Date__c` | Appraisal Received | #4, Appraisal POD |
| `Appraisal_Proof_of_Delivery_Date__c` | Appraisal POD | Closes Appraisal POD |
| `Lock_Date__c` | Lock Date | #5, COC Rate Locked, ICD Request |
| `Lock_Exp_Date__c` | Lock Expiration | Lock expiry work items (−3d / +1d) |
| `Title_Commitment_Date__c` | Title Commitment | ICD Request (1 of 3) |
| `Hazard_Insurance_Date__c` | Hazard Insurance | ICD Request (1 of 3) |
| `ICD_Date__c` | ICD Date | Closes ICD Request |
| `Submitted_to_Processing_Date__c` | Submitted to Processing | #7, IPR Wait |
| `Submitted_to_UW_Date__c` | Submitted to UW | #8 |
| `Initial_UW_Decision_Date__c` | Initial UW Decision | #9 |
| `Resubmitted_Date__c` | Resubmitted Date | #10 (set) / Resubmitted to Processing (cleared) |
| `Clear_to_Close_Date__c` | Clear to Close | #11 |
| `Disbursement_Date__c` | Disbursement Date | Funding; synced to standard `CloseDate` |
| `COC_LE_Trigger__c` | COC LE Trigger | #12a. **Number(18,0) counter**, not a flag |
| `COC_CD_Trigger__c` | COC CD Trigger | #12b. Counter. **Zero records populated as of 2026-08-25** |

⚠️ **These fields are only ever written on loans where `Loan__c` is populated and
`Lender__c LIKE '%Eve%'`** — about **2,010** open Borrower loans. The rest of the pipeline
(~20k open opps) never receives them, so milestone automation never fires there.

⚠️ Encompass frequently lands **several dates in one save** and **out of order**. Any logic
gated on "the next date is still blank" will silently skip. This caused orphaned work items
and is why notification #2 sometimes never sends.

---

## 3. Opportunity — people and routing

| Field | Type | Writer | Notes |
|---|---|---|---|
| `Loan_Officers__c` | Lookup(`Loan_Officer__c`) | 🔌👤 | Email via `Loan_Officers__r.Email__c`. **86%** populated in processing |
| `LOA1__c` / `LOA2__c` | Lookup(User) | ⚙️🧩 | Lookup filter = profile **Agent Loa On-Demand** (message says "title", it checks profile) |
| `LOA__c` / `LOA_2__c` | Text | 🔌 | LOS-written names; flow resolves them to the User lookups |
| `LOA2_Name__c` | 🧮 Formula | — | `LOA2__r.FirstName & " " & LastName`. Compound `Name` cannot be referenced cross-object |
| `Loan_Processor__c` | Text(50) | 🔌 | Processor **name** — **94%** populated |
| `Loan_Processor_Email__c` | Email | 🔌 | Processor **email** — only **20%** populated. Known integration gap |
| `Processor_Jr__c` / `Processor_Jr_Text__c` | Lookup(User) / Text | ⚙️🔌 | Junior processor |
| `Account_Executive__c` | Text(50) | 👤 | With `Affinity_Program__c` drives owner reassignment via Apex |
| `Referred_By__c` | Lookup(Contact) | 👤 | Referral origin. Requires `Referred_Date__c` (VR) |
| `Listing_Agent__c` / `Buyers_Agent__c` | Lookup(Contact) | 🧩 | Set by `OpportunityUpdater`; related lists not on Contact layout |

---

## 4. Opportunity — status, stage, risk

| Field | Type | Writer | Notes |
|---|---|---|---|
| `StageName` | Picklist | ⚙️👤 | Closed Won is **automation-only** (VR). Recomputed by before-save flow |
| `Current_Status__c` | Picklist | ⚙️ | Cleared on close. Do not treat as user-owned |
| `Current_Milestone__c` | Text(50) | 🔌 | Started → Processing → Submittal → Initial Decision → Resubmittal → CTC → Closing |
| `Loan_Status__c` | Picklist | 🔌 | Terminal values block stage reopening |
| `Loan_Folder__c` | Text | 🔌 | "Adverse Loans" = terminal |
| `Closed_Loan__c` | Checkbox | 🔌 | True when funded |
| `Healthiness__c` | Picklist | 👤⚙️ | On Track / Delayed / Out of Scope. Auto-fills from Stat risk when blank |
| `Stat_Closing_Risk__c` | 🧮 Formula | — | Forward-looking risk for open pipeline |
| `Closing_On_Time__c` | 🧮 Formula | — | "On Time" / "Delayed"; null until closed |
| `On_Time_Pct__c` / `Delayed_Pct__c` | 🧮 Formula | — | 100 / 0 / null — AVG gives a percentage directly |
| `Days_In_Current_Stage__c` | 🧮 Formula | — | Blank when the milestone date is missing (deliberate) |
| `Branch__c` | Picklist | ⚙️🔌 | 24 active values. Skipped by integration when `Branch_Transfer__c` = true |
| `Loan__c` | Text(50) | 🔌 | Loan number. Required before most stage changes (VR) |
| `LoanId__c` | Text | 🔌 | Encompass GUID; primary match key |
| `Lender__c` | Text(50) | 🔌 | `LIKE '%Eve%'` = Everett Financial |

### Deprecated / trap fields — do not use
| Field | Why |
|---|---|
| `Loan_Officer__c` (singular) | Labelled "Deprecated". Use `Loan_Officers__c` |
| `Closed_Won_Date__c` | Only ~50% populated. Label collides with standard CloseDate. Use `CloseDate` |
| `Needs_Agent__c` / `Needs_Agent_Date__c` | **Repurposed 2026-08-24.** Old metadata described opposite semantics |

---

## 5. Lead — prequalification (⚙️ Screen Flow `Prequalification_Form`)

Written by the bilingual intake flow, launched from the **Start Prequalification** quick action.

| Field | Notes |
|---|---|
| `Prequal_Income_Range__c` | Picklist bands. Also exists on Opportunity |
| `Prequal_Downpayment_Range__c` | Picklist bands. Also on Opportunity |
| `Prequal_Housing_Status__c` | Renting / Owns / Rent Free / Other |
| `Prequal_Housing_Other__c` | Required when housing = Other |
| `Prequal_Rent_Method_Other__c` / `Prequal_Rent_Paid_To_Other__c` | "Other" specify boxes |
| `Prequal_Required_Documents__c` | Built by Decision `dec_Docs`, **not a formula** |
| `CoBorrower_Required_Documents__c` | Co-borrower equivalent via `dec_CoDocs` |
| `CoBorrower_ID_Type__c` | SSN / ITIN |
| `Prequal_Best_Day_To_Contact__c` / `..._Time_...` | Multiselect, `;`-joined into Text(255) |
| `Prequal_Docs_Expected_Date__c` | Creates a document-collection Work Item |

⚠️ Flow **formulas null-poison and cannot reference other formulas** — document logic must use
Decision elements.

## 6. Lead — NPPM, strategy, routing

`NPPM_Realtor__c` (Lookup NPPM) ⚙️ · `Referred_By_NPPM__c` (Yes/No) ⚙️ ·
`Strategy__c` ⚙️ · `Referred_By__c` 👤 · `Branch__c` ⚙️👤 · `Lead_Importance__c` ⚙️ ·
`Preferred_Language__c` (EN/ES — **staging only** as of 2026-08-11) ·
`Cloned_From_Id__c` (SiMo BPO provenance) · `Bypass_Validation_Rules__c` ·
`Skip_Loan_Creation__c` · `MonitorBase_Alert__c` / `..._Date__c` / `MonitorBase_Indicator__c`

---

## 7. Work Item — `Mortgage_Condition__c` (32 fields)

| Field | Type | Writer | Notes |
|---|---|---|---|
| `Name` | Text(80) | ⚙️🧩 | **Dup guards and auto-close match on the Name prefix** — renaming breaks automation |
| `Condition_Name_LTA__c` | Long text | 🧩👤 | Full condition text |
| `Opportunity__c` / `Lead__c` | Lookup | ⚙️👤 | Either parent; Lead items are Task RT only |
| `Status__c` | Picklist | 👤⚙️ | Not Started / In Progress / On-Hold / Completed / Waived / N/A |
| `Is_Complete__c` | 🧮 Formula | — | Drives every "open item" filter |
| `Agent_Role__c` | Picklist | ⚙️ | LOA1 / LOA2 / Processor |
| `Assigned_Date__c` / `Completed_Date__c` | DateTime | ⚙️ | SLA baseline |
| `Due_Date__c` | Date | ⚙️👤 | Business-day formulas, weekends only (no holidays) |
| `Latest_Note__c` | Text(255) | 👤 | The writable note everywhere |
| `Notes__c` | Long text | ⚙️ | Append-only history, newest first, GMT stamps |
| `Priority__c` | Picklist | 👤 | High / Normal / Low |
| `Borrower_Email__c`, `Borrower_Phone__c`, `Listing_Agent_*`, `Buyers_Agent_*` | 🧮 Formula | — | Cross-object pull-downs so the auto report type can expose them |

**OWD Private.** `MortgageChecklistController` is `without sharing` **on purpose** so the
on-record widget shows all items to anyone who can open the loan.

---

## 8. NPPM — `NPPM__c`

`Name` · `Role__c` (Realtor-NPPM / Realtor-BD — **both qualify**) · `Email__c` · `Phone__c` ·
`Brokerage__c` · `Source_Opportunity__c` (Lookup Opportunity — the join to the referral chain)

⚠️ **No User lookup exists.** There is no Id path from a Salesforce User to an NPPM record;
`Owner.Title` proves someone *is* an NPPM but never *which* one.

---

## 9. Custom settings

**`Notification_Settings__c`** (hierarchy) — `Test_Mode__c` (Checkbox), `Test_Recipient__c` (Email).
When Test Mode is on, all 12 notification flows route to the test recipient.
**It misdirects rather than suppresses** — to pause notifications, deactivate the flows.

---

## Appendix — exhaustive field list

```sql
-- All custom fields on an object, with type
SELECT QualifiedApiName, Label, DataType
FROM FieldDefinition
WHERE EntityDefinition.QualifiedApiName = 'Opportunity'
ORDER BY QualifiedApiName
```

Caveats:
- `FieldDefinition` reflects the **running user's field-level security**. A field you lack FLS
  on is silently omitted, and `SELECT` on it returns `INVALID_FIELD: No such column`. Absence
  is **not** proof a field doesn't exist — a deploy's `created: true|false` is the only
  authoritative check.
- `FieldDefinition` does not expose field Description. Descriptions require a per-field
  Tooling `CustomField.Metadata` query, which returns one row at a time.
