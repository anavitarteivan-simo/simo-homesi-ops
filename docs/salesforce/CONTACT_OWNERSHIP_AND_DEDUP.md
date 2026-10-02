# Contact ownership, lead conversion and duplicate handling

Why can someone own a Contact without owning any Opportunity of that contact, and what does
(and does not) stop duplicate Contacts / Accounts / Opportunities? Findings from live reads of
**prod** (`--target-org prod`, org `00DKb000000OvoRMAS`). Nothing was changed to produce them.

Tags: **[Verified]** read live on the date shown · **[Likely]** strong inference ·
**[Unverified]** not checked.

Raised 2026-10-01 after Production reported a duplicate Opportunity. A summary for Business
Development is in `reports/2026-10-02-owner-contact-sin-opportunity.pdf` (see
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
- **Correction 2026-10-01:** an earlier version of this file said a closed Opportunity can only be
  edited by a System Administrator. That is **wrong**: the validation rule
  `Prevent_Changes_Closed_Opportunity` exists but is **inactive** in both prod and `homesi-staging`
  (prod rule last modified 2025-05-14) [Verified]. Its formula would exempt System Administrators, but it does
  not run. `AUTOMATION_INVENTORY.md` §4.1 lists it with Active = no.
- Moving a closed Opportunity backwards is reverted by the flow `Reset_stage_by_hierarchy`, per
  `AUTOMATION_INVENTORY.md` [not re-verified live].
- Deleting an Opportunity sends it, and its Tasks, to the Recycle Bin (about 15 days to undelete).

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

## 9. B2B duplicate Opportunity cleanup, owners no longer in the company (2026-10-02)

Requested by the business after the 2026-10-01 report. Done with explicit confirmation on `--target-org prod`.

**Scope.** Strong pairs only (open Opportunities of the same B2B record type sharing at least two of contact, email and
phone), recomputed from live data. Rule: when exactly one owner of a pair is one of the users reported as gone
(**Andres Zorro, Danika Piragua, Jairo Sanjuan, Samuel Tirado, Victor Fuentes**, all inactive in Salesforce), delete that
Opportunity and keep the other. **Camilo Delgado Uribe and Elias Yaber were excluded**: both users are still **active**
(System Administrator profile) and Camilo logged in on 2026-10-01 [Verified]; their pairs wait for confirmation. The
decision on history was "delete like the first cleanup": Tasks go with the Opportunity (no re-parenting).

| What | Result |
|---|---|
| Opportunities deleted | **20** (Andres Zorro 5, Danika Piragua 8, Jairo Sanjuan 3, Samuel Tirado 4, Victor Fuentes 1). All in the Recycle Bin (about 15 days). Re-read: 0 live, 20 deleted. |
| Tasks that went with them | 345 (302 by agents, 43 Customer.io events) |
| Kept Opportunities | 20; owner, stage and account unchanged vs the backup |
| Contacts aligned with the kept owner | **7** owner changes (one also moved Account); re-read: 7 of 7 as intended |
| Not aligned | 4 pairs whose kept Opportunity has no primary contact role, so the contact was left alone |
| Pairs left | **38** of 58, listed in `reports/2026-10-02-oportunidades-b2b-duplicadas-restantes.pdf` with each Opportunity's last agent contact |

**Caution recorded at the time.** In 16 of the 20 pairs the deleted Opportunity had **more agent Tasks** than the kept one (302 agent
Tasks in total, one Opportunity with 83), and in 8 of the 20 it was **further along** in stage. The business chose to
keep the active owner's Opportunity regardless. The Tasks are recoverable only from the Recycle Bin, plus the local
backup (git-ignored, may hold PII) in `data/dup-opp-cleanup-2026-10-02/`.

**Open.** Camilo Delgado Uribe and Elias Yaber are described as having left but are active System Administrators;
this is an access-review item for the Salesforce admins, not part of this cleanup. The 38 remaining pairs need the
business to decide per pair (the report shows the last contact).


### 9.1 Plan for the 38 remaining pairs (written 2026-10-02, **not executed**; resume when the business answers)
Salesforce cannot merge Opportunities (only Leads, Contacts and Accounts). Resolving a pair means keeping one
Opportunity, moving its history to it, and deleting or closing the other. Unlike the first two cleanups, this plan
**re-parents the Tasks** of the Opportunity that goes away to the one that stays, so no agent history is lost.

**A. Pairs with the same active owner (7). The owner is the same, so there is no ownership conflict.**
| Owner | Keep | Drop | Why |
|---|---|---|---|
| Josue Toro | `006Qg00000NvGlxIAF` (22 agent Tasks) | `006Qg00000WcY9XIAV` (2) | more history; same Account |
| Josue Toro | `006Kb00000KusvgIAB` (15) | `006Qg00000QJ3ODIA1` (0, Qualification) | the other is empty |
| Giovanni Osorio | `006Kb00000Kusw4IAB` (11) | `006Qg00000qX5UPIA0` (0, Needs Analysis) | the other is empty |
| Giovanni Osorio | `006Qg00000QxFyXIAV` (10) | `006Qg00000qk0NGIAY` (1, Qualification) | more history, further along |
| Annie Garrido | `006Qg00000Lrtn3IAB` | `006Qg00000XkbJKIAZ` | same Task count; the first has the latest contact |
| Annie Garrido | `006Qg00000KPdihIAD` (15) vs `006Qg00000g7ys7IAA` (6, latest contact) | **the owner decides** | both Negotiation |
| Belkys Armesto | `006Qg00000Of9PjIAJ` vs `006Qg00000nyVazIAE` | **the owner decides** | one is further along, the other has the latest contact |
The first five rows are clear suggestions by stage and last agent contact; they still need the go-ahead.

**B. Pairs with an inactive owner (3).** Danika Piragua with Samuel Tirado (`006Qg00000QMcdyIAD`, `006Qg00000XgxtVIAR`) and Samuel
Tirado with Victor Fuentes (`006Qg00000VCSJhIAP`, `006Qg00000XgeMEIAZ`): both owners are inactive, so first decide **which
active agent takes the Opportunity that stays**. Danika with Camilo Delgado Uribe (`006Qg00000eDGHdIAO`, `006Kb00000KuszjIAB`)
and Elias Yaber with Josue Toro wait for the confirmation that Camilo and Elias have left (both users are still active).

**C. The other 27 pairs** have two different active owners: the business picks the Opportunity to keep (the report shows
the last agent contact), and the same procedure applies.

**Procedure per pair (staging does not apply: data in prod).**
1. Re-read both Opportunities live (open, owner, stage unchanged since the report).
2. Back up both Opportunities, their Tasks and contact roles to the git-ignored `data/`.
3. Re-parent the agent Tasks from the dropped Opportunity to the kept one (decide separately about the Customer.io event
   Tasks, which the storage plan will remove anyway) and, when the primary contacts differ, add the dropped one's contact as an
   extra role on the kept Opportunity.
4. Delete the dropped Opportunity (Recycle Bin, about 15 days).
5. Align the contact owner (and Account) with the kept Opportunity, as in section 9.
6. Re-read and confirm: dropped = deleted, kept = unchanged except the added Tasks, Task counts add up.
7. Update this section and the report; every change through a PR.

**Separate item, not part of the cleanup:** Camilo Delgado Uribe and Elias Yaber are described as having left but are active
System Administrators; this is an access review for the Salesforce admins.
