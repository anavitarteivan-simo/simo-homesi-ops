# Lead Import — Project Reference (CLAUDE.md)

Reference for any AI agent or teammate running the **Salesforce lead-import** workflow for the Simo/Homesi org (alias `prod`). Captures the canonical field map, the IDs we keep reusing, the dedupe rules, and the hard-won gotchas from real batches. Rename to `CLAUDE.md` inside the project folder.

---

## 1. What the workflow does

Takes a raw lead list (any format — .xlsx, .csv, .pdf, pasted text) and produces **two files**:

- **NEW.csv** — Data Import Wizard–ready, only rows that are safe to create fresh.
- **IN_QUESTION.csv** — source rows that already have an *open* Lead/Opportunity, with a `Disposition` column for a human to decide.

Never guess the batch settings. Always ask (Owner, Branch, Lead Source, Record Type, **Referred By + Referred Date**) before building. Referred By/Date are asked on *every* batch even when the answer is "none."

Pipeline: inspect file → ask settings → parse & normalize → fold unmapped columns into Notes → intra-file dedupe → Salesforce dedupe (email + phone) → classify blockers → write the two files → verify.

---

## 2. Canonical IDs (verified in prod)

### Record types (Lead)
| Type | Id |
|---|---|
| Borrower | `012Kb000000RpDAIA0` |
| Realtor | `012Kb000000RpDDIA0` |
| Broker | `012Kb000000RpDBIA0` |
| Loan Officer | `012Kb000000RpDCIA0` |

### Owners / Users seen
| Name | User Id | Notes |
|---|---|---|
| Giovanni Osorio | `005Kb00000B1ZE0IAN` | Common Borrower owner |
| Mariano Claudio | `005Kb00000B1ZGaIAN` | |
| Juseth Castro | `005Qg00000Qd5lgIAB` | |
| Javier Peñaloza | `005Kb00000B1ZDCIA3` | Profile "Agent Sales" |
| Adriana Gonzalez | `005Qg00000TxaOXIAZ` | LO Profile (user) |
| **Ana Zegarra** | `005Qg00000Qd5lhIAB` | **= "Ana Pena"**, email `ana.pena@supremelending.com`, Branch Manager |
| Adriana Romero | `005Qg00000Jasa1IAB` | Used as **Co-Owner**; Agent Loa On-Demand |
| Carolina Zazzali | `005Kb00000B1ZD2IAN` | Used as **Sales Agent**; profile "Agent" |

### Loan Officer custom-object records (for `Lead.Loan_Officer__c` lookup — NOT the User)
| LO | `Loan_Officer__c` Id | Linked user? |
|---|---|---|
| Adriana Gonzalez | `a08Qg00000u7kU7IAI` | **No linked user** → no auto-share |
| Ana Zegarra | `a08Qg00000FdopBIAR` | Linked to `005Qg00000Qd5lhIAB` |

### Referred-By Contacts (pick the one with referral history)
| Referrer | Contact Id | Notes |
|---|---|---|
| Amitay Huerta | `003Kb00001XmSwMIAV` | DHS Realty |
| Daniella Ottone | `003Qg00000tY9lxIAC` | NPPM 724 |
| Lucio Romero (master) | `003Qg00000gAkvuIAC` | LPT Realty — holds 266 lead + 18 opp referrals |
| Lucio Romero (dup) | `003Qg00000qSXntIAG` | Lion Drive — 0 referrals but **real working contact** (89 activities, buyers agent on 4 opps). Do NOT blindly delete. |
| Manuel Solano (master) | `003Kb00001XmSsuIAF` | 22 lead referrals |
| Manuel Solano (dup) | `003Qg00000aeWJ1IAM` | 0 referrals |

---

## 3. Field map → Data Import Wizard headers

The wizard matches on **display-label headers**. Use these header strings EXACTLY:

