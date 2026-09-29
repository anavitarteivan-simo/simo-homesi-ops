# CLAUDE.md — Homesi / Simo Solutions Group: Salesforce + Customer.io

Operating context for work across the Homesi Salesforce org and the Customer.io
(Journeys + Pipelines) workspaces. Written 2026-08-25. Facts below were verified
against live APIs unless marked otherwise.

Confidence tags used throughout: **[Verified]** read from a live API this session,
**[Likely]** strong inference, **[Unverified]** assumption worth re-checking.

---

## 1. Systems

### Salesforce

| Alias | Username | Instance | Notes |
|---|---|---|---|
| `prod` | m.rodriguez@supremelending.com | ruby-ruby-7485.my.salesforce.com | Org ID `00DKb000000OvoRMAS`. Company name on the user record is **Homesi**. This is the org that matters. |
| `homesi-staging` | m.rodriguez@supremelending.com.staging | ruby-ruby-7485--staging.sandbox.my.salesforce.com | Org ID `00DEm000008XXK7MAO`. Currently the `target-org` default — **do not assume the default is prod**. |

Two Salesforce MCP servers are usually mounted. Check `getUserInfo` on each before
querying: the one returning `companyName: "Homesi"` is prod, the other is staging.

### Customer.io

| Workspace (environment) ID | What it is |
|---|---|
| `164380` | **Homesi** Journeys workspace. ~180,580 profiles. Salesforce-synced. All work below refers to this one unless stated. |
| `224311` | **Simo Solutions Group** Journeys workspace. 35,548 profiles. Receives only SiMo BPO record-type records. Lead sync here is **healthy** — see §4.5. |

**Neither workspace has any custom events configured.** `GET /event_names` returns
an empty array for both. All segmentation is attribute-based on Salesforce-synced
fields. Only built-in message events (`opened_email`, `bounced_email`, etc.) exist.
If someone refers to "the events we configured," ask what they mean — as of
2026-08-25 there are none.

Pipelines objects in workspace 164380:

| Object | ID | Name |
|---|---|---|
| Source | `34098` | Salesforce Prod (`option_id: salesforce`) |
| Source | `27714` | Journeys Message Metrics |
| Source | `27715` | Journeys API: City Lending |
| Source | `164564` | Journeys API: Supremelending |
| Source | `167540` | Dashboard Daniella Ottone (`http`) |
| Destination | `13465` | Journeys Workspace (`customerio`, siteId `e6430e236427e1f4373d`) |
| Destination | `52375` | Salesforce Prod |
| Connection | `19589` | Source 34098 → Destination 13465 |
| Sync | `503` | "Lead sync" — pull, 1800s, `cdp_type: identify`, `user_id -> Id`, 71 fields |
| Sync | `623` | "Opportunity sync" — pull, 1800s, `cdp_type: identify`, `user_id -> Id`, 91 fields |

---

## 2. People

| Name | Salesforce User ID | Email | Role in this context |
|---|---|---|---|
| Melquiades Rodriguez | `005Kb00000B1HzJIAV` | m.rodriguez@supremelending.com | System Administrator. The operator. |
| Laura Betancourt | — (CIO user `530010`) | laura.garcia@supremelending.com | Builds Customer.io segments and campaigns. |
| Giovanni Osorio | `005Kb00000B1ZE0IAN` | giovanni.osorio@supremelending.com | Owns the Ottone lead book. Business Developer. |
| Javier Peñaloza | `005Kb00000B1ZDCIA3` | javier.penaloza@supremelending.com | Owns "Likely to Sell" leads, Branch 703. |
| Jorge Campodonico | `005Kb00000B1ZGWIA3` | — | On realtor webinar threads. |
| sf integrations | `005Qg00000C9srvIAB` | — | Integration user. Creates records automatically. |

---

## 3. Key Salesforce record IDs

### Lead record types

| Name | RecordTypeId | Notes |
|---|---|---|
| Borrower | `012Kb000000RpDAIA0` | Main consumer lead type |
| Broker | `012Kb000000RpDBIA0` | |
| Loan Officer | `012Kb000000RpDCIA0` | |
| Realtor | `012Kb000000RpDDIA0` | |
| **SiMo BPO** | `012Qg000003xvgTIAQ` | **Belongs to a different workspace.** Excluded from the 164380 Lead sync. ~35,700 records. Note the different key prefix (`012Qg` vs `012Kb`) — it was created much later. |

