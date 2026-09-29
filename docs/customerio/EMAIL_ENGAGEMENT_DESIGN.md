# Lead Email Engagement Score — Design & Plan

**Status:** Design only (nothing built)
**Author:** Salesforce admin session
**Date:** 2026-07-02
**Org:** Simo Solutions Group / Homesí (prod)

---

## 1. Goal

Produce an **email engagement score** that shows how engaged a customer is with our
email campaigns, built from Customer.io (CIO) email activity. Requirements as stated:

- See which campaigns a customer was added to (A, B, C…).
- Score three event types: **Email Sent**, **Email Opened**, **Link Clicked**.
- **Repeat actions accumulate** — if a customer opens the same email 5×, the score rises each time.
- A campaign can have **N emails**; scoring within a campaign is **cumulative** across those emails.
- Each campaign yields a **per-customer score** (customer Y → score X on campaign A, score Z on campaign B).
- **Overall engagement = average of the per-campaign scores.**

---

## 2. Current-state findings (what the data supports)

### 2.1 The engagement events exist — as Task records
Customer.io writes each email event into Salesforce as a **Task** on the Lead/Contact
(`WhoId`), with the event type in the custom picklist **`Task.Subtype__c`**.

Volumes (all-time, prod):

| Subtype__c | Count | Use in score |
|---|---:|---|
| Email Sent | 1,350,565 | base signal |
| Email Opened | 243,364 | engagement |
| Email Link Clicked | 75,540 | strong engagement |
| Email Failed | 18,851 | (exclude / negative) |
| Email Unsubscribed | 5,009 | (suppression) |
| Email Marked as Spam | 60 | (negative) |
| SMS | 61,884 | (separate, out of scope for email score) |
| Call / Task Other / Meeting / Reminder | ~160k | not email (ignore) |

Each open/click is its **own Task**, so **repeat actions are already captured** as separate
rows — the cumulative / repeat-counting requirement is natively satisfied by counting rows.

### 2.2 The blocker — no campaign link on the events
The events **cannot be attributed to a specific campaign or email** with the current data:

- **No campaign/broadcast field on Task.** Every custom Task field was reviewed — they are all
  call (RingCentral), Zoom, SLA, or processing-doc fields. Nothing carries a CIO `campaign_id`,
  `broadcast_id`, `message_id`, or `newsletter_id`.
- **No CIO event object.** There is no `CIO_Event__c` or equivalent custom object.
- **The Subject is the message subject line, not the campaign** — and it's personalized
  (e.g. "Gonzalo Lopez, we're excited to connect! 🙌"), so it can't be reverse-matched to a campaign.
- **The `Email Sent` Tasks are mixed** — some are CIO nurture, many are ordinary rep emails
  captured by Einstein Activity Capture / Outlook ("Re: Preapproval…", "Title Request…"). They
  share the same `Subtype__c`, so CIO events aren't cleanly separable by field alone.

### 2.3 Second blocker — Salesforce Campaigns are not the CIO campaigns
The Campaigns that have members are **lead-source** campaigns — Facebook lead-gen forms
("Campaña Formularios Casa buena," "New Leads Campaign-FORM," the `_leadgen` set), event invites,
and a couple of email blasts. The CIO nurture emails that generate the engagement Tasks are
**not modeled as these Campaign records**, and there is no CampaignMember ↔ CIO-email join.

**Conclusion:** "customer added to campaign A/B/C" (CampaignMember) and "customer opened our
emails" (CIO Tasks) live in two disconnected systems with **no shared key**. Per-campaign
engagement scoring is therefore **not buildable from the data as it stands** — it is blocked on
an integration change, not on Salesforce configuration.

---

## 3. Target scoring model (design)

### 3.1 Event weights (tunable)
| Event | Default weight | Rationale |
|---|---:|---|
| Email Sent | 1 | we reached them |
| Email Opened | 3 | they engaged |
| Email Link Clicked | 5 | strong intent |
| Email Failed | 0 (or −1) | deliverability signal |
| Email Marked as Spam | −10 | strong negative |
| Email Unsubscribed | suppression flag, not a score input |

### 3.2 Cumulative & repeat-counting
Score counts **every** event row, so repeats add up:

```
raw_score = (Sent  × w_sent)
          + (Opened × w_open)
          + (Clicked × w_click)
          + (Spam × w_spam)
```

Because each open/click is a separate Task, opening the same email 5× contributes 5 × w_open.

### 3.3 Two levels of the score

**Level 1 — Person score (BUILDABLE NOW).**
Aggregate all of a person's email events into one engagement score + tier. Answers
"how engaged is this customer with our emails overall."

**Level 2 — Per-campaign score (BLOCKED — needs §5 integration fix).**
The same formula scoped to one campaign's N emails, producing one score per (customer × campaign),
with **overall engagement = AVG(per-campaign scores)**. This is the exact spec requested, and
becomes buildable once events carry a campaign id.

### 3.4 Engagement tier (person level)
Derived band for easy segmentation (thresholds tunable):

| Tier | Rule (example) |
|---|---|
| Hot | score ≥ 30 AND opened/clicked in last 30 days |
| Warm | score 10–29, or activity in last 90 days |
| Cold | score < 10 or no engagement in 90+ days |
| Dormant/Suppressed | Unsubscribed = true, or only Sent with 0 opens over 6+ months |