| CSV header | Lead field | Notes |
|---|---|---|
| First Name | FirstName | |
| Last Name | LastName | **Required.** Single-word name → Last = `Unknown`. |
| Company | Company | **Required.** Default = `First + Last`. |
| Email | Email | Lowercase; blank if it fails `[^@\s]+@[^@\s]+\.[^@\s]+`. |
| Phone | Phone | Format `+1 (XXX) XXX-XXXX` exactly. |
| State | State | **RESTRICTED picklist — FULL state name** (`Florida`, not `FL`). Header is `State`, NOT `State/Province`. |
| Lead Source | LeadSource | Unrestricted (any string stores). |
| Branch | Branch__c | **Required on every row, every record type** (skill policy). |
| Owner ID | OwnerId | User Id. |
| Record Type ID | RecordTypeId | See §2. |
| Referred By | Referred_By__c | Contact **Id** under this header. NOT "Referred By ID". |
| Referred Date | Referred_Date__c | Required whenever Referred By is set (VR). Default = today. |
| Loan Officer | Loan_Officer__c | `Loan_Officer__c` **custom-object** Id (not a User). |
| Sales Agent | Sales_Agent__c | User Id. Lookup filter = profile IN ("Agent Loa On-Demand","Agent"), enforced. |
| Co-Owner | Co_Owner__c | User Id. Triggers `LeadCoOwnerSharing`. |
| Property Address | (street) | Org label for street is **Property Address**. |
| Property Postal Code | (zip) | Org label for zip is **Property Postal Code**. |
| Do Not Call | DoNotCall | `TRUE` / blank. |
| Notes | **Notes__c** | Long Text Area(40000). **NOT `Jungo_Notes__c`.** Multi-line ok (see §6). |
| CoBorrower FirstName/LastName/Email/Phone | CoBorrower_*__c | Only include when co-borrower data exists. |

**Do NOT include:** a `Status` column (defaults to New), or `Lead Importance` (`Lead_Importance__c` — omit per policy; values are Low/Medium/High if ever needed).

---

## 4. Validation rules that bite

- **LeadSource_Required_Borrower** — Lead Source required on Borrower leads.
- **branch_mandatory_validation_rule** — Branch required when status moves to Discarded/On-hold/Working/Qualified (not at New insert, but always include Branch anyway).
- **Referred_By_Required_For_BD_Borrower** — Referred By set ⇒ Referred Date required. Together-or-not-at-all.
- **Check_Field_Lead_Importance_Borrower** — references Lead Importance; we omit the column.

---

## 5. Salesforce dedupe & classification

Query existing records by **email** and **phone**:
- Lead phone match: `Phone IN ('+1 (XXX) XXX-XXXX', ...)` — exact formatted string.
- Opp phone match: `Phone_360SMS__c IN ('XXXXXXXXXX','1XXXXXXXXXX', ...)` — digits only, match **both** bare and `1`-prefixed variants.
- Opp email field is `Email__c` (not `Email`).

**Blocker** (→ IN_QUESTION): open Lead (`IsConverted=false AND Status != 'Discarded'`) OR open Opp (`StageName NOT IN ('Closed Won','Closed Lost')`).

**Non-blocker** (→ allowed into NEW): Lead `Status='Discarded'`; Lead `IsConverted=true`; Opp `Closed Won`/`Closed Lost`. A source row goes to NEW only if it has **zero** blockers.

> Reloading a non-blocker creates a fresh duplicate of a dead/discarded record **by design** (a new workable lead). Intended, but be aware.

Lead Source values that exist in prod (unrestricted, but match an existing one when the user gives an approximation): `Realtors Base Digital`, `Recruitment Base Digital`, `Broker Affinity Base`, `Recruitment Base Digital-Broker`, `Juseth Database`, `Realtors Base Digital Webinar`, `Own Database`, `Credit Union and Community Bank Base`, `Recruitment Base Digital Dual License`, plus `Referral`, `Facebook`, `Past Client`. (e.g. user said "Realtor Base Digital" → real value is **`Realtors Base Digital`**.)

---

## 6. Import mechanics

- **NEW.csv → "Add new records"** in the Data Import Wizard. Do NOT use "Add new and update existing": there's no Lead Id column to match on, and you don't want to touch existing records.
- **"Add new and update existing"** is only for IN_QUESTION dispositions — and those are better done by Salesforce **Id via the API**, not the wizard.
- **Single lead** → create directly with the connector `createSobjectRecord` on `Lead` (Company is required). Example done this session: Rossy Iraheta → `00QQg00000mAjjOMAS`.
- **Multi-line Notes** — write with Python's `csv` module so newlines get quoted. The Data Import Wizard occasionally mangles embedded newlines on some browsers → fall back to **Salesforce Inspector** (Data Update / Data Insert) for those files.

