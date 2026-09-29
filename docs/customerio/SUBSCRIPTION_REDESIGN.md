# Customer.io → Salesforce Prod — Subscription Redesign (DRAFT)

**Status:** EXECUTED 2026-05-21 — all 14 subscriptions are live on destination `52375`. See section 9 for as-built IDs.
**Date:** 2026-05-21
**Scope:** Customer.io destination "Salesforce Prod" (destination ID `52375`), workspace `164380`.

---

## 1. What this draft covers

Two requested changes:

1. **On Email Unsubscribed**, besides creating the Task, also update the **Email Opt Out** field on the recipient record.
2. **Emails sent to Opportunity-based recipients** should create a Task linked to the **Opportunity** (instead of failing).

Both changes are blocked by the same underlying issue, so this draft addresses them together.

---

## 2. The problem (diagnosis)

The Salesforce → Customer.io syncs on source **"Salesforce Prod" (`34098`)** both write the Salesforce record `Id` into the **same** Customer.io identifier (`user_id`):

| Source sync | Salesforce object | `identifiers.user_id` | Also stored as |
|---|---|---|---|
| Lead sync (`503`) | Lead | `Id` (e.g. `00Q…`) | attribute `LeadId` |
| Opportunity sync (`623`) | Opportunity | `Id` (e.g. `006…`) | attribute `OpportunityId` |

So a Customer.io profile's `id` is **either** a Salesforce Lead Id **or** an Opportunity Id — both live in the same identifier namespace.

The six current Task subscriptions blindly copy that id into the Salesforce Task field **`WhoId`**:

```
"WhoId": { "@path": "$.properties.userId" }
```

`WhoId` only accepts a **Contact or Lead**. When the recipient came from an Opportunity, `WhoId` receives an Opportunity Id (`006…`) and Salesforce rejects the whole Task:

```
errorCode: FIELD_INTEGRITY_EXCEPTION
field:     WhoId
message:   "Name ID: id value of incorrect type: 006Qg00000jDsWxIAK"
status:    400
```

**This is happening now.** Destination `52375` shows a continuous stream of HTTP 400 errors (`ERRORS_DISCARDED_400`) — 100+ in the recent window. Today, emails to Opportunity recipients create **no Task at all**; they silently fail.

The fix: route by record type. An Opportunity Id belongs in **`WhatId`** (which accepts Opportunities), not `WhoId`.

---

## 3. Salesforce fields confirmed (read from Salesforce Prod)

The "Email Opt Out" field exists on **both** objects involved:

| Object | Field API name | Label | Type |
|---|---|---|---|
| Lead | `HasOptedOutOfEmail` | Email Opt Out | Checkbox (standard) |
| Opportunity | `HasOptedOutOfEmail__c` | Email Opt Out | Checkbox (custom) |

Both are the standard "Email Opt Out" checkbox. Setting `HasOptedOutOfEmail` on a Lead also tells Salesforce's own engine to stop emailing that record.

---

## 4. Can we add filters to an event? — Yes

Every subscription has a **Filter / Trigger** (the `subscribe` field). Today it only matches the event type, e.g.:

```
type = "track" and event = "Email Unsubscribed"
```

It can be extended with additional conditions on any field in the event payload. We will use it to split each event into a **Lead branch** and an **Opportunity branch** based on the prefix of `properties.userId`:

- Lead Ids start with **`00Q`**
- Opportunity Ids start with **`006`**

The first three characters of a Salesforce Id are a fixed object-type prefix, so this is a reliable discriminator. It is the *only* discriminator available — the email-metric event payload carries just the ids (`userId`, `customer_id`, `delivery_id`, `subject`, etc.) and no record-type trait.

> **Confirmed in Customer.io's documentation.** The Trigger uses Customer.io's Filter Query Language (FQL), which includes a `match( string, pattern )` function. `match` does **glob** matching and returns true only on a **full-string match** — so `match( properties.userId, "006*" )` is true exactly when `userId` begins with `006`. The full-match requirement anchors the pattern to the start automatically; no regex `^` is needed (and `^` would *not* work — glob treats it as a literal character). Glob matching is case-sensitive, which is fine here because `006` is numeric.
>
> - **Opportunity branch:** `match( properties.userId, "006*" )`
> - **Lead branch:** `!match( properties.userId, "006*" )` — the `!` negation catches everything that is not an Opportunity (i.e. Leads, prefix `00Q`).
>
> Source: Customer.io Docs, "Action triggers: code mode" — https://docs.customer.io/integrations/data-out/action-trigger-syntax/

---

## 5. Proposed design