---

## 4. Level 1 — Person-level engagement (buildable today)

### 4.1 Fields (on Lead and Contact)
| Field | Type | Meaning |
|---|---|---|
| `Email_Sent_Count__c` | Number | cumulative Email Sent |
| `Email_Opened_Count__c` | Number | cumulative Email Opened (repeats included) |
| `Email_Clicked_Count__c` | Number | cumulative Link Clicked (repeats included) |
| `Email_Engagement_Score__c` | Number (or formula) | weighted score per §3.1 |
| `Last_Email_Engagement__c` | DateTime | most recent open/click |
| `Email_Engagement_Tier__c` | Picklist/Formula | Hot / Warm / Cold / Dormant |

> If the score is a **formula** over the three count fields, it recomputes automatically and only
> the counts need maintaining.

### 4.2 Maintenance
- **Going forward:** a record-triggered flow (or Apex trigger) on **Task after-insert**, filtered to
  `Subtype__c IN (Email Sent, Email Opened, Email Link Clicked)` and `WhoId` = Lead/Contact,
  increments the matching count on the related record.
- **Historical backfill:** an Apex batch aggregates existing Tasks by `WhoId` and seeds the counts
  once. (Volume is large — 1.35M+ rows — so this is a batch job, not a synchronous script.)

### 4.3 Reporting
Standard Lead/Contact reports and list views on the score + tier; a dashboard of engagement
distribution and top-engaged customers.

### 4.4 Caveats
- The person score **includes rep emails** mixed into `Email Sent` (§2.2). If we only score
  Opened/Clicked (which are almost entirely CIO tracked-pixel/redirect events), the score is a
  cleaner "marketing engagement" signal. **Recommended: base the score on Opened + Clicked, use
  Sent only as context** — avoids inflating scores with 1:1 rep correspondence.

---

## 5. Level 2 — Per-campaign engagement (integration prerequisite)

### 5.1 What must change (CIO / integration side)
Each CIO email event delivered to Salesforce must include a **campaign identifier** (and ideally an
email/message identifier). Two clean options:

- **Option A — stamp the Task:** add fields the integration populates:
  `CIO_Campaign_Id__c`, `CIO_Campaign_Name__c`, `CIO_Message_Id__c` on Task.
- **Option B (preferred) — dedicated object `CIO_Email_Event__c`:** columns for
  `Recipient` (Lead/Contact), `Event_Type` (Sent/Opened/Clicked/…), `CIO_Campaign_Id`,
  `CIO_Message_Id`, `Event_Timestamp`. Keeps the 1.35M-event stream off the Task object and is
  cleaner to aggregate. This is the recommended target.

CIO's webhook payload already includes `campaign_id` / `broadcast_id` / `newsletter_id` and
`message_id` — so this is a mapping change in whatever middleware writes the events, not new data.

### 5.2 Salesforce model once the ID flows in
- **Campaign external id:** add `CIO_Campaign_Id__c` (External Id) to Campaign, so a CIO campaign
  maps to one Salesforce Campaign.
- **Junction object `Campaign_Engagement__c`** (Customer × Campaign):
  `Lead__c` / `Contact__c`, `Campaign__c`, `Sent_Count__c`, `Opened_Count__c`,
  `Clicked_Count__c`, `Campaign_Score__c` (formula per §3.1).
- **Aggregation:** trigger/batch rolls events into the matching `Campaign_Engagement__c` row.
- **Overall score:** roll-up (or formula) = **AVG(`Campaign_Score__c`)** across that person's
  `Campaign_Engagement__c` rows → written back to `Email_Engagement_Score__c` on Lead/Contact.

### 5.3 Data flow (target)
```
CIO event ──(integration adds campaign_id)──▶ CIO_Email_Event__c
        └─▶ aggregate into Campaign_Engagement__c (customer × campaign)
                └─▶ Campaign_Score__c per campaign
                        └─▶ Lead/Contact overall = AVG(campaign scores)
```

---

## 6. Recommended phasing

| Phase | Scope | Depends on |
|---|---|---|
| **0 (now)** | This design; decide weights + whether score = Opened+Clicked only | — |
| **1** | Level-1 person score: fields, going-forward flow, historical backfill, report/dashboard | nothing (buildable today) |
| **2** | Integration change: stamp `campaign_id` (+`message_id`) on events (Option A or B) | CIO / middleware owner |
| **3** | Level-2 per-campaign model: Campaign external id, `Campaign_Engagement__c`, aggregation, overall = AVG | Phase 2 complete |

---

## 7. Open decisions

1. **Score basis** — include `Email Sent` (inflated by rep emails) or score on **Opened + Clicked only** (recommended)?
2. **Weights** — confirm Sent 1 / Opened 3 / Clicked 5, and Spam penalty.
3. **Objects in scope** — Leads only, or Leads **and** Contacts (many events are on `003…` Contacts)?
4. **Recency decay** — flat cumulative, or decay older engagement (e.g. half-life 90 days) so the score reflects *current* engagement?
5. **Integration owner** — who can add `campaign_id` to the CIO→Salesforce event payload (Phase 2 gatekeeper)?