Opportunity SiMo BPO record type: `012Qg000003xvgUIAQ` (excluded from Opportunity sync).

### Useful Lead fields

- `Referred_By__c` — **lookup to Contact**, not a text field. This is the realtor/partner referral link.
- `Referred_Date__c`, `Referred_Info__c`, `Webinar_Referred_By__c` (text), `Referred_By_NPPM__c` (picklist)
- `Branch__c`, `Strategy__c`, `NPPM__c`, `Source__c`, `Recruitment_Segmentation__c`
- Alternate email fields: `email_temp__c`, `CoBorrower_Email__c`. There is **no** `Email__c` on Lead (there is on Opportunity).

### Daniella Ottone — duplicate contacts

| Contact ID | Email | Account | Created | Holds |
|---|---|---|---|---|
| `003Qg00000tY9lxIAC` | daniella.ottone@yahoo.com | NPPM 724 | Jun 1 2026 | **2,761 leads + 7 opportunities**, 3 tasks. Last activity Jul 14. |
| `003Qg00000wlGmMIAU` | theottonegroup@gmail.com | eXp Realty | Jul 17 2026 by `sf integrations` | 0 leads, but **3 tasks incl. the most recent activity** (Jul 28 NPPM strategy minutes). |

Same phone on both: 904-615-3825.

**Gotcha:** the record with zero leads is the one with the *live* relationship history.
"Zero referred leads" is not a test for emptiness — contacts carry tasks, events,
opportunities, and campaign members independently. Do not delete either; **merge**.

---

## 4. ACTIVE INCIDENT — Salesforce Lead sync into Customer.io is dead

**Status as of 2026-08-25: unresolved, escalated to Customer.io support.**

### Symptom
Lead sync 503 completes successfully on every run and emits valid identify events,
but **zero profiles are created in Journeys**. Opportunity sync 623 — same source,
same destination, same structure — works normally.

### Timeline
- **Last confirmed Lead sync into Journeys: 2026-06-30.** The Daniella Ottone bulk
  import (created Jun 29) landed as `00Q` profiles with `_created_in_customerio_at`
  around Jun 30. Nothing since.
- Every lead tested created on or after Jul 1 returns 404 in Customer.io.

### Evidence [Verified]

Single-record isolation test — filter narrowed to one lead:

```
RecordTypeId != '012Qg000003xvgTIAQ' AND Id = '00QQg00000m5OxLMAU'
```

- Salesforce validation: "1 records match your filter criteria"
- Run `32768355` (2026-08-24 20:28:52 UTC): 1 row processed, 0 failed, 0 suppressed, `complete`
- Source emitted a well-formed identify event:
  `messageId: 503:sync:164380:34098:503-2026-08-24T20:28:51Z:00QQg00000m5OxLMAU:1787581735000`,
  `userId: 00QQg00000m5OxLMAU`, 71 traits populated, `email: adgfsdgg@gmail.com`
- `GET /v1/environments/164380/customers/00QQg00000m5OxLMAU` → **404**

Full-volume runs behave identically:

| Run | Time (UTC) | Rows | Failed | Status |
|---|---|---|---|---|
| 32757114 | 18:00 | 191,990 | 0 | complete |
| 32768781 | 20:34 | 191,596 | 0 | complete |
| 32769670 | 20:46 | 192,174 | 0 | complete |

No Lead profiles created by any of them.

### Ruled out
Volume, timeouts, the SOQL filter, record-level permissions, sync enablement,
identifier mapping, `cdp_type`, field mapping, source auth, source health.
Recent sync-run errors: none (last failures were Jun 2025 and Oct 2025).

### Root cause: still unknown

**A `settings: null` hypothesis was raised and then disproved — do not repeat it.**
`GET /cdp/api/workspaces/164380/source_destination?source_id=34098` returns
connection `19589` with `settings: null`, and Customer.io docs say Salesforce →
Journeys connections require `settings.objects` object mappings. That looked like
the answer.

It isn't. Workspace 224311's connection `67931` **also** has `settings: null`, and
its Lead sync works fine (§4.5). `settings: null` is the normal state here, not a
defect. Two other facts it never explained: why Opportunities still flow through
the same connection, and why the break started at a specific date.