Each of the 6 email events is split into a Lead branch and an Opportunity branch. Email Unsubscribed additionally gets an opt-out field update on each branch. Result: **14 subscriptions** on destination `52375` (6 existing, modified; 8 new).

| Event | Lead branch (`!match …006*`) | Opportunity branch (`match …006*`) |
|---|---|---|
| Email Sent | Task — `WhoId` *(modify existing)* | Task — `WhatId` *(new)* |
| Email Opened | Task — `WhoId` *(modify existing)* | Task — `WhatId` *(new)* |
| Email Link Clicked | Task — `WhoId` *(modify existing)* | Task — `WhatId` *(new)* |
| Email Marked as Spam | Task — `WhoId` *(modify existing)* | Task — `WhatId` *(new)* |
| Email Failed | Task — `WhoId` *(modify existing)* | Task — `WhatId` *(new)* |
| Email Unsubscribed | Task — `WhoId` *(modify existing)* **+** Lead opt-out update *(new)* | Task — `WhatId` *(new)* **+** Opportunity opt-out update *(new)* |

"Modify existing" = the only change to the 6 current subscriptions is adding the Lead-branch filter to their trigger. Their mappings stay as-is.

---

## 6. Subscription configs

Four reusable templates. The `subscribe` (Trigger) strings below are valid FQL — paste them into the action's **Code mode**, or build the equivalent in the visual editor.

### Template A — Task on Lead (`WhoId`) — *modifies the 6 existing subscriptions*

Only the trigger changes; append the Lead-branch condition:

```
type = "track" and event = "<EVENT>" and !match( properties.userId, "006*" )
```

Mapping is unchanged from today, e.g. Email Sent:

```json
{
  "operation": "create",
  "recordMatcherOperator": "OR",
  "enable_batching": false,
  "traits": {},
  "bulkUpsertExternalId": { "externalIdName": "", "externalIdValue": "" },
  "bulkUpdateRecordId": "",
  "customObjectName": "Task",
  "customFields": {
    "WhoId": { "@path": "$.properties.userId" },
    "Subject": { "@path": "$.properties.subject" },
    "OwnerId": "005Kb00000B1ZEtIAN",
    "TaskSubtype": "Email",
    "ActivityDate": { "@path": "$.timestamp" }
  }
}
```

### Template B — Task on Opportunity (`WhatId`) — *6 new subscriptions*

Trigger:

```
type = "track" and event = "<EVENT>" and match( properties.userId, "006*" )
```

Mapping — identical to Template A **except `WhoId` becomes `WhatId`**:

```json
{
  "operation": "create",
  "recordMatcherOperator": "OR",
  "enable_batching": false,
  "traits": {},
  "bulkUpsertExternalId": { "externalIdName": "", "externalIdValue": "" },
  "bulkUpdateRecordId": "",
  "customObjectName": "Task",
  "customFields": {
    "WhatId": { "@path": "$.properties.userId" },
    "Subject": { "@template": "Email Opened - {{properties.subject}}" },
    "OwnerId": "005Kb00000B1ZEtIAN",
    "TaskSubtype": "Email",
    "ActivityDate": { "@path": "$.timestamp" }
  }
}
```

Per-event `Subject` value (same as the current Lead-branch subscriptions):

| Event | `Subject` |
|---|---|
| Email Sent | `{ "@path": "$.properties.subject" }` |
| Email Opened | `{ "@template": "Email Opened - {{properties.subject}}" }` |
| Email Link Clicked | `{ "@template": "Email Link Clicked - {{properties.subject}}" }` |
| Email Unsubscribed | `{ "@template": "Email Unsubscribed - {{properties.subject}}" }` |
| Email Marked as Spam | `{ "@template": "Email Marked as Spam - {{properties.subject}}" }` |
| Email Failed | `{ "@template": "Email Failed - {{properties.failure_message}}" }` |

### Template C — Lead "Email Opt Out" update — *1 new subscription*

- Event: **Email Unsubscribed**, Lead branch
- Action: **Lead** (`lead`)

Trigger:

```
type = "track" and event = "Email Unsubscribed" and !match( properties.userId, "006*" )
```

Mapping:

```json
{
  "operation": "update",
  "recordMatcherOperator": "OR",
  "enable_batching": false,
  "traits": { "Id": { "@path": "$.properties.userId" } },
  "customFields": { "HasOptedOutOfEmail": true }
}
```

`traits` is the record matcher — here it locates the Lead by its Salesforce `Id` (which is what `userId` is). `customFields` then sets the Email Opt Out checkbox.

### Template D — Opportunity "Email Opt Out" update — *1 new subscription*

- Event: **Email Unsubscribed**, Opportunity branch
- Action: **Opportunity** (`opportunity`)

