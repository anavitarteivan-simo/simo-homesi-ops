# Customer.io — SimoSolutions Group Workspace: Salesforce Integration Replication Spec

**Status:** PREPARED 2026-07-02 — blocked on Customer.io connector re-auth (current token only covers workspace `164380` / Supreme Lending).
**Goal:** Replicate the Supreme Lending Salesforce integration into the SimoSolutions Group workspace, filtered to the new **SiMo BPO** record type; then update Supreme Lending syncs to exclude that record type.

---

## 0. New Salesforce record type IDs (created 2026-07-02, prod)

| Object | RecordType | DeveloperName | Id |
|---|---|---|---|
| Lead | SiMo BPO | `SiMo_BPO` | `012Qg000003xvgTIAQ` |
| Opportunity | SiMo BPO | `SiMo_BPO` | `012Qg000003xvgUIAQ` |

Both cloned from Realtor (same business process, same picklist assignments). Layouts `Lead-SiMo BPO Layout` / `Opportunity-SiMo BPO Layout` are clones of the Realtor layouts. Visibility: **Admin profile only** for now.

---

## 1. Supreme Lending (workspace 164380) as-is architecture

Two independent halves:

### Data-in (Salesforce → Customer.io)
- **Source `34098` "Salesforce Prod"** — `option_id: salesforce`, settings: `{sync_type: "pull", isSandbox: false, forceUseBulkApi: false, streamSliceStep: "P30D", instanceUrl: "https://ruby-ruby-7485.my.salesforce.com"}`, OAuth connected.
- Connected (connection `19589`, settings null) to **destination `13465` "Journeys Workspace"** (`option_id: customerio` — the workspace's own Journeys destination, auto-provisioned).
- **Sync `503` "Lead sync"** — pull, interval **1800s**, enabled, backfill n/a, `cdp_type: identify`, `record_type: Lead`, `identifiers: {user_id: "Id"}`. No where_clause today.
- **Sync `623` "Opportunity sync"** — pull, interval **1800s**, enabled, `cdp_type: identify`, `record_type: Opportunity`, `identifiers: {user_id: "Id"}`. No where_clause today.

### Data-out (Customer.io email metrics → Salesforce Tasks/opt-out)
- **Source `27714` "Journeys Message Metrics"** (`option_id: customerio`, `is_journeys_metrics_source: true`, auto-provisioned).
- → **Destination `52375` "Salesforce Prod"** (`option_id: salesforce`, settings `{isSandbox: false, instanceUrl: "https://ruby-ruby-7485.my.salesforce.com"}`), OAuth connected, **14 subscriptions** (see §4).

---

## 2. Sync 503 (Lead) — full mapping (verbatim from API, 2026-07-02)

```json
{"cdp_type":"identify","record_type":"Lead","identifiers":{"user_id":"Id"},
 "fields":["Id","LastName","FirstName","Name","RecordTypeId","Title","Company","City","State","Phone","MobilePhone","Email","LeadSource","Status","Industry","Rating","OwnerId","HasOptedOutOfEmail","IsConverted","ConvertedDate","ConvertedOpportunityId","CreatedDate","CreatedById","LastModifiedDate","DoNotCall","Citizenship__c","City__c","DOB__c","NMLS_Number__c","PPS__c","Recruitment_Segmentation__c","Referred_By__c","Workshop_Name__c","State__c","Credit_Score__c","CoBorrower_FirstName__c","CoBorrower_LastName__c","CoBorrower_Email__c","CoBorrower_Phone__c","Campaign_name__c","Adset_name__c","CoBorrower_DOB__c","Position_Recruitment__c","CoBorrower_Marital_Status__c","Marital_Status__c","Loan_Officer__c","Branch__c","Type_of_product__c","Created_Date_Time__c","Interest_rate__c","Loan_Program__c","Loan_Type__c","Property_City__c","Property_State__c","Buyers_Agent__c","LO_Assistant__c","Sellers_Agent__c","tdc_tsw__SMS_Opt_out__c","Phone_360SMS__c","Email_Owner__c","Title_Owner__c","Phone_Owner__c","Full_Name_Owner__c","Sales_Agent__c","NPPM__c","Original_Loan_Status__c","SMS_Opt_In__c","Strategy__c","IsDeleted","Webinar_Name__c","Webinar_Id__c"],
 "renames":{"Adset_name__c":"","Branch__c":"","Buyers_Agent__c":"","Campaign_name__c":"","Citizenship__c":"","City":"","City__c":"","Company":"","ConvertedDate":"","CreatedDate":"","Created_Date_Time__c":"","Credit_Score__c":"","DOB__c":"","DoNotCall":"","Email":"email","Email_Owner__c":"","FirstName":"First_Name__c","Full_Name_Owner__c":"","HasOptedOutOfEmail":"","Id":"LeadId","Industry":"","IsConverted":"","LO_Assistant__c":"","LastModifiedDate":"","LastName":"lastName","LeadSource":"","Loan_Officer__c":"","Loan_Type__c":"","Marital_Status__c":"","MobilePhone":"","NMLS_Number__c":"","Name":"name","OwnerId":"","Phone":"phone","Phone_360SMS__c":"","Phone_Owner__c":"","Rating":"","RecordTypeId":"","Recruitment_Segmentation__c":"","Referred_By__c":"","Sellers_Agent__c":"","State":"","State__c":"","Status":"","Title":"title","Title_Owner__c":"","Type_of_product__c":"","Workshop_Name__c":""}}
```

## 3. Sync 623 (Opportunity) — full mapping (verbatim from API, 2026-07-02)

```json
{"cdp_type":"identify","record_type":"Opportunity","identifiers":{"user_id":"Id"},
 "fields":["Id","IsDeleted","AccountId","RecordTypeId","Name","StageName","CloseDate","LeadSource","IsClosed","IsWon","OwnerId","CreatedDate","CreatedById","LastModifiedDate","LastModifiedById","LastStageChangeInDays","ContactId","Application_Date__c","Loan_Officers__c","Appraisal_Ordered_Date__c","Appraisal_Received_Date__c","Appraised_Value__c","BS_Sold_Units__c","Branch__c","Citizenship__c","Clear_to_Close_Date__c","Current_Milestone__c","Current_Status__c","DOB__c","Disbursement_Date__c","Disclosures_Signed_Date__c","Est_Closing_Date__c","File_Open_Date__c","LOA__c","LoanId__c","Loan_Folder__c","Loan_Processor__c","Loan_Purpose__c","Loan_Status__c","Loan_Type__c","Loan__c","NMLS_Number__c","PPS__c","Property_City__c","Property_State__c","Property_Type__c","Rate__c","Referred_By__c","Secondary_Phone__c","Submitted_to_Processing_Date__c","Submitted_to_UW_Date__c","Ad_Name__c","Phone__c","Credit_Score__c","agent_contact_owner_2__c","CoBorrower_FirstName__c","CoBorrower_LastName__c","CoBorrower_Phone__c","Type_of_product__c","Assigned_to__c","Assigned_Date__c","Referred_Date__c","CoBorrower_DOB__c","Closed_Loan__c","Position_Recruitment__c","Recruitment_Segmentation__c","CoBorrower_Marital_Status__c","Marital_Status__c","Buyers_Agent__c","Listing_Agent__c","Campaign_name__c","Opportunity_Team__c","tdc_tsw__SMS_Opt_out__c","lead_ID_Meta__c","LOA_support_OD__c","NMLS_Company__c","Phone_360SMS__c","First_Name__c","Owner_Title__c","Phone_Owner__c","Full_Name_Owner__c","Original_Loan_Status__c","SMS_Opt_In__c","State__c","Strategy__c","CoBorrower_Email__c","Email_Owner_Opp__c","HasOptedOutOfEmail__c","Email__c","Webinar_Name__c","Webinar_Id__c"],
 "renames":{"Branch__c":"","ContactId":"","CreatedDate":"","Email_Owner_Opp__c":"","Email__c":"email","Full_Name_Owner__c":"","HasOptedOutOfEmail__c":"HasOptedOutOfEmail","Id":"OpportunityId","IsClosed":"","LastStageChangeInDays":"","LeadSource":"","Loan_Officers__c":"","Name":"name","OwnerId":"","Owner_Title__c":"","Phone_360SMS__c":"","Phone_Owner__c":"","StageName":""}}
```

---

## 4. Destination 52375 subscriptions (14, all enabled) — replicate into Simo workspace DISABLED

All are on the Journeys Message Metrics source events. `OwnerId` hardcode `005Kb00000B1ZEtIAN` stays (same Salesforce org). Per-event pattern (verbatim configs in the 2026-05-21 redesign doc §6 + as-built §9):

| SL sub id | action | name | subscribe (trigger) |
|---|---|---|---|
| 182232 | customObject | Custom Object | `type = "track" and event = "Email Sent" and !match( properties.userId, "006*" )` |
| 342652 | customObject | Custom Object | `... "Email Opened" and !match(...006*)` |
| 343605 | customObject | Custom Object | `... "Email Unsubscribed" and !match(...006*)` |
| 343606 | customObject | Custom Object | `... "Email Link Clicked" and !match(...006*)` — has extra `Description` @template with url/recipient/campaign_id/action_id/delivery_id/timestamp |
| 343607 | customObject | Custom Object | `... "Email Marked as Spam" and !match(...006*)` |
| 343608 | customObject | Custom Object | `... "Email Failed" and !match(...006*)` — Subject uses `properties.failure_message` |
| 712640–712645 | customObject | Custom Object (Opportunity) | same 6 events with `match( properties.userId, "006*" )`, `WhatId` instead of `WhoId`; 712642 (Link Clicked) has the same extra `Description` template |
| 712646 | lead | Lead Email Opt Out | `... "Email Unsubscribed" and !match(...006*)` — update `{HasOptedOutOfEmail: true}`, matcher `traits.Id = $.properties.userId` |
| 712647 | opportunity | Opportunity Email Opt Out | `... "Email Unsubscribed" and match(...006*)` — update `{HasOptedOutOfEmail__c: true}` |

Lead-branch Task mapping template (WhoId): `{"operation":"create","recordMatcherOperator":"OR","enable_batching":false,"traits":{},"bulkUpsertExternalId":{"externalIdName":"","externalIdValue":""},"bulkUpdateRecordId":"","customObjectName":"Task","customFields":{"WhoId":{"@path":"$.properties.userId"},"Subject":<per-event>,"OwnerId":"005Kb00000B1ZEtIAN","TaskSubtype":"Email","ActivityDate":{"@path":"$.timestamp"}}}`
Opportunity-branch identical except `WhatId` replaces `WhoId`.

> When building the Simo replica, DO NOT hand-copy — re-read live configs from `GET /cdp/api/workspaces/164380/destinations/52375/subscriptions` and clone programmatically.

---

## 5. Record-type filters (the whole point)

Salesforce syncs support `mapping.where_clause` (SOQL WHERE, validated via `POST /cdp/api/workspaces/:ws/sources/:src/validate_salesforce_filter` with `{where_clause, sobject_name, identifiers}`).

| Workspace | Sync | where_clause |
|---|---|---|
| SimoSolutions (new) | Lead sync | `RecordTypeId = '012Qg000003xvgTIAQ'` |
| SimoSolutions (new) | Opportunity sync | `RecordTypeId = '012Qg000003xvgUIAQ'` |
| Supreme Lending 164380 | Lead sync `503` | `RecordTypeId != '012Qg000003xvgTIAQ'` |
| Supreme Lending 164380 | Opportunity sync `623` | `RecordTypeId != '012Qg000003xvgUIAQ'` |

Notes:
- `!=` in SOQL also excludes rows with NULL RecordTypeId — not a concern here (all Lead/Opp rows carry a record type).
- Update via `PUT /cdp/api/workspaces/164380/sources/34098/syncs/{503|623}` with the mapping including `where_clause`; **settings are merged**. Outer `confirm_restart: true` restarts the sync immediately.

## 6. Execution checklist

1. ✅ **USER re-authed the Customer.io connector** — token now covers 164380 + **224311 ("Simo Solutions Group")**.
2. ✅ Source **157352 "Salesforce Prod"** created in 224311 (pull, isSandbox false). Connected to Journeys destination **343979** via connection **67931** (settings null — same shape as Supreme Lending's 19589; the `settings.objects` gotcha did not apply).
3. ✅ Destination **344289 "Salesforce Prod"** created in 224311 — **enabled: false** (master off-switch), wired to Journeys Message Metrics source **156502**, with all **14 subscriptions created enabled** (769358–769371, exact clones incl. Link-Clicked Description template and both opt-out updates). Enabled-subs-on-disabled-destination = nothing flows until the destination itself is enabled — ONE toggle at go-live.
4. ✅ **Salesforce OAuth completed 2026-07-08** (as `sf integrations`, sysadmin). GOTCHAS hit on the way, worth remembering: (a) Salesforce's Oct-2025+ policy blocks uninstalled apps — Customer.io now ships an **External Client App managed package** that MUST be installed in the org first (`OAUTH_EC_APP_NOT_FOUND` otherwise; the classic "Customer.io Data Pipelines" connected app install does NOT satisfy it, and a locally created ECA can't — client_id must match CIO's). (b) The static package link in CIO's docs (`04tWj000000sQojIAE`) was DEAD ("Package Not Found") — the working link came from CIO's in-app connect flow. (c) Source and destination authorize SEPARATELY — connecting one leaves the other unconnected.
5. ✅ Syncs created on source 157352, both **disabled**: Lead sync **2082** (`RecordTypeId = '012Qg000003xvgTIAQ'`), Opportunity sync **2083** (`RecordTypeId = '012Qg000003xvgUIAQ'`), pull, 1800s, backfill none, mappings identical to Supreme Lending.
6. ✅ Supreme Lending exclusions applied 2026-07-08: sync 503 `where_clause = "RecordTypeId != '012Qg000003xvgTIAQ'"`, sync 623 `where_clause = "RecordTypeId != '012Qg000003xvgUIAQ'"`. Both still enabled, 1800s interval, full mappings preserved (verified by re-read).
7. ✅ Verified end state: Simo syncs 2082/2083 disabled + filtered; Simo destination 344289 **disabled** (OAuth connect had auto-enabled it — turned back off), OAuth connected, 14 subscriptions intact. **API GOTCHA: destination PUT REPLACES fields, does not merge — a partial `{enabled:false}` PUT blanked the destination name; always include `name` in destination PUTs.**

## 6b. GOTCHA — reserved `phone` attribute broke the initial ingest (fixed 2026-07-09)

After the 35.8k-lead load, the Simo workspace showed only 186 profiles. Root cause: the Lead sync mapping renamed `Phone` → the **reserved Customer.io `phone` attribute**, and new workspaces enforce a **16-byte max** on it. Salesforce-formatted phones (`+1 (XXX) XXX-XXXX` = 17 chars) caused the Journeys destination (343979) to discard entire identify batches with HTTP 400 (`attributes.phone: property value cannot be longer than 16 bytes`). Supreme Lending's workspace (Dec 2024) is grandfathered and does NOT enforce this — its identical `Phone`→`phone` rename works there. Fix: removed the rename on sync 2082 (Phone stays as attribute `Phone`), then `POST .../syncs/2082/runs {"restart": true}` for a full resync → 35,843 rows, 0 failures. If a `phone` identifier is ever needed in Simo, map `Phone_360SMS__c` (digits-only, ≤16 bytes) instead.

## 6c. Workspace identifier configs DIFFER (as-found, deliberate to leave)

| | Supreme Lending 164380 | Simo Solutions 224311 |
|---|---|---|
| `id` identifier | enabled | enabled |
| `email` identifier | **disabled** (attribute only) | **enabled** |
| identify_by_id | false | true |

Consequence in Simo: records sharing an email MERGE into one profile, and an email unsubscribe suppresses every record with that email. Supreme keys strictly by Salesforce Id (one record = one profile, always). Changing identifier config on a live workspace is a CIO UI/support operation — left as-is 2026-07-09; profile count ~35.5k vs 35,829 leads reflects email merges + blank emails.

## 7. Go-live — EXECUTED 2026-07-08 (user go-ahead)

- Lead sync 2082 + Opportunity sync 2083: **enabled** (30-min interval; first run imports all matching records — currently 0 until SiMo BPO records exist).
- Destination 344289: **enabled** with all 14 subscriptions active.
- Everything in the Simo workspace is now LIVE, scoped to the SiMo BPO record type; Supreme Lending syncs exclude it.

## 8. OPEN ITEM — Supreme Lending connection migration deadline

Per CIO docs (updated 2026-07-02): Salesforce connections created before **2026-06-17** must migrate to the External Client App auth before **2026-08-17** or they STOP WORKING. This applies to Supreme Lending source `34098` + destination `52375` (created Dec 2024). The ECA package is already installed in the org, so the remaining step is: workspace 164380 → Salesforce connection → migration banner → "Upgrade authentication" → log in as `sf integrations` → Allow. **Do this well before Aug 17.**
