# Borrower Follow-Up — PRODUCTION cutover log

**Date:** 21 August 2026 · **Org:** `00DKb000000OvoRMAS` (prod, `ruby-ruby-7485.my.salesforce.com`)
**Deployed by:** It Support (`005Kb00000B1HzJ`) via Salesforce DX, alias `prod`
**Test level:** omitted on every deploy — the FUR system contains **zero Apex**, confirmed by querying `ApexClass` / `ApexTrigger` in both orgs. This is what let us bypass prod's 16 pre-existing failing tests entirely.

---

## 1. What is now live in production

| Wave | Components | Result |
|---|---|---|
| 1 | `Follow_Up_Request__c` object + 24 fields | ✅ 25/25 |
| 2 | `Outbound_Message__c` object + 5 fields | ✅ |
| 3 | `Mortgage_Condition__c.Follow_Up_Request__c` lookup | ✅ |
| 4 | `Mortgage_Condition__c` 7 non-formula fields | ✅ |
| 5 | `Mortgage_Condition__c` 2 formula fields | ✅ |
| 6 | `Lead` 4 fields + `Opportunity` 2 fields | ✅ 15/15 |
| 7 | PermissionSet `Borrower_Follow_Up_Integration` | ✅ |
| 9 | CustomTab + 3 ListViews | ✅ |
| 8 | 4 Flows (landed Draft) | ✅ |
| 10 | FlowDefinitions → all 4 **Active** | ✅ |
| 11 | Admin FLS on all 43 new fields + tab visibility | ✅ |

### New prod Ids — record these, they differ from staging

| Component | PROD Id |
|---|---|
| `Follow_Up_Request__c` object | `01IQg000004Ol1tMAC` — key prefix **`a1P`** |
| `Outbound_Message__c` object | `01IQg000004Ol3VMAS` — key prefix **`a1Q`** |
| PermissionSet `Borrower_Follow_Up_Integration` | `0PSQg000000JTUXOA4` |
| CustomTab `Follow_Up_Request__c` | `01rQg00001KtughIAB` |
| ListView `Open_FURs` / `Escalated` / `All_FURs` | `00BQg00000RVElX` / `RVElW` / `RVElV` |
| Flow `Set_Has_AI_Followup_Request` v1 | `301Qg00000zDV2xIAG` |
| Flow `Clear_Next_Touch_On_FUR_Stop` v1 | `301Qg00000zDV2uIAG` |
| Flow `Resume_FUR_On_WorkItem_Complete` v1 | `301Qg00000zDV2wIAG` |
| Flow `Repoint_FUR_On_Lead_Convert` v1 | `301Qg00000zDV2vIAG` |
| Admin profile (FLS target) | `00eKb000000aw4EIAQ` (`fullName` = **`Admin`**) |

### Verified after deploy
- `Follow_Up_Request__c` — **InternalSharingModel = Private**, ExternalSharingModel Private, feeds enabled. Set at creation, so no sharing-recalc race.
- `Outbound_Message__c` — ControlledByParent (correct for master-detail).
- `Mortgage_Condition__c` — still **Private**, feeds off, untouched. Its object header was never deployed.
- All 4 flows `IsActive = true`, triggering on Borrower Follow-Up / Lead / Work Item / Lead.
- `Requested_Document__c` — **still absent from prod.** Correct; it is retired.

---

## 2. Decisions taken at cutover

| Decision | Choice | Why |
|---|---|---|
| FUR sharing model | **Private** | Follow-ups carry borrower questions and document requests. Matches how `Mortgage_Condition__c` is already secured in prod. Staging was Public Read/Write. |
| Unused fields | **Deployed all 4** (`Touches_Sent__c`, `Doc_Type__c`, `ContentDocument_Id__c`, `Received_At__c`) | Forward compatibility — WF-4 v3 document-receipt work needs no further prod field deploy. |
| Flow activation | **All 4 active** | Accepted that `Repoint_FUR_On_Lead_Convert` now runs on every prod lead conversion. It is a genuine no-op while prod holds zero FURs. |
| FLS rollout | **Step 1 = Admin only** (done) | Steps 2+ below. |