What the evidence actually supports: the Lead sync on source 34098 emits valid
identify events that the Journeys destination does not materialise, while the
Opportunity sync on the same source/destination pair works. That is a
Customer.io-side behaviour we cannot see into from the API. Escalate rather than
guess.

### Impact
~2,265 unconverted leads **with email addresses** created since Jul 1 are stranded
(1,427 Borrower, 497 Broker, 295 Realtor, 46 Loan Officer), plus eight weeks of
attribute updates on existing leads. Segment-triggered campaigns depending on Lead
data are silently starved.

### Do not
- Write `settings` to connection 19589 blind via API. Settings are **merged, not
  replaced**, the current value can't be read back, and 20 running campaigns depend
  on this connection. Note 224311 runs healthily with `settings: null`, so "filling
  in the object mappings" is not a known fix — it may make things worse.
- Leave a narrowed test filter saved. While `Id = '...'` is in place, **no other
  leads sync at all**. Restore string:
  ```
  RecordTypeId != '012Qg000003xvgTIAQ'
  ```

### Known-missing leads (good sync test records)

| Lead Id | Created | Email | Type |
|---|---|---|---|
| `00QQg00000m5OxLMAU` | Aug 24 | adgfsdgg@gmail.com | Borrower |
| `00QQg00000m1L0MMAU` | Aug 22 | danielvargasnunez@icloud.com | Borrower |
| `00QQg00000ly3CsMAI` | Aug 21 | oscarherrera1204@gmail.com | Borrower |
| `00QQg00000kwhV9MAI` | Jul 30 | heatheroathout@gmail.com | Borrower / Likely to Sell |

---

## 4.5 Workspace 224311 (Simo Solutions Group) — the control case

This workspace is the most useful diagnostic asset for the 164380 outage: same
Salesforce org, same connector type, mirrored config, **and its Lead sync works.**

### Configuration [Verified 2026-08-25]

| Object | ID | Detail |
|---|---|---|
| Source | `157352` | Salesforce Prod |
| Source | `156502` | Journeys Message Metrics |
| Source | `156503` | Journeys API: Simo Solutions Group |
| Destination | `343979` | Journeys Workspace |
| Connection | `67931` | 157352 → 343979. **`settings: null`** — same as the broken one. |
| Sync | `2082` **[Likely]** Lead | `cdp_type: identify`, `user_id -> Id`, 72 fields, `where_clause: RecordTypeId = '012Qg000003xvgTIAQ'` |
| Sync | `2083` **[Likely]** Opportunity | `cdp_type: identify`, `user_id -> Id`, 93 fields, `where_clause: RecordTypeId = '012Qg000003xvgUIAQ'` |

Sync-ID attribution is inferred from run ordering (Lead fires ~19s before
Opportunity, matching the 503/623 pattern in 164380). The `syncs` list endpoint
returns `null` for `id`, so this is not directly confirmable — verify in the UI
before acting on it.

Note the filters are the **exact inverse** of 164380's: this workspace takes only
SiMo BPO (`=`), the other excludes it (`!=`). Together they partition the org.

### Health [Verified]
- Salesforce holds **35,826** SiMo BPO leads, all created in one batch
  **2026-07-08 to 07-09**. Nothing created since.
- Workspace 224311 holds **35,548** profiles (subscribed: 35,145).
  Shortfall ~278 (0.8%) — **[Unverified]** cause, likely records without email.
- Spot check: Lead `00QQg00000jfbGdMAI` (SiMo BPO, created Jul 9) **is present**,
  `_created_in_customerio_at` Jul 9 2026. It synced the same day.
- Recent runs mostly show `total_rows: 0` — expected, because no new SiMo BPO
  records exist. Sync 2082 still picks up 1–2 changed rows periodically, most
  recently Aug 24. **It is alive, just idle.**

### Segments (8, all dynamic)
`1` All Users · `5` Unsubscribed · `6` Valid Email Address ·
`7` Invalid Email Address · `9` Doesn't have a Mobile Device ·
`16` Realtors - Leads · `18` Loan Officer - Leads · `19` Bounced - Email

Mostly Customer.io defaults. No custom event conditions — there are no custom
events in this workspace.

