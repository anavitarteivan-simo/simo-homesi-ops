# SiMo BPO — Reply-Gated Lead Capture — Design & Plan

**Status:** Design only (nothing built)
**Date:** 2026-07-02
**Org:** Simo Solutions Group / Homesí (prod)

---

## 1. Goal

Launch a **BPO service offering** to our existing realtor and loan-officer database
(recruitment / MMI-sourced contacts) and capture *interested* prospects into a **separate,
clearly-labeled pipeline** — without polluting or duplicating the recruitment / B2C / B2B books.

The mechanism is **reply-gated**: we do NOT bulk-duplicate the database. We email the audience,
and only when someone **replies** (shows interest) do we create a **SiMo BPO lead** for them.

---

## 2. Key architecture decisions (locked)

| Decision | Choice | Implication |
|---|---|---|
| Where SiMo leads live | **Same Salesforce org**, new **SiMo BPO** Lead record type | Simplest; one system. Not a hard data wall, but that's acceptable (see below). |
| Isolation level | **Operational** (same company) — **admins may see everything** | **No restriction rules needed.** Admins already have View/Modify All via System Administrator. |
| Who sends the batch | **Customer.io (CIO)** | Salesforce is only the *destination*; CIO owns sender, reply-to, tracking, unsubscribe. |
| Reply capture / lead creation | **n8n** listening on `contact@simosolutionsgroup.com` | n8n is the only bridge: dedup, match, create. |
| Existing automation | Most rules are **record-type-restricted** | A new record type mostly won't trigger borrower/recruitment automation — **but must be verified** (§7). |

### 2.1 Visibility model (confirmed in org)
- **System Administrator** → View All + Modify All on Lead & Opportunity (admins see all — as desired).
- Assignable permission sets if a *non-admin* SiMo user needs full visibility: **Manage All Leads**,
  **Manage All Opportunities**, **Manage Leads & Opportunities**.
- No restriction rules, no sharing rules required for this project.

---

## 3. End-to-end flow

```
[CIO] send BPO campaign to realtor/LO audience
        (From + Reply-To = contact@simosolutionsgroup.com)
                    │
                    ▼  recipient replies
[Inbox] contact@simosolutionsgroup.com
                    │
                    ▼
[n8n]  1. Filter: drop auto-replies / OOO / bounces / non-human
       2. Extract sender email (+ name, message)
       3. Dedup: does a SiMo BPO lead already exist for this email?  ──► yes ──► stop (or update)
       4. Match: find existing Lead / Contact / Loan_Officer__c by email
       5. Create SiMo BPO Lead:
            - mapped fields (name, email, phone, company, NMLS…)
            - Source_Record_Id__c  = matched record Id (or blank if new)
            - SiMo_Source_Type__c  = Realtor / Loan Officer / New
            - LeadSource           = "SiMo BPO"
       6. (optional) notify a SiMo rep / post to a channel
                    │
                    ▼
[Salesforce] SiMo BPO lead in its own pipeline; admins + SiMo team can work it
```

**Why reply-gated is the right call:** we never create 10k+ duplicates. The SiMo pipeline only
contains people who engaged — self-selecting, clean, compliant, and small enough to work by hand.

---

## 4. Salesforce components to build

### 4.1 Record type + layout
- New Lead record type **SiMo BPO** (`SiMo_BPO`).
- Page layout replicated from the Realtor layout (adjust fields for BPO context).
- Assign the record type to the relevant profiles (SiMo team + admins).

### 4.2 Fields (new, on Lead)
| API name | Type | Purpose |
|---|---|---|
| `Source_Record_Id__c` | Text (18) **External Id** | Id of the original Lead/Contact/Loan Officer the SiMo lead came from — link-back, avoids re-contact, enables cross-pipeline reporting. |
| `SiMo_Source_Type__c` | Picklist | `Realtor` / `Loan Officer` / `New` (no prior record). |
| `SiMo_Opt_Out__c` | Checkbox | SiMo-channel suppression, separate from the existing email opt-out so unsubscribing from BPO ≠ unsubscribing from everything. |

*(LeadSource: reuse the existing field with a new value **"SiMo BPO"** — LeadSource is not restricted in this org, so a new value stores fine.)*

### 4.3 Integration user / connected app for n8n
- A dedicated **integration user** (own profile/permset) so n8n's writes are attributable and revocable.
- **Connected App** (OAuth) for n8n → Salesforce (query Lead/Contact/Loan_Officer__c; create Lead).
- Least-privilege: Create/Read on Lead, Read on Contact + Loan_Officer__c, nothing else.

---

## 5. n8n flow design

### 5.1 Trigger + hygiene
- **Email trigger** (IMAP or provider webhook) on `contact@simosolutionsgroup.com`.
- **Filter out**: auto-replies / out-of-office (`Auto-Submitted`, `X-Autoreply` headers, subject "Out of Office"), bounces (mailer-daemon), and internal addresses.
- Extract: sender email (normalized/lowercased), sender display name, message body (for the note).

### 5.2 Dedup (SiMo side)
- Query Salesforce: `SELECT Id FROM Lead WHERE RecordType.DeveloperName='SiMo_BPO' AND Email=:email AND IsConverted=false`.
- If found → stop (or append a note / bump a "replied again" counter). **No duplicate SiMo leads.**

