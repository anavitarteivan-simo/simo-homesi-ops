# Contact ownership, lead conversion and duplicate handling

Why can someone own a Contact without owning any Opportunity of that contact, and what does
(and does not) stop duplicate Contacts / Accounts / Opportunities? Findings from live reads of
**prod** (`--target-org prod`, org `00DKb000000OvoRMAS`). Nothing was changed to produce them.

Tags: **[Verified]** read live on the date shown · **[Likely]** strong inference ·
**[Unverified]** not checked.

Raised 2026-10-01 after Production reported a duplicate Opportunity. A summary for Business
Development is in `reports/2026-10-01-owner-contact-sin-opportunity.pdf` (see
`reports/README.md`); this file is the living version.

---

## 1. Contact owner is independent of Opportunity owner

Nothing in the org ties them together. [Verified 2026-10-01]

- **Profile `Agent Sales` has Read, Edit, View All and Modify All on Contact.** An agent sees every
  Contact, edits it, and can change its `OwnerId`. `ViewAllData` / `ModifyAllData` are false, so
  this comes from the object permission, not the org-wide one.
- **`Agent Sales` and `Branch Manager` both have `ConvertLeads` and `TransferAnyEntity`.**
- **Contact has no validation rules.** [Verified]
- **No flow or trigger compares Contact owner with Opportunity owner.** Searched the flow
  inventory and the Contact triggers. [Verified for what was searched]
- Contact triggers: `FormatContactFields` (formats `NMLS_Number__c` only),
  `UpdateAccountEmployeeCountTrigger`, and `ContactTrigger`. **`ContactTrigger` belongs to the
  managed package `tdc_tsw` and its body is hidden** — whether it validates the owner is
  **[Unverified]**, though it looks like the SMS-messaging package.
- Active flows on Contact: only `clear_recordType_related` (scheduled). It does not read the owner.
- **`OwnerId` on Contact is not field-history tracked.** `ContactHistory` cannot tell who changed
  the owner or when.

## 2. Access model

- Opportunity and Account OWD are **Private**. Contact is **Controlled by Parent**, so Contact
  access rides on Account access, not on Opportunities. Owning a Contact never requires an Opp.
  (`EntityDefinition.InternalSharingModel` reports Contact as "Private" — it is wrong for Contact;
  see `ORG_REFERENCE.md` gotcha on that. Trust the Sharing Settings UI.)
- `Contact.Contact_All_Internal_Read` sharing rule exists with **Edit** access for all internal
  users. Dormant while Contact stays Controlled by Parent [Likely]; it would take effect if the
  Contact OWD is ever changed. Tracked in `AUTOMATION_INVENTORY.md` §7.2.
- A closed Opportunity (Closed Won / Closed Lost) cannot be modified except by a System
  Administrator (`Prevent_Changes_Closed_Opportunity`). Closing a duplicate is therefore not
  reversible for an agent. Deleting an Opportunity sends it, and its Tasks, to the Recycle Bin
  (about 15 days to undelete).

## 3. How a Contact is created

- Most Contacts come from **lead conversion**: in the 90 days to 2026-10-01 there were 1,280
  conversions and 1,741 new Contacts. [Verified] The numbers do not match one-to-one, so there are
  other paths.
- Other paths: created by hand by an agent, created by `sf integrations`, and the stub Contact
  created by `EmailMessageStubContactCreator` so inbound replies are captured.
- A **new** Contact is owned by whoever creates it, or by the owner chosen at conversion.
- **Converting a Lead against an existing Contact does not change that Contact's owner** (standard
  Salesforce behaviour; org conversion settings below do not override it [Likely]). The conversion
  can create a new Account and a new Opportunity without aligning the existing Contact's owner or
  Account with them.

## 4. Lead Settings (conversion) — prod, 2026-10-01 [Verified]

From Tooling API `LeadConvertSettings`:

| Setting | Value |
|---|---|
| `allowOwnerChange` | `true` — the person converting can choose the owner of the records created |
| `opportunityCreationOptions` | `VisibleOptional` — creating the Opportunity is optional on the convert screen |
| Field mappings | Lead→Account 1 field, Lead→Contact 16, Lead→Opportunity 160 |