### Why this matters
Do not accept any explanation for the 164380 outage that would also predict
failure here. Anything true of both workspaces (`settings: null`, connector
version, identifier mapping, `cdp_type`, the Salesforce org, the OAuth
connection) is **not** the cause.

Real differences worth investigating: 164380's Lead sync carries **71** fields vs
72 here; its filter uses `!=` vs `=`; its volume is ~192,000 rows per full run vs
~35,000; and it shares a destination with three other sources rather than two.

---

## 5. Segments and campaigns worth knowing

### Segment 679 — "Daniella Ottone Active Leads" (static, 0 members)
Manual/static segment, `conditions: null`. Superseded. Kept only because campaign
125 history references it. **Static segments have no logic** — membership is an
explicit list written by import or `PUT .../segments/679/members`.

### Segment 685 — "Daniella Ottone - All Owned Leads (Status = New)" (dynamic, 650)
Built by Laura Betancourt. Conditions: `Referred_By__c = 003Qg00000tY9lxIAC`
AND `Status = New`. **Triggers campaign 125.**

### Segment 714 — "Javier Peñaloza - Lucio Romero - Likely to Sell (Aug 2026)" (dynamic, 0)
Four AND conditions:

| Attribute | Op | Value |
|---|---|---|
| `OwnerId` | eq | `005Kb00000B1ZDCIA3` (Javier Peñaloza) |
| `RecordTypeId` | eq | `012Kb000000RpDAIA0` (Borrower) |
| `LeadSource` | eq | `Likely to Sell` |
| `Branch__c` | eq | `703` |

The logic is correct — 450 leads match in Salesforce. It shows 0 **because of the
sync outage**, not because of the filter.

**Open question:** the name says "Lucio Romero" but the filter covers only Javier
Peñaloza. No user named Lucio Romero exists in the org. If his leads belong here,
condition 1 needs an `or`.

### Campaign 125 — "Borrowers - Daniella Ottone - Active Leads - July 2026"
`seg_attr` (segment-triggered), **running**, 20 actions (`1672`–`1691`).
Owned by Laura/Giovanni — **not ours to stop.**

Deliverability as last read: 3,199 sent / 2,524 delivered / 202 bounced /
27 unsubscribed / **5 spam complaints** / 1 click. Bounce rate ~6% overall and
20% on the first send; complaint rate approaching the ~0.3% threshold that
mailbox providers act on. This affects sender reputation for **every** campaign
in workspace 164380.

Audience quality: the 2,743 Ottone leads were bulk-created in a **43-second window**
on Jun 29. Only 738 have emails; none have city/state/zip. Names include
"Luis - Electricidad", "James- Appliances", "Ms Trouble - Good Guys Mc", and one
whose entire name is an email address — i.e. a phone contact list, not referrals.

### Workspace scale
32 campaigns total, **20 running**, all `seg_attr`.

---

## 6. GOTCHAS

### 6.1 Segment-triggered campaigns fire on entry
There are 20 running `seg_attr` campaigns. **Any resync, backfill, or bulk import
that pushes profiles into their segments sends email immediately** — no queue, no
review. A full resync also rewrites attributes on existing profiles, which can push
someone out of a segment and back in, re-triggering a campaign they already got.
Pause campaigns *before* large data operations.

### 6.2 Never match Customer.io profiles by email
Emails collide across old lead records, new lead records, and opportunity profiles.
Observed false positive: `oscarherrera1204@gmail.com` looked present, but the profile
was Lead `00QKb00000cV6fRMAS` from Jun 2024 — a different record from the Aug 2026
lead with the same address.

**Always match by Salesforce ID:**
```
GET /v1/environments/164380/customers/{SFID}?id_type=id
```
Profile ID prefixes: `00Q` = Lead, `006` = Opportunity, `003` = Contact.
A `006`-prefixed profile means the person synced as an Opportunity, not a Lead.

### 6.3 Customer.io segment type is immutable
Static cannot become dynamic. "Convert this segment to data-driven" always means
**create a new segment** and repoint whatever uses it. Segments in use by active
campaigns can't be deleted (422) or referenced by other segments when deleting (400).

### 6.4 Customer.io lowercases condition values on save
Sending `value: "003Qg00000tY9lxIAC"` reads back as `"003qg00000ty9lxiac"`.
Matching is case-insensitive so it still works — **verified**: the segment built and
matched 650 profiles. Report the read-back value, don't assume your input was stored.