---

## 3. Findings that corrected our own documentation

1. **`Opportunity.Needs_Agent__c` already existed in prod.** The gap analysis said it was missing, based on `FieldDefinition` returning no row. The deploy reported `created: false` against pre-existing Id `00NQg0000097LTzMAM`. **Lesson: deploy output is the authoritative existence check; `FieldDefinition` can under-report.**
2. **The duplicate "System Administrator" profile is gone.** Prod now returns exactly one row (`00eKb000000aw4EIAQ`); `00eQg00000M4WMTIA3` no longer exists. The naming rule still held — deploying `Admin.profile-meta.xml` returned `fullName: Admin`, `created: false`.
3. **The permission set referenced 8 fields prod will never have** — `Chase_Latest_Note__c`, `SMS_Consent_At__c`, `SMS_Consent_Source__c` on Lead and Opportunity, plus `AI_Followup_Request__c` / `AI_Followup_Status__c` on Opportunity. All belong to unbuilt features (SMS is Phase 2; the Opportunity request box was deferred to Leads-only). Stripped rather than deploying dead fields.
4. **It also referenced the retired `Requested_Document__c`** — 5 fieldPermissions + 1 objectPermissions block. Stripped.
5. **A `.orig` backup file inside a deploy folder caused a failed deploy.** The CLI picked it up and the stale copy still named `Requested_Document__c`. Because `rollbackOnError` is on, the tab and 3 list views that had already succeeded **were rolled back with it**. Deploy from folders containing only the exact files intended — never leave backups in the tree.
6. **Master-detail fields cannot take FLS.** `Outbound_Message__c.Follow_Up_Request__c` had to be excluded from the Admin profile — same class as the known `Status__c` required-field trap. 43 fields, not 44.

---

## 4. STILL REQUIRED before the demo works

### 4.1 Page layouts and placement — **not deployed, blocks the demo**
Nothing visual was deployed. Prod is using default layouts, so:
- The **Lead** request box (`AI_Followup_Request__c`) and `AI_Followup_Status__c` are not on any Lead page — an agent cannot type a request.
- The **Borrower Follow-Up** layout has no related lists (Work Items / Outbound Messages) and no field arrangement.
- `Chase_With_Borrower__c` / `Borrower_Doc_Ask__c` are not in a "Borrower Chase (Automation)" section on the Work Item layout.
- The Work Items widget (`c:mortgageChecklist`) is already in prod and needs no deploy, but must be placed on Lead pages if Lead work items are wanted.

Do **not** deploy the staging FUR layout as-is: it still carries a **Requested Documents** related list for the retired object.

### 4.2 n8n repoints — 12 hardcoded values
| What | From (staging) | To (prod) | Places |
|---|---|---|---|
| Salesforce credential | Sandbox `8j2Z1Q8YwHHvR9nn` | prod credential | every Salesforce node, all 7 workflows |
| `Mortgage_Condition__c` Task RT Id | `012Em00000ANGRJIA5` | **`012Qg000003uX4PIAU`** | 4 nodes |
| Instance URL | `ruby-ruby-7485--staging.sandbox.my.salesforce.com` | `ruby-ruby-7485.my.salesforce.com` | 4 HTTP nodes |
| Default work-item owner | `005Em00000E99YfIAJ` | prod user Id | Escalate sub `Prep` |

### 4.3 Salesforce-side access
- Assign PermissionSet `0PSQg000000JTUXOA4` to the n8n integration user.
- Grant the `Mortgage_Condition__c` **Task** record type (`012Qg000003uX4PIAU`) to that user's **profile** — RT assignment is profile-only, permission sets cannot do it. This has already caused `INVALID_CROSS_REFERENCE_KEY` once.

### 4.4 FLS steps 2+
Step 1 (Admin) is done. The remaining 13 human working profiles are listed in the Salesforce CLAUDE.md standing rule. Field list: `Salesforce Workspace/furprod/new_fields_for_FLS.txt` — 43 fields, with the 2 formulas marked read-only. Recommended for agents: `AI_Followup_Status__c` and `Has_AI_Followup_Request__c` **read-only** (an agent edit corrupts the NEEDS DETAIL fingerprint gate and the poll checkbox).

