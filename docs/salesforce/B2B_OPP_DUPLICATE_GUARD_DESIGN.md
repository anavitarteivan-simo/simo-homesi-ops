# B2B Opportunity duplicate guard (rules A + B) — design only

**Status: DESIGN ONLY. Nothing is built or deployed.** It waits for the Business Owner's answers
to the questions in section 9. Drafted 2026-10-01. Background and evidence:
`salesforce/CONTACT_OWNERSHIP_AND_DEDUP.md`.

## 1. Goal

Stop an agent (or a lead conversion) from creating a **second open B2B Opportunity** for the same
person when one is already open. Only blatant cases: no fuzzy matching, no name matching.

## 2. Scope

| In scope (Opportunity record types) | Id |
|---|---|
| Realtor | `012Kb000000RpDHIA0` |
| Broker | `012Kb000000RpDFIA0` |
| Loan Officer | `012Kb000000RpDGIA0` |

Out of scope: Borrower, and **SiMo BPO** (`012Qg000003xvgUIAQ`) — its Opportunities are intentional
copies and must never be treated as duplicates (same reason `DetectDuplicateHandler` excludes it).
Ids read from prod 2026-10-01; re-read before building.

## 3. The rule

An Opportunity **O** of an in-scope record type is a duplicate when another Opportunity **X**
exists with all of:

- `X.Id != O.Id`
- `X.RecordTypeId = O.RecordTypeId` (same type only)
- `X.IsClosed = false`
- **and either**
  - **Rule A:** `lower(trim(X.Email__c)) = lower(trim(O.Email__c))` **and** the last 10 digits of
    `X.Phone__c` = the last 10 digits of `O.Phone__c` (both fields must be populated on both), **or**
  - **Rule B:** X and O have the same **primary** `OpportunityContactRole` Contact.

Not covered on purpose: email alone, phone alone, name (shared phones/emails and common names
would create false positives).

## 4. When it evaluates

- On **insert** of O, and on **update** only when `Email__c`, `Phone__c` or `RecordTypeId` change.
- When a **primary OpportunityContactRole** is created, or its `IsPrimary` / `ContactId` changes
  (Rule B). The contact role is created *after* the Opportunity, so Rule B cannot run on the
  Opportunity insert.
- It must **not** fire on any other edit. 116 Opportunities are already duplicated (58 pairs), and
  an unrelated edit to one of them must keep working.
- Rule A on lead conversion: `Send_data_to_Opp_when_Lead_is_converted` fills `Email__c` and
  `Phone__c` *after* the Opportunity is inserted, so the check has to run on that update, not on
  the insert [Unverified — confirm in staging].

## 5. Action (decision needed — section 9)

Two modes, switchable without a deploy:

- **Block:** the save fails with a message such as *"There is already an open [type] opportunity
  for this person. Work that one, or ask a manager."* On a lead conversion this fails the whole
  conversion transaction [Unverified — confirm in staging], and the agent must work the existing
  Opportunity.
- **Warn:** the save succeeds and the match is recorded (a field or a task for a manager) for
  review.

Open point: the Opportunity object is Private. If the message shows the other Opportunity's Id or
owner, it discloses a record the agent may not be able to see. Decide whether the message shows
the owner's name, the Id, or neither.

## 6. Exceptions and bypass

- A **custom permission** (proposed `Bypass_B2B_Duplicate_Guard`) for managers and admins.
- Integration users keep their existing paths; confirm they are not blocked unintentionally.
- X is ignored when it is **closed** (Closed Won / Closed Lost). Creating a new Opportunity after
  one was lost is legitimate. 2 of the 58 known pairs were like this.
- Bulk saves (Data Import Wizard, integrations) must be bulk-safe and also compare the records
  inside the same batch against each other.

## 7. Expected effect (measured on the 58 known pairs, prod, 2026-10-01)

In 56 of 58 pairs the older Opportunity was open when the newer one was created; in 2 it was
Closed Lost.

| Rule | Pairs it would have blocked (of the 56) |
|---|---|
| A (email + phone) | 50 |
| B (same primary contact) | 26 |
| A or B | **56** |

39 of the 58 newer Opportunities were created by a lead conversion; 19 in other ways. None of the
8 most frequent creators (50 of 58) is an integration. Whether each pair is a true duplicate was
**not** checked one by one; they are matched on type + email/phone/contact.

## 8. Build and release notes (for later)

- Opportunity already has several triggers (`OpportunityTrigger`, `OpportunityDataQualityTrigger`,
  `SyncLoanOfficerText`, `OpportunityCoOwnerSharing`, `OpportunityAccountExecutiveOwner`).
  Whether to add a handler to an existing one or a new trigger is **[Unverified]**; trigger order is
  not guaranteed.
- A flow variant must filter entry criteria on `RecordTypeId` + the Id, never
  `RecordType.DeveloperName` (see `PROD_OUTAGE_RCA_2DAY.md`). Read gotchas #21–#31 in
  `ORG_REFERENCE.md` first.
- A kill switch for the guard (Off / Warn / Block) in a Custom Setting or Custom Metadata, separate
  from the two existing kill switches, which must not be touched.
- Staging first (`homesi-staging`), then prod from merged `main`, through a PR (`CHANGE_POLICY.md`).
- Staging holds none of the records involved, so tests need seeded data.

## 9. Decisions needed from the Business Owner

1. Block or warn? If block, for everyone or only agents?
2. Can one realtor/broker/loan officer legitimately have **two open Opportunities of the same
   type**? If yes, which cases, and the rule must allow them.
3. Who gets the bypass permission?
4. What must the agent see and do when blocked (message text, who to ask)?
5. What happens to the 58 existing pairs: who decides which Opportunity stays (cleanup precedes the
   rule, or the rule starts in Warn mode)?
6. Should Rule B be included, or only Rule A first?

## 10. Test plan (staging, with seeded data)

| Case | Expected |
|---|---|
| New Realtor Opp, same email + phone as an open Realtor Opp | Blocked / warned |
| Same email + phone, but the existing Opp is Closed Lost | Allowed |
| Same email + phone, different record type | Allowed |
| Same email only, or same phone only | Allowed |
| Same primary contact, same type, existing open | Blocked / warned |
| Lead conversion creating the duplicate | Conversion fails / warns |
| Unrelated edit on an already-duplicated Opp | Succeeds |
| SiMo BPO clone | Allowed |
| User with the bypass permission | Allowed |
| 200 Opps loaded in one batch, some duplicating each other | Duplicates inside the batch caught; no governor-limit failure |

## 11. Rollback

Set the kill switch to Off. If a deploy goes wrong, redeploy the previous trigger/flow version from
the last good `main`. Verify afterwards by saving an open Realtor Opportunity in prod and
re-reading it.