Consequence: **do not reconstruct a Salesforce 18-char ID from a Customer.io
condition.** The casing is destroyed and a re-cased guess fails the checksum and
silently returns 0 rows. Look the ID up by name in Salesforce instead.

Related: `one_of` is additionally trimmed, deduplicated and sorted server-side, caps
at 50 values, and is rejected on `cio_id`. Avoid `one_of` for case-sensitive IDs.

### 6.5 Segment condition shape
Never use a bare `{"attribute": {...}}` leaf — that's automation-filter shape and
returns 500. For a profile attribute match use `attribute_change` with the
structural `to`/`from` filter pair:

```json
{ "event": { "type": "attribute_change", "name": "Status",
    "filters": { "and": [
      { "field": "to",   "operator": "eq", "value": "New", "inverse": false },
      { "field": "from", "operator": "eq", "value": "New", "inverse": true }
    ]}},
  "times": 1, "within": 0, "inverse": false }
```
The `from` half is structural, not a second user criterion. Same rule bans
`device_attribute`, `object_attribute`, `map`, `not` as segment leaves.

### 6.6 `ALL ROWS` does not work through the MCP tools
Both Salesforce MCP servers use `/query`, not `/queryAll`. `ALL ROWS` is Apex-only
syntax and returns `unexpected token: 'ALL'` everywhere else.

**Dangerous false negative:** `WHERE IsDeleted = true` through `/query` returns
**0 rows with no error** because `/query` silently filters deleted records. That is
not evidence of absence.

To actually query deleted records:
- **Developer Console → Execute Anonymous** — `ALL ROWS` works here
- **Workbench** — plain SOQL, tick "Deleted and archived records", no `ALL ROWS`
- **REST** — `/services/data/v64.0/queryAll/?q=...`, no `ALL ROWS`

Recycle Bin retention is **15 days**, then purged.

### 6.7 No merge capability via MCP
Salesforce REST has no merge endpoint and neither MCP exposes one — only create,
update, delete. Contact merges must happen in the UI, or via SOAP `merge()` /
Apex `Database.merge()`. Deleting is not merging: it destroys the loser's tasks,
events and history.