### 5.3 Match (source side)
- Query, in order, by email:
  1. `Lead` (existing realtor/LO/borrower) — capture Id + fields.
  2. `Contact` — capture Id + fields.
  3. `Loan_Officer__c` (custom object) — capture Id + fields.
- First hit wins → sets `Source_Record_Id__c` + `SiMo_Source_Type__c`. No hit → `SiMo_Source_Type__c = New`.

### 5.4 Create
- Insert `Lead` with RecordTypeId = SiMo BPO, mapped fields, `LeadSource='SiMo BPO'`, source link-back.
- Owner: a SiMo queue or a default SiMo rep (decide — §9).

### 5.5 Notify (optional)
- Post to Slack/Teams or create a Salesforce Task for the SiMo rep so replies get worked fast.

---

## 6. Customer.io (send side) — requirements

- **Sender + Reply-To = `contact@simosolutionsgroup.com`.**
- **Domain auth:** SPF / DKIM / DMARC for `simosolutionsgroup.com`, or the batch lands in spam.
- **Audience:** the realtor/LO segment (CIO segment or a synced list). Respect any existing global suppression.
- **Compliance (CAN-SPAM — this is new-purpose outreach to recruitment-sourced contacts):**
  - Unsubscribe link + physical mailing address in the footer.
  - CIO unsubscribe should map back to `SiMo_Opt_Out__c` (via the existing CIO→SF path, or a small n8n step) so a BPO opt-out is honored and doesn't touch the recruitment opt-out.
- **Tracking:** opens/clicks live in CIO (as today). Reply = the real conversion signal here.

---

## 7. Automation audit (must do before n8n inserts)

Most Lead rules are record-type-restricted, so a SiMo BPO lead *should* skip them — but the
**create-time** ones must be verified, or n8n inserts will fail or get polluted:

| Automation | Risk if not RT-guarded | Action |
|---|---|---|
| `not_allow_to_create_non_borrowers_leads` (VR) | May **block** the insert | Confirm it excludes SiMo BPO, or add an exclusion. |
| `branch_mandatory_validation_rule` | May **block** if Branch required | Confirm SiMo BPO isn't forced to have a Branch. |
| `LeadSource_Required_Borrower` (VR) | Requires LeadSource | We set `LeadSource='SiMo BPO'`, so OK — verify. |
| `branch_default_when_Lead_create` (flow) | Assigns a branch meant for borrowers | Confirm RT filter excludes SiMo BPO. |
| `Update_Strategy_Field` (flow) | Computes NPPM/B2B strategy | Currently fires on **all** Borrower RT; SiMo BPO is a different RT, so should skip — verify. |
| `add_lead_to_campaign` (flow) | Round-robin owner + campaign assignment | Confirm RT scope. |
| Loan Officer / owner default flows | Wrong owner assignment | Confirm RT scope. |

**Deliverable of the audit:** a short list of exactly which rules (if any) need a `RecordType != SiMo_BPO` guard added before go-live.

---

## 8. Reporting & lifecycle

- **SiMo pipeline reports** filtered to `RecordType = SiMo BPO` — its own funnel, conversion, source-type mix.
- **Cross-pipeline** via `Source_Record_Id__c`: "which of our recruited realtors became BPO prospects," attribution back to the original relationship.
- **De-dupe / re-contact guard:** before a future recruitment or BPO send, exclude anyone already a SiMo BPO lead (or already opted out of the SiMo channel).

---

## 9. Open decisions

1. **Owner of new SiMo leads** — a SiMo queue, round-robin among SiMo reps, or one default owner?
2. **Field map** — exact set of fields to copy from the matched source record (name/email/phone/company/NMLS/title/…?).
3. **Repeat replies** — on a 2nd reply from an existing SiMo lead: ignore, note, or re-open?
4. **SiMo opt-out wiring** — should a CIO unsubscribe write `SiMo_Opt_Out__c` via the existing CIO→SF flow or via n8n?
5. **Notification** — do SiMo reps want a Slack/Teams ping or a Salesforce Task on each new reply-lead?
6. **"New" (no-match) replies** — someone replies who isn't in our DB at all: create as SiMo BPO `New`, or route for manual review first?

---

## 10. Build phases (proposed order)

| Phase | Scope | Depends on |
|---|---|---|
| **0 (now)** | This plan; resolve §9 open decisions | — |
| **1** | Salesforce foundation: SiMo BPO record type, layout, 3 fields, LeadSource value | §9.2 field map |
| **2** | Automation audit (§7) + add any needed RT guards | Phase 1 |
| **3** | Integration user + Connected App for n8n | Phase 1 |
| **4** | n8n flow: trigger → filter → dedup → match → create → notify | Phases 1–3 |
| **5** | CIO send: domain auth, audience, compliance footer, opt-out wiring | independent (CIO side) |
| **6** | Test end-to-end with a small batch; verify no automation misfires; tune | all |

---

## 11. Risks / watch-items

- **Deliverability** of a new domain (`simosolutionsgroup.com`) — needs SPF/DKIM/DMARC before any real send.
- **New-purpose outreach** to recruitment-sourced contacts — keep the SiMo opt-out honored and separate.
- **Reply false-positives** — auto-replies/OOO/bounces must be filtered or they create junk leads.
- **Automation misfire** — the §7 audit is the gate; do not run n8n inserts until it's clean.
- **Record type ≠ security** — admins and integration users see all SiMo leads. This is accepted per the decision, but worth remembering if the isolation requirement ever hardens (that would force a separate org).