### 4.5 Not started
- `fur_settings` / `fur_cadences` data tables still point at staging test values. **`test_mode` must stay `true`** until the email templates are approved.
- Email templates, sender mailbox, unsubscribe mechanism — see `Borrower_Email_Marketing_Brief.md`.

---

## 4b. Layouts — progress 24 August

| Item | State |
|---|---|
| **FUR layout** (`00hQg00000IiV2XIAV`) | ✅ **live in prod.** 14 automation-owned fields locked (incl. `Thread_Token__c`, `Next_Touch_At__c`, `Lead__c`, `Opportunity__c`); `Status__c` left editable so cancelling still works; deprecated `Outbound_Message_Ids__c` removed; related lists = Files, Work Items (Name/Status/Priority/Due Date/Chase With Borrower), Outbound Messages (Name/Channel/Sent At/Cadence Step), New excluded on both children. |
| **Work Item layout** (`00hQg00000F30irIAB`) | ✅ **live in prod.** Mirrored staging's `Borrower Chase (Automation)` section, all 10 fields. Prod's `RelatedActivityList` + `RelatedHistoryList` **deliberately preserved** — staging had none, and deploying staging's file as-is would have deleted them. |
| **Lead page** | ✅ done by user in App Builder — "AI Follow Up Request" tab with Preferred Language, AI Follow-Up Status, AI Follow-Up Request, plus the Follow-Up Requests related list and Work Items card. Outstanding: set **AI Follow-Up Status to read-only** (an agent edit corrupts the `NEEDS DETAIL #<fp>` retry fingerprint). |
| **Opportunity layout** | ❌ not started. Classic `Opportunity-Borrower Layout` is missing `Needs_Agent__c`, `Needs_Agent_Date__c`, `Preferred_Language__c`, `HasOptedOutOfEmail__c`, and has **no Borrower Follow-Ups related list**. The Lightning page ("Opportunity Record Borrower - Final") is Dynamic Forms, so fields must also be placed there by hand. |
| **FUR tab in app nav** | ❌ not in `standard__LightningSales` / `HOMESB2C` `<tabs>`. Reachable only via App Launcher, and list views will spawn new workspace tabs. |
| **FUR compact layout** | ❌ highlights panel shows Name only. Polish. |

### Layout deploy gotchas found (neither was in the gap analysis — layouts aren't queryable via the data API)
1. **`SmartFillEnrich`** is a standard action present in the sandbox but **not in prod**. Both staging layouts excluded it; prod rejects excluding a button it doesn't have. Strip `<excludeButtons>SmartFillEnrich</excludeButtons>` from any layout ported from staging. (`OpenSlackRecordChannel` is fine — Slack is enabled in prod.)
2. **Related-list columns must be unqualified.** `<fields>Status__c</fields>`, not `<fields>Mortgage_Condition__c.Status__c</fields>`. Confirmed against the existing `Lead-Borrower Layout`.
3. **A `.orig` backup left inside a deploy folder is a deployable component.** One caused a failed deploy whose `rollbackOnError` also reverted the tab and 3 list views that had already succeeded.

## 4c. n8n repointed to PROD — 24 August ✅

Salesforce credential on **every** Salesforce-authenticated node across all 7 workflows: Sandbox `8j2Z1Q8YwHHvR9nn` → **`quBZzjgLYxZSi9My`**.

**How that credential was chosen (not a guess):** the live production digest `LOA Work Items - Daily Digest` (`sEZI3Hg6CEYLFokc`, active, weekday 9am, links to `ruby-ruby-7485.lightning.force.com`) already uses it. `dsfRbykdxZPdoIte` — the other credential labelled "Salesforce - Prod" — is used by nothing live. **Still a personal login, not an integration user (F-16). The automation stops the day that password changes.**