### 6.8 Salesforce MCP result quirks
- Large results (>~25k tokens) are written to a file instead of returned. Parse with
  `jq`/`python` via bash, not `Read` (line offsets won't chunk JSON).
- SOQL through the MCP caps around **2,000 records** per call and reports
  `done: false` with a `nextRecordsUrl` that can't be followed. Split queries by
  key ranges (e.g. `LastName >= 'Rob'`) or by a filter that partitions the set.
  `OFFSET` maxes at 2000 and won't rescue you.
- Results from parallel tool calls have appeared **transposed** (query A's result
  under query B). Sanity-check that a result actually answers the query you sent.
- `mcp__Salesforce_DX__*` requires `directory` and `usernameOrAlias` on every call.
  Use alias `prod`.

### 6.9 Customer.io API quirks
- **List filters are ignored unless `size > 0`.** `GET /segments?search=X` without
  `size` silently returns everything unfiltered.
- `page_all` emits NDJSON **per page**; a `jq` of `{id, name}` runs against the page
  envelope and yields nulls. Use `.segments[] | {id, name}`.
- `/attributes` returns **50 per page regardless of `size`**. Paginate.
- **There is no endpoint to list profiles in a segment.** `/segments/:id/customers`
  doesn't exist (500 + HTML). `/customers?segment_id=` silently ignores the param and
  returns unfiltered profiles. Use the UI:
  `https://fly.customer.io/workspaces/164380/journeys/segments/:id/people`
- Working endpoints for size: `/segments/:id/count` and `/segments/:id/metrics`.
- CDP endpoints live under `/cdp/api/workspaces/{id}/...`, Journeys under
  `/v1/environments/{id}/...`.
- `/sources/{id}/syncs` is **not** available — use `/sources/syncs` and filter.
  `/sources/{id}/syncs/{sync_id}` returns all-null; get sync detail from the list.
- `/destinations/{id}` returns fields at the **top level**, not under `.destination`.
- Always `dry_run` writes first. `PUT /segments/:id` **replaces** the definition and
  requires `name` or returns `Name can't be blank` — GET first.

### 6.10 Sync-run counters lie about success
`status: complete`, `failed_rows: 0` and a large `total_rows` do **not** mean data
landed. Sync 503 has reported clean runs for eight weeks while delivering nothing.
Always verify by fetching an actual record by ID in Journeys.

### 6.10b Some CDP responses come back double-encoded
Calls against workspace 224311 returned `{"data": "<json string>"}` — the payload
JSON-encoded inside a string field — while identical calls against 164380 returned
plain objects. A `jq` filter that works on one workspace can silently yield `null`
or an empty array on the other. If a filter returns nothing unexpectedly, re-run
without `jq` and look at the raw shape before concluding the data is absent.

### 6.11 SiMo BPO is a different workspace
`012Qg000003xvgTIAQ` is excluded from workspace 164380 by design. If you widen a
Lead sync filter and drop that exclusion, ~35,700 records flood the wrong workspace.
Keep the exclusion in every filter you write.

### 6.12 Data-quality caution before any send
Lead lists in this org have included bulk-imported phone contacts with junk names
and consumer webmail addresses. Before enabling any campaign against a new segment,
check: creation window (a 43-second span means bulk import), share with email
addresses, name plausibility, and bounce history. A 20% bounce rate damages the
whole workspace's sender reputation, not just one campaign.

---

## 7. Verification recipes

Check whether a Salesforce lead reached Customer.io:
```
GET /v1/environments/164380/customers/{LEAD_ID}?id_type=id
# 404 = not synced. Do not test by email.
```

Segment size and health:
```
GET /v1/environments/164380/segments/{id}/count
GET /v1/environments/164380/segments/{id}/metrics
GET /v1/environments/164380/segments/{id}/status
```

Sync health (the real test is a record lookup, not these counters):
```
GET /cdp/api/workspaces/164380/sources/syncs
GET /cdp/api/workspaces/164380/sources/34098/sync_runs?source_sync_id=503&limit=10
GET /cdp/api/workspaces/164380/sources/34098/sync_runs?show_only_errors=true
GET /cdp/api/workspaces/164380/sources/34098/events?limit=100
   # userId prefix tells you what's actually flowing: 00Q=Lead, 006=Opportunity
GET /cdp/api/workspaces/164380/source_destination?source_id=34098
```

Campaign deliverability:
```
GET /v1/environments/164380/campaigns/{id}/metrics
# read total_sent, total_bounced, total_spammed, total_unsubscribed, total_human_clicked
```

Count what should be in a segment, from Salesforce:
```sql
SELECT COUNT(Id) FROM Lead
WHERE OwnerId = '005Kb00000B1ZDCIA3'
  AND LeadSource = 'Likely to Sell'
  AND Branch__c = '703'
```

---

## 8. Open items

1. **Lead sync outage** — awaiting Customer.io support on connection `19589`
   `settings.objects` Lead mapping. Ticket references run `32768355`.
2. ~~Workspace 224311 health~~ — **closed 2026-08-25.** Lead sync there is healthy;
   35,548 of 35,826 SiMo BPO leads present. Now serving as the control case (§4.5).
   Residual: the ~278-record shortfall is unexplained but low priority.
3. **Ottone duplicate contacts** — needs a UI merge. Decide which survives; the eXp
   Realty record (`003Qg00000wlGmMIAU`) carries the current relationship, the yahoo
   record (`003Qg00000tY9lxIAC`) carries all 2,761 leads. **If merged, segment 685's
   `Referred_By__c` condition must be updated to the surviving Contact ID or it
   silently empties.**
4. **Campaign 125** — running with poor deliverability. Laura and Giovanni own the
   decision; they have been flagged.
5. **Segment 714 naming** — "Lucio Romero" appears in the name but not the filter,
   and no such user exists.

---

## 9. Working style for this account

- Verify before asserting. Counts, states and IDs change mid-session — campaign 125
  went from `stopped` to `running` and segment 685 was created by someone else while
  this investigation was in progress. Re-read before acting on a stale value.
- Prefer reads. Confirm before any write, delete, merge, or campaign state change.
- Distinguish "the API returned zero" from "there is nothing there." Several
  endpoints here return clean zeros for the wrong reason.
- Say which workspace and which org a finding came from.