---

## 7. Gotchas (hard-won on real batches)

1. **Inspect raw first, `header=None`.** Source files came in three messy shapes: (a) name+phone+email mashed into one column; (b) vertical **stacked blocks** separated by blank rows (`Name:`/`Phone:`/`Email:`); (c) **mixed within one file** — top rows columnar, bottom rows a single multi-line cell. A naive `read_excel` silently dropped ~40% of rows in one case.
2. **The first data row can be swallowed as the header** (no header row in export). Read with `header=None` and reconstruct.
3. **State is restricted, full-name only.** `FL`→`Florida`. Cities land in the State column: `Houston`/`Austin`→`Texas`, `Iuta`→`Utah`, `Pensilvania`→`Pennsylvania`. Preserve the original in Notes when remapping.
4. **Phone formats vary wildly:** 10-digit, 11-digit w/ leading `1`, "3-7" split (`567-2246543`), stray trailing dots, leading `": "`. Strip to 10 digits, drop leading `1`, reformat. Junk-filter all-same-digit.
5. **Mojibake** from Word/PDF/CRM exports: `√Å`→`Á`, smart quotes/dashes. Normalize before writing or Salesforce shows garbage.
6. **Co-borrower pairs** appear in the name cell (`A & B`, `A y B`, `A, B`). Split the 2nd person into `CoBorrower *` fields, not Notes. Shared-surname heuristic (`Maribel & Jesus Garcia`) is imperfect — **spot-check**.
7. **`Sales_Agent__c` lookup filter is enforced** (`isOptional=false`): profile IN ("Agent Loa On-Demand","Agent"). Carolina Zazzali (Agent) passes; a different profile would reject the import.
8. **Owner vs Loan Officer confusion.** A file's "Owner" column may actually be the LO. On the Amitay batches, owner = Giovanni while Adriana was "just the LOA." Confirm; don't assume the column label.
9. **`Loan_Officer__c` auto-share depends on a linked user.** Adriana Gonzalez's LO record has no `Salesforce_User__c`, so setting it records the LO but does **not** share the lead to her. Ana Zegarra's LO record *is* linked.
10. **Duplicate referrer Contacts are common.** Pick the one WITH referral activity (`SELECT Referred_By__c, COUNT(Id) ... GROUP BY`). The "empty" dup may still be a live working contact (Lion Drive Lucio: 0 referrals but 89 activities + buyers agent on 4 opps). **Native `merge` DML breaks** on the `tdc_tsw` (360 SMS) trigger — use manual repoint + delete, and only after checking every reference.
11. **"Ana Pena" = Ana Zegarra.** Resolve owners by email (`ana.pena@supremelending.com`) when the display name doesn't match.
12. **Double-upload creates duplicates.** The Data Import Wizard does NOT dedupe against prior imports. One file loaded on 8/19 and again on 8/25 produced duplicate pairs; SF's dup rules tagged the second copies `-(DUPLICATE)` and Discarded some. **Always SF-dedupe before every load, and check `CreatedDate` to detect a prior upload of the same batch.**
13. **`FieldDefinition` / `SELECT field` reflect the running user's FLS.** A field can read as "missing" when it's really "no FLS." Trust a deploy's `created:true/false`, not a query, for existence.
14. **Discard rows with no email AND no phone** — unmatchable and undialable. Report the count.
15. **`Phone_360SMS__c` is sometimes `1`-prefixed, sometimes not** — always match both variants.

---

## 8. Verify checklist (before handing over NEW.csv)

- Every row: non-blank Last Name, non-blank Company, Lead Source, Branch.
- State (if present) is a full state name, never a 2-letter abbrev.
- Every row with Referred By also has Referred Date.
- No row has both Email and Phone blank.
- Every phone matches `^\+1 \(\d{3}\) \d{3}-\d{4}$`; every email matches the email regex or is blank.
- No `Status` and no `Lead Importance` column.
- File reparses with `csv.DictReader`; multi-line Notes survive quoting (no ragged rows).
- IN_QUESTION shows **names** (Owner, Referred By), never raw Ids.