| Change | Count | Documented estimate |
|---|---|---|
| Salesforce credential rebinds | **57** (52 salesforce nodes + 5 httpRequest with predefined SF cred) | — |
| Task record-type Id `012Em00000ANGRJIA5` → `012Qg000003uX4PIAU` | **5** | 4 |
| Instance URL staging pod → `ruby-ruby-7485.my.salesforce.com` | **5** | 4 |
| Default owner `005Em00000E99YfIAJ` → `005Kb00000B1HzJIAV` (It Support) | **2** | 1 |

### Three locations the cutover checklist did NOT list — correct the checklist
1. **WF-1 Path A `Create Wording Item`** — a 5th record-type Id, in `additionalFields.recordTypeId` (Path B uses `customFieldsValues`, so a search for the wrong shape misses it).
2. **WF-1 Path A `Plan Wording Item`** — a 2nd `DEFAULT_OWNER` in jsCode. The owner Id was documented as existing only in the Escalate sub's `Prep`.
3. **WF-1 Path B `Chatter Ask Agent`** — a 5th staging-pod URL.

**Lesson: search for the literal value across every workflow, don't work from the documented node list.** A per-node checklist built by hand missed 3 of 12 occurrences.

**WF-4 Inbound Dispatcher has zero Salesforce nodes** (Outlook trigger → Code → If → Data Table / Execute Workflow) and needed no changes.

### 🔴 THE PUBLISH TRAP — this nearly made the whole repoint cosmetic
WF-4 and Escalate & Notify were **active**. Editing an active workflow lands the change as an **unpublished draft**; the running version keeps the old values. After the repoint their drafts held prod credentials while their *active* versions still held **all 21 sandbox bindings and all 4 staging URLs** — i.e. live workflows still writing to the sandbox while every tool call reported success. Fixed by `publish_workflow` on both; verified `versionId == activeVersionId` (sub `6711449a…`, WF-4 `902fca68…`). **Any repoint of an active workflow is incomplete until it is republished and the version Ids match.**

### Current n8n state
| Workflow | Active | Points at |
|---|---|---|
| WF-4 Inbound Dispatcher | **NO** — deactivated deliberately as the safety gate | n/a |
| WF-4 Email Reply Handler | yes | **PROD** |
| Escalate & Notify (sub) | yes | **PROD** |
| WF-1 Path A / Path B / WF-2 / WF-5 | no | **PROD** |

The dispatcher is the only mailbox poller, so with it off **nothing processes inbound email**. Reactivating it resumes the whole inbound chain against production.

### ⚠️ GATE BEFORE ANY WF-2 RUN — `test_mode` cannot be verified via MCP
There is no MCP tool that reads Data Table rows, so `fur_settings.test_mode` **must be eyeballed in the n8n UI** (Data Tables → `fur_settings`, table `0A0KbAfzHmAHvhCl`) before WF-2 is ever run. It was `true` as of exec 324. With prod credentials bound and `test_mode = false`, a WF-2 run emails **real borrowers** using the placeholder templates — `NMLS #—` and a promised unsubscribe link that does not exist.

### Cosmetic, left alone deliberately
- **WF-5 `Build Digest` hardcodes the literal string "staging" twice** in the digest HTML header and footer. A production digest would be labelled staging.
- All 7 workflow names still end in **"(staging)"**, and the sub's staging name is cached in its three callers' `cachedResultName`.
- Hardcoded internal recipient `m.rodriguez@supremelending.com` in WF-4 `Notify Unmatched`, WF-4 + sub `Soft-Failure Alert`, WF-5 `Send Digest` — internal only, not borrower-facing.
- Outlook credential still `9SSXP90Befj1zdrm` (`itsupportaccount@simosolutionsgroup.com`) on 12 nodes. `docs@homesi.co` repoint remains a separate gated cutover step.

## 5. Demo posture

Per your instruction: prod Salesforce metadata is live, all four Salesforce flows are active, and **no n8n workflow is active** — WF-1, WF-2, WF-5 were never published, and WF-4 plus its dispatcher are still bound to the staging credential, so nothing polls or sends prod data. Outbound email fires only when you ask me to trigger a workflow manually.