Trigger:

```
type = "track" and event = "Email Unsubscribed" and match( properties.userId, "006*" )
```

Mapping:

```json
{
  "operation": "update",
  "recordMatcherOperator": "OR",
  "enable_batching": false,
  "traits": { "Id": { "@path": "$.properties.userId" } },
  "customFields": { "HasOptedOutOfEmail__c": true }
}
```

---

## 7. Decisions & remaining items

1. **Prefix match — RESOLVED.** Customer.io's FQL `match( properties.userId, "006*" )` performs glob, full-string matching, so it reliably means "begins with `006`". The templates above use it. (Verified against Customer.io's "Action triggers: code mode" docs.)
2. **`OwnerId` — RESOLVED.** Opportunity-branch Tasks keep the same hardcoded owner used today: Salesforce user `005Kb00000B1ZEtIAN`.
3. **Checkbox value type — TEST DURING ROLLOUT.** Templates C/D set the "Email Opt Out" checkbox to JSON boolean `true`. Start with `true`; if the Salesforce connector rejects it, switch to the string `"true"`. This gets verified with a test event before the subscriptions go live (rollout step 4).
4. **Opportunity Task `WhoId` — RESOLVED: `WhatId` only.** Opportunity-branch Tasks link to the Opportunity via `WhatId` and leave `WhoId` empty. No person linkage.
5. **Subject typo — RESOLVED.** The current Email Unsubscribed subscription has a double space (`"Email Unsubscribed  -"`); it will be corrected to a single space when that subscription is updated during rollout.
6. **Other Salesforce destinations — to be removed.** Destinations `13908` ("Salesforce", disabled, 2 stale subscriptions) and `13990` ("Salesforce", enabled, 0 subscriptions) will be deleted. **Deleting a destination is permanent and must be done by you** in the Customer.io UI (Data Pipelines → Destinations) — it is a destructive action that cannot be performed on your behalf.

---

## 8. Suggested rollout

1. In one action's **Code mode**, paste the FQL Trigger and use the **Tester** tab to confirm an Opportunity `userId` (`006…`) matches and a Lead `userId` (`00Q…`) does not.
2. Add the 8 new subscriptions (Templates B ×6, C ×1, D ×1) **disabled**.
3. Add the Lead-branch filter to the 6 existing subscriptions.
4. Use the destination's **Send test event** with a sample `006…` `userId` to confirm the Opportunity Task creates and the Opportunity opt-out update sets the checkbox. This is also where the checkbox value (boolean `true` vs string `"true"` — item 3) gets verified.
5. Enable the 8 new subscriptions.
6. Watch the destination error count — `ERRORS_DISCARDED_400` should fall to zero as Opportunity events stop hitting `WhoId`.

---

## 9. As-built — executed 2026-05-21

All 14 subscriptions are live on destination `52375` ("Salesforce Prod").

**Existing — modified** (Lead branch, `!match(...006*)`, `WhoId`, enabled):

| ID | Event |
|---|---|
| 182232 | Email Sent |
| 342652 | Email Opened |
| 343605 | Email Unsubscribed (Subject typo fixed) |
| 343606 | Email Link Clicked |
| 343607 | Email Marked as Spam |
| 343608 | Email Failed |

**New — created** (Opportunity branch + opt-outs, `match(...006*)`, enabled):

| ID | Name | Event | Action |
|---|---|---|---|
| 712640 | Custom Object (Opportunity) | Email Sent | customObject → `WhatId` |
| 712641 | Custom Object (Opportunity) | Email Opened | customObject → `WhatId` |
| 712642 | Custom Object (Opportunity) | Email Link Clicked | customObject → `WhatId` |
| 712643 | Custom Object (Opportunity) | Email Marked as Spam | customObject → `WhatId` |
| 712644 | Custom Object (Opportunity) | Email Failed | customObject → `WhatId` |
| 712645 | Custom Object (Opportunity) | Email Unsubscribed | customObject → `WhatId` |
| 712646 | Lead Email Opt Out | Email Unsubscribed | lead → `HasOptedOutOfEmail` |
| 712647 | Opportunity Email Opt Out | Email Unsubscribed | opportunity → `HasOptedOutOfEmail__c` |

**Pending verification** (needs live traffic to flow): confirm Opportunity events now succeed (no more `FIELD_INTEGRITY_EXCEPTION` on `WhoId`) and that the opt-out updates set the checkbox — this is where the boolean `true` vs string `"true"` value (item 3) gets confirmed.

**Still to do by you:** delete stale destinations `13908` and `13990` (section 7, item 6 — permanent deletion must be done by you in the Customer.io UI).