There is no setting that forces reuse of the existing Account or Contact, or that aligns the
Contact owner with the Opportunity owner.

## 5. Duplicate handling

**Duplicate rules** [Verified 2026-10-01]: only `Account.Standard_Account_Duplicate_Rule` is
active (Allow on create and edit, per `AUTOMATION_INVENTORY.md` §4.3). All Contact and Lead
duplicate rules are inactive, including `Contact_Duplicate_Rule_by_email`, the only one that
would Block (on edit).

**Matching rules**: Contact matches on **email only**; Lead on email + `Branch__c`; Account on
`NMLS_Company__c`. **No matching rule uses phone.**

**The real Lead dedupe is Apex**: `DetectDuplicateHandler` (class body read live 2026-10-01),
with the flow `not_allow_to_create_non_borrowers_leads` (see `AUTOMATION_INVENTORY.md`).

- Runs when a **Lead** is saved. Compares the incoming Lead with unconverted Leads and with
  Opportunities by **email OR phone**, in the same `Branch__c` and record type. Realtor Leads are
  compared without the branch filter.
- Skips Leads with no `Branch__c`, Leads already Discarded as `Duplicate Lead`, and record type
  `SiMo_BPO` (intentional clones; see `CloneMMIToSimoBPO`).
- On a match it renames the Lead with the suffix `-(DUPLICATE)`, sets it to Discarded and swaps
  field values with the original. That is where `-(DUPLICATE)` leads come from.
- Phones that exist on an Account are filtered out for non-borrower leads, so company numbers do
  not trigger it.
- Inactive-owner guard (patch 2026-08-05): an inactive owner falls back to `Team Marketing city`,
  then `sf integrations`. Those Ids are hard-coded in the class and in the flow
  `change_owner_to_duplicate_leads_no_borrowers`.
- **It does not run** when an Opportunity is created by hand, when a Contact is created, or when
  a Lead is converted against an existing Contact.
- **[Unverified]** whether it checks Realtor-type Opportunities (the code mixes Lead and
  Opportunity record-type Ids; not traced to the end), and which trigger calls it
  (`Body` cannot be filtered in a Tooling query).

## 6. Open questions for Business Development

1. Must a Realtor Contact's owner always be the owner of its active Opportunity? Exceptions?
2. May an agent hold a Contact they do not own an Opportunity for? For how long?
3. Who may reassign a Contact: any agent, or only a manager?
4. On converting a Lead against an existing Contact: whose ownership wins, and does the
   Opportunity go under the Contact's Account or a new one?
5. Should an active Contact duplicate rule include phone? Today only the email rule exists, and it
   is inactive.
6. Should duplicate checks cover manual Opportunity and Contact creation, not only Leads?

Options on the table: **A** change nothing · **B** remove Modify All on Contact from `Agent
Sales` · **C** block, on save, a Contact owner who has no Opportunity of that contact · **D**
periodic report of Contacts whose owner has no Opportunity of theirs. Not chosen yet.

## 7. Not measured

How many Contacts currently have an owner with no Opportunity of that contact. Run a count
before choosing B or C.

## 8. Prod changes made while investigating (2026-10-01)

Done with explicit confirmation, on `--target-org prod`:

| What | Record | Result |
|---|---|---|
| Deleted a duplicate Realtor Opportunity | `006Kb00000KuswtIAB` | In the Recycle Bin, with its 12 Tasks. Backup of the Opportunity, its Tasks and contact role is in the git-ignored `data/dup-opp-2026-10-01/`. |
| Kept the other Opportunity | `006Qg00000dwt0tIAA` | Untouched: Proposal, 34 Tasks. |
| Contact owner set to the owner of the kept Opportunity | Contact `003Kb00001XmSs0IAF` | Verified by re-read. |
| Contact moved to the kept Opportunity's Account | `AccountId = 001Qg00000GPYrhIAH` | Verified by re-read; the old Account stays as an indirect relation. |

Still open: whether to re-parent the 12 deleted Tasks to the kept Opportunity (they are only
recoverable from the Recycle Bin until it expires), and why the call integration logged activity
on the older Opportunity.
