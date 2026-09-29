# Borrower Follow-Up System — PROD Cutover Checklist

**Status:** everything below is built + verified in **staging** (`homesi-staging`). Nothing is in prod yet.
**Cutover principle:** deploy the Salesforce data model + flows to prod → repoint n8n → flip `test_mode` off → activate workflows.
**Owner column:** `IT` = Claude/IT can do it · `YOU` = user/admin action · `LEAD` = leadership decision.

---

## 0. GATING BLOCKERS — do not go live until these are done

| # | Item | Owner | Why it blocks |
|---|---|---|---|
| 0.1 | **Real email templates + NMLS footer in WF-2** (Appendix-A copy). Current bodies are working placeholders. | YOU + IT | Real borrowers would receive draft copy with no compliance footer. **Hard stop.** |
| 0.1a | **Branding DECIDED 2026-08-11: sender display name `Homesi Docs`, and the email identifies Homesí as *powered by Supreme Lending*.** | YOU | Sets the voice of all 20 templates (10 steps x EN/ES). |
| 0.1b | **Compliance question on the footer: Homesí is a marketing brand, not the licensed lender.** The footer must name the licensed entity + its NMLS ID — `Everett Financial, Inc. dba Supreme Lending, NMLS #____` — alongside the Homesí branding. Confirm the exact required wording (and the NMLS ID) with compliance before templates are written. | YOU / compliance | An advertising email from an unlicensed-looking brand with no lender identification is a regulatory exposure, not a copy preference. Also confirm whether a state-license line and Equal Housing Lender logo/text are required. |
| 0.1c | **The footer currently promises "use the unsubscribe link to stop emails" but there is no link.** Decide: add a real unsubscribe mechanism, or change the wording to reply-STOP (which WF-4 already handles and propagates to the person's opt-out field). | YOU | Promising a control that does not exist is the kind of thing that gets quoted back at you. |
| 0.2 | **Integration user created in prod** (replaces the personal Salesforce login, design item F-16) + a NEW n8n Salesforce credential built on it. | YOU | Today the prod SF cred `dsfRbykdxZPdoIte` is a *personal* login. If that user is deactivated or their password rotates, every workflow dies. Also all record writes would show under a person's name. |
| 0.3 | **Sending mailbox — DECIDED 2026-08-11: Display name `Homesi Docs`, address `docs@homesi.co`** (Homesí = the Latino division, so the brand the borrower recognises). Replaces `itsupportaccount@simosolutionsgroup.com`. | YOU | WF-4 polls this same inbox to match replies, so outbound and inbound MUST be one mailbox. Sub-tasks below. |
| 0.3a | **`homesi.co` must be an accepted domain in the M365 tenant**, with SPF + **DKIM** + DMARC aligned for that domain. | YOU | Without DKIM for homesi.co, borrower mail lands in spam — Gmail/Yahoo bulk-sender rules require SPF+DKIM+DMARC alignment. |
| 0.3b | **Decide: licensed user mailbox vs shared mailbox.** RECOMMENDED: a sign-in-able (licensed) mailbox for `docs@homesi.co`. | YOU | n8n's Outlook credential uses an interactive OAuth sign-in, and WF-2 sends via `draft:create → draft:send` **in the credential's own mailbox** (the node sets no `from`). A licensed mailbox = authorize n8n directly as `docs@homesi.co`, send + receive natively match, no delegation. A shared (unlicensed) mailbox cannot sign in — it would need Full Access + **Send As** granted to a licensed service account AND a `from` parameter added to the send nodes (extra build + Reply-To handling). |
| 0.3d | **⚠️ The credential exists but the MAILBOX DOES NOT.** Repointing to `X9T7HveknhfWyJd5` on 2026-08-12 returned **`404 MailboxNotEnabledForRESTAPI`** and broke WF-4's inbound poll until reverted. **Staging stays on `itsupportaccount` + `test_mode` recipient override until the user explicitly says to switch.** Verify the mailbox answers Graph BEFORE repointing anything. | YOU | A dead mailbox on the WF-4 trigger fails silently — replies are simply never read. |
| 0.3c | **Create the n8n Outlook credential** for `docs@homesi.co`, then repoint: **WF-4 trigger** (inbound poll), **WF-2 `Create Draft` + `Send Draft`**, and optionally **WF-5 `Send Digest`** / alert senders. | IT | Miss the WF-4 trigger and replies are still read from the old inbox; miss WF-2 and borrower mail still sends from itsupportaccount. |
| 0.4 | **Pilot scope agreed:** one branch, 2–3 agents, agent-initiated follow-ups only. | LEAD | Prevents the whole org generating borrower email on day 1. |
| 0.5 | **Decide: should an AI Chatter post mark an Opp "contacted"?** Posting to an Opp feed fires the org's `Chatter to Contacted Flow`. | YOU | In prod that flow is ACTIVE and will run on every AI escalation post. Options: accept it, or drop Chatter on the Opp branch (Work Item + Needs Agent already deliver the handoff). |

> NOT blockers (Phase 2 only): 360 SMS API key, SMS-consent legal call, reactivation cutoff date. The pilot is **email-only**.

---

## 1. Salesforce — deploy metadata to PROD

Deploy order matters (objects → fields → flows → layouts → perms).

- [ ] **1.1 Objects**
  - [ ] `Follow_Up_Request__c` (+ ~23 fields) — include `<enableFeeds>true</enableFeeds>`
  - [ ] ~~`Requested_Document__c`~~ **RETIRED 2026-08-11 — do NOT deploy.** Documents are now `Mortgage_Condition__c` work items on both Lead and Opportunity (one data shape). The object was never deployed to prod, so there is nothing to migrate.
  - [ ] `Outbound_Message__c` (master-detail → FUR; `Message_Id__c` = Text(255) **External ID + Unique**)
  - [ ] ⚠️ When deploying any CustomObject header, include the FULL set of `enable*` flags (`enableReports`, `enableActivities`, `enableBulkApi`, `enableFeeds`, `enableHistory`, `enableSearch`, `enableSharing`, `enableStreamingApi`). Omitted flags revert to default — this previously disabled reports on `Mortgage_Condition__c` in prod.
- [ ] **1.2 Fields on `Mortgage_Condition__c`**: `Chase_With_Borrower__c`, `Borrower_Doc_Ask__c` (Text 255), `Follow_Up_Request__c` (lookup), `Chase_State__c`, `Chase_Status__c`, `Chase_Next_Touch__c`, `ContentDocument_Id__c`, `Doc_Type__c`, `Received_At__c`, `Chase_Latest_Note__c`
  - [ ] `Priority__c` and `Lead__c` **already exist in prod** — do NOT recreate.
- [ ] **1.3 Fields on Lead + Opportunity**: `AI_Followup_Request__c` (LTA 2000), `AI_Followup_Status__c` (Text 120), `Chase_Latest_Note__c`, `SMS_Consent_Source__c`, `SMS_Consent_At__c`
  - [ ] `Needs_Agent__c` **already exists on both** — do NOT recreate.
  - [ ] `HasOptedOutOfEmail__c` on **Opportunity already exists in prod** — do NOT recreate (staging was the one missing it). Lead uses the standard `HasOptedOutOfEmail`. Both are written by the opt-out propagation.
- [ ] **1.4** `Lead.Has_AI_Followup_Request__c` (Checkbox) + before-save flow `Set_Has_AI_Followup_Request` (LTA can't be SOQL-filtered — this checkbox is how WF-1 polls)
- [ ] **1.5 Flows** (2-phase activate each if it lands Draft in prod)
  - [ ] `Repoint_FUR_On_Lead_Convert` — re-points FURs + Work Items from Lead → new Opp on conversion.
  - [ ] `Clear_Next_Touch_On_FUR_Stop` — **NEW.** Before-save on the FUR: if Status is Cancelled/Completed/Dead/Opted Out/Escalated, blanks `Next_Touch_At__c` so a manual stop takes it out of the cadence in one field change.
  - [ ] `Resume_FUR_On_WorkItem_Complete` — **NEW (pre-pilot fix).** When an agent completes an "AI Follow-Up" work item, the follow-up resumes: Awaiting Reply, +1 cadence step, Next Touch +1 business day, escalation cleared, `Needs_Agent__c` unticked. Runs in system mode (expected Info warning on deploy).
- [ ] **1.6 FUR tab + list views**: CustomTab `Follow_Up_Request__c` + `Open_FURs`, `Escalated`, `All_FURs` + profile tab visibility.
  - ⚠️ ListView filter child element is `<operation>`, NOT `<operator>`.
- [ ] **1.7 FUR classic layout** + 3 related lists (`Mortgage_Condition__c.Follow_Up_Request__c`, `Requested_Document__c.Follow_Up_Request__c`, `Outbound_Message__c.Follow_Up_Request__c`), New button excluded.
- [ ] **1.8 Permission set** `Borrower_Follow_Up_Integration` (all FLS incl. `Priority__c`, `Due_Date__c`, `Latest_Note__c`, `Lead__c`)
  - [ ] **ASSIGN it to the integration user.** Deploying the permset is not enough — unassigned FLS = `INVALID_FIELD: No such column` at runtime.
  - [ ] ⚠️ `Status__c` on `Mortgage_Condition__c` is a *required* field — FLS cannot be granted via permset (it errors). It's always accessible.
- [ ] **1.9 Record type assignment (PROFILE-only, permsets can't do this):** the integration user's **profile** must have `Mortgage_Condition__c` → **Task** record type assigned, or work-item creation fails `INVALID_CROSS_REFERENCE_KEY`.
- [ ] **1.10a AI FIELDS — FLS, and do NOT assume it came along.** The n8n permission set covers only the *integration* user. Every agent-facing AI field needs FLS on the **13 human working profiles** as well:
  - [ ] `Lead.AI_Followup_Request__c` — **read + edit** (this is the box the agent types in)
  - [ ] `Opportunity.AI_Followup_Request__c` — read + edit (when the Opp box is added)
  - [ ] `Lead.AI_Followup_Status__c` — **READ ONLY** (system-written; an agent editing it corrupts the `NEEDS DETAIL #<fingerprint>` retry gate)
  - [ ] `Opportunity.AI_Followup_Status__c` — read only
  - [ ] `Lead.Has_AI_Followup_Request__c` — read only (system checkbox, no need to expose for edit)
  - [ ] `Needs_Agent__c` on Lead + Opportunity — read + edit (agents may want to clear it manually)
  - [ ] `Mortgage_Condition__c`: `Chase_With_Borrower__c` **read + edit** (the LOA's start switch), `Borrower_Doc_Ask__c` / `Chase_Latest_Note__c` / `Chase_State__c` read
  - ⚠️ **In staging these had FLS on only 3 non-human parents** (integration permset + 2 read-only web/webhook profiles). Left as-is in prod, agents would not see the request box at all — it only looks fine when testing as an admin.
- [ ] **1.10 STANDING FLS RULE:** every new custom field gets read+edit FLS on all **13 human working profiles** (Agent, Agent Loa On-Demand, Agent Recruiter, Agent Sales, Agent TPO, Branch Manager, Branch Manager AA084, LO Profile, LOA Profile, Only_assignment, Sales agent Profile, Supervisor, Supervisor Sales).
  - [ ] ⚠️ Prod has **TWO profiles named "System Administrator."** The login one is `00eKb000000aw4EIAQ` (owned PermissionSet `0PSKb0000019iVGOAY`). Name-based metadata deploys hit the *other* one — write admin FLS straight to the PermissionSet by Id.
- [ ] **1.11 Page layouts / record pages** (YOU)
  - [ ] AI Follow Up Request tab/section on the **Lead** page — *already done in prod*
  - [ ] Same request box on the **Opportunity** page
  - [ ] **Borrower Follow-Ups** related list on Opportunity + Lead
  - [ ] FUR Lightning record page + component visibility
- [ ] **1.12** Confirm **Chatter feed tracking** is ON for Opportunity + Lead (standard objects, usually on) — required for the escalation @mention.
- [ ] **1.13 Deploy note:** for **non-Apex** prod deploys, OMIT the test level entirely (prod has pre-existing failing local tests; `NoTestRun` is rejected in prod).

---

## 1b. Salesforce — PAGE LAYOUTS / RELATED LISTS (nothing is visible without these)

Every one of these records is created correctly today and **invisible on the record it belongs to**. This is the single most likely cause of "the automation isn't doing anything" at pilot.

- [ ] **1b.1 Borrower Follow-Ups** (`Follow_Up_Request__c` via `Lead__c`) on the **Lead** page layout — without it, an agent types in the request box, a FUR is created, and they see nothing happen. They will type it again.
- [ ] **1b.2 Borrower Follow-Ups** (via `Opportunity__c`) on the **Opportunity** page layout
- [ ] **1b.3 Work Items** (`Mortgage_Condition__c` via `Lead__c`) on the **Lead** page layout
- [ ] **1b.4 Files** on the **Lead** and **Opportunity** layouts — required for the ambiguous-reply attachment rescue to be *visible*. The `ContentDocumentLink` is created either way, so without this the document is in Salesforce and unfindable.
- [ ] **1b.5 Outbound Messages** (`Outbound_Message__c` via `Follow_Up_Request__c`) on the FUR layout
- [ ] **1b.6 Chase Conditions** (`Mortgage_Condition__c` via `Follow_Up_Request__c`) on the FUR layout
- [ ] **1b.7 Related-list columns.** A related list showing only Name displays the thread token (e.g. `FUR-MSTD2VKY0`) and nothing else. Add at minimum **Type** and **Status**; `Next_Touch_At__c` is what distinguishes "still cadencing" from "stopped".
- [ ] **1b.8 `Outcome__c` picklist value `Chase Cancelled`** must exist in prod (restricted picklist). WF-2 writes it when an agent calls off a chase; without it the update fails.
- [ ] Related-list metadata token for a custom child is `<ChildObject>.<LookupField>` (e.g. `Mortgage_Condition__c.Follow_Up_Request__c`) — NOT the relationship name. `<excludeButtons>New</excludeButtons>` works; `ChangeOwner` is rejected at related-list level.

**Found in the staging UI 2026-08-20 while capturing guide screenshots** (all four are things an agent would see):

- [ ] **1b.9 Remove the "Requested Documents" related list from the FUR layout.** It still renders on the Borrower Follow-Up page (observed as "Requested Documents (0)"), but `Requested_Document__c` was **retired** — every requested document is a Work Item now. It will always read (0), which teaches agents that the system isn't tracking their documents. The guide explicitly tells them this list no longer exists, so leaving it in contradicts the documentation.
- [ ] **1b.10 Rename the Lead "AI Follow Up Request" tab section from "Section".** The field section on that tab is labelled literally `Section`. Cosmetic, but it is the first thing a Sales Agent sees on the screen they use most.
- [ ] **1b.11 Remove `New` and `Import` from the Borrower Follow-Ups list-view buttons.** The list view currently offers New / Import / Change Owner / Printable View. A hand-created FUR has no thread token, no cadence step and no parent record, so it would sit in the poll doing nothing — or worse, be picked up half-formed. Agents start follow-ups from the request box or the Chase With Borrower tick, never here. (`searchLayouts` is replace-all — see the Salesforce CLAUDE.md gotcha before deploying.)
- [ ] **1b.12 Confirm `AI_Followup_Status__c` placement carried to prod.** It IS on the staging Lead layout (above the request box, rendering its value) — the older note calling it "displayed nowhere" is stale. Verify prod matches, and grant it **read-only** to agents: an agent editing it corrupts the `NEEDS DETAIL #<fp>` fingerprint gate.

---

## 2. n8n — repoint from staging to prod

Workflows: WF-1 Path A `bfvPz2pwKQnK8ozG` · Path B `NQBD7I86IlIsj47Z` · WF-2 `nG8hwck9RsoJZiQb` · WF-4 `7nVnALsJHaPseTVt` · **WF-4 Inbound Dispatcher `pA2IVtxuaTyFIQGK`** · WF-5 `vNLsXCapVmrP5GIC` · Escalate & Notify `vJKvJpOZUxrhqOKY`

> ⚠️ **ARCHITECTURE CHANGED 2026-08-17 — WF-4 NO LONGER POLLS THE MAILBOX.** A dispatcher sits in front of it: Outlook trigger → auto-reply screen → Execute Sub-workflow → WF-4 with `mode: each`, one execution per email. WF-4's trigger is now an `executeWorkflowTrigger` (deliberately still named `New Email (docs inbox)` so `Get Attachments` / `Download Attachment` resolve unchanged). Consequences for cutover: **the mailbox repoint is on the DISPATCHER, not WF-4**, and **if the dispatcher is ever deactivated, inbound mail silently stops being processed**.
>
> `FUR TEST - Inbound Email Simulator` (`66oCRAyOwmBfwLnk`) is a **test harness only — do NOT activate in prod.** It sends simulated borrower replies into the mailbox.

- [ ] **2.1 Create the prod Salesforce credential** on the new integration user (§0.2). Do NOT reuse the personal `Salesforce - Prod` cred.
- [ ] **2.2 Swap the credential on EVERY Salesforce node** in all 6 workflows (staging `8j2Z1Q8YwHHvR9nn` → new prod cred). Includes HTTP nodes using the *predefined* Salesforce cred.
- [ ] **2.3 Hardcoded staging values to change:**
  - [ ] Chatter/REST URLs: `ruby-ruby-7485--staging.sandbox.my.salesforce.com` → `ruby-ruby-7485.my.salesforce.com` — in **Escalate & Notify** (`Chatter @mention`) AND **WF-4** (`Flag Needs Agent`, `Chatter Record`, **`Propagate Opt-Out`**). That's 4 nodes across 2 workflows — miss one and it silently writes to (or fails against) the sandbox.
  - [ ] `Mortgage_Condition__c` **Task record-type Id**: `012Em00000ANGRJIA5` → prod RT Id (in `Create Work Item (Opp)` and `Create Work Item (Lead)`)
  - [ ] Default owner fallback user Id `005Em00000E99YfIAJ` (staging) → prod integration/fallback user Id (in `Prep`)
- [ ] **2.4 `fur_settings` data table:** set **`test_mode = false`**. (This is the single switch that stops redirecting all borrower email to the test address.)
- [ ] **2.5 WF-5 digest recipient:** `m.rodriguez@supremelending.com` → the real sales-leads/ops list.
- [ ] **2.6 Mailbox:** if moving to `docs@`, create the Outlook credential and repoint **the DISPATCHER's Outlook trigger** (`pA2IVtxuaTyFIQGK` — *not* WF-4, which no longer polls) + WF-2's `Create Draft` / `Send Draft`. Optionally WF-5 `Send Digest` and the alert senders, though those are internal-only and can stay on itsupportaccount.
  - Also repoint the **dispatcher's `Get Unrouted Attachments` / `Download Unrouted Attachment`** and WF-4's `Get Attachments` / `Download Attachment` — they use the same Outlook credential to fetch files from the polled mailbox.
- [ ] **2.6a Anthropic credit monitoring.** The Anthropic key ran out of credit during staging testing and **every AI node failed instantly** — WF-4 executions errored on `Classify Reply`, so inbound replies stopped being processed. In prod that is an outage with no obvious cause. Set a billing alert, and note that the shared Error Alert workflow *does* fire on it (that is how it was caught).
- [ ] **2.6b `fur_question_log` columns.** The table gained `has_attachments` (boolean) and `message_id` (string) on 2026-08-17. Same n8n instance, so nothing to deploy — just don't drop them.
- [ ] **2.7 Review `fur_cadences`** (day offsets, channels, exhaust actions) — config lives in n8n, editable without redeploy.
- [ ] **2.8 Confirm Error Workflow** = `Error Alert (shared)` `5gSRY0P5hpfLKmFD` on all 6 workflows (already set in staging; verify after any rebuild).
- [ ] **2.9 Publish + ACTIVATE:** WF-1 Path A, WF-1 Path B, WF-2, WF-5 (all **INACTIVE**; WF-5 has never been published at all — `activeVersionId` is `null`). WF-4, the **Dispatcher**, and Escalate & Notify are already active.
  - ⚠️ Publish the **sub-workflow first** — a caller can't publish while a referenced sub-workflow is unpublished. Same applies to WF-4 before the Dispatcher.
  - ⚠️ **The Dispatcher must be active or no inbound mail is processed at all.** WF-4 has no trigger of its own. Add this to the runbook / monitoring.
  - ⚠️ Do **NOT** activate `FUR TEST - Inbound Email Simulator` (`66oCRAyOwmBfwLnk`).
- [ ] **2.10 Verify the strict exhaust-action config.** WF-5 now matches `exhaust_action` **exactly** and **throws** on anything unrecognised (chosen deliberately 2026-08-18). Valid values are exactly `Escalate`, `Dead_Lead_OnHold`, `Close_NoResponse`. `fur_cadences` is free text with no validation, so a helpful-but-non-canonical value like `Escalate to LOA2`, or one extra underscore in `Dead_Lead_On_Hold`, will fail the close-out branch for that run. Check all four exhaust rows before activating WF-5.
- [ ] **2.11 Consider making `Thread_Token__c` required** (or add a validation rule). A FUR with a blank thread token previously became the accidental catch-all for every no-token inbound email. The code now guards against it, but the data shape that caused it is still creatable by hand.

---

## 3. Smoke test in prod (before telling agents to use it)

Run these in order, on ONE pilot record, with `test_mode` still **true** if you want a dry run first.

- [ ] **3.1** Type a request in the box on a pilot Lead → confirm a FUR is created (Borrower Follow-Ups tab) with the right Type/Cadence.
- [ ] **3.2** Confirm the outbound email actually sends and looks right (real template + NMLS footer). Check the `Outbound_Message__c` child row was created.
- [ ] **3.3** Reply as the borrower with `[FUR-xxx]` in the subject + an attachment → file lands on the record's Files; status → Docs Partial.
- [ ] **3.4** Reply with a question → FUR Escalated + **Work Item** created (High, borrower's words in Latest Note) + **Needs_Agent** ticked + **Chatter @mention** posted. Confirm the Chatter-to-Contacted side effect is what you decided in §0.5.
- [ ] **3.5** Reply from the borrower's on-file address with **no** token → confirm it still matches (email rung) or lands as Unmatched with the notification email.
- [ ] **3.6** Convert the pilot Lead → confirm FUR + Work Items re-point to the new Opportunity.
- [ ] **3.6a Escalation resume:** complete the AI Follow-Up work item from §3.4 → confirm the FUR goes Escalated → Awaiting Reply, cadence step +1, Next Touch = +1 business day, and `Needs_Agent__c` unticks.
- [ ] **3.6b Opt-out:** reply "stop / remove me" → confirm the FUR goes Opted Out **and** `HasOptedOutOfEmail__c` is ticked on the Opportunity (or `HasOptedOutOfEmail` on the Lead). Confirm no further email goes out.
- [ ] **3.7** Run WF-5 manually once → confirm the digest email arrives at the real recipient list and that it closes out **zero** healthy FURs.
- [ ] **3.7a AI FIELD FLS VERIFICATION — run this query and read the result, do not trust the deploy log.** A profile deploy can report success and still miss the field (and prod's duplicate "System Administrator" makes name-based deploys land on the wrong profile):
  ```sql
  SELECT Field, Parent.Profile.Name, PermissionsRead, PermissionsEdit
  FROM FieldPermissions
  WHERE Field IN ('Lead.AI_Followup_Request__c','Lead.AI_Followup_Status__c',
                  'Opportunity.AI_Followup_Request__c','Opportunity.AI_Followup_Status__c',
                  'Mortgage_Condition__c.Chase_With_Borrower__c')
  ORDER BY Field
  ```
  Expect a row for **each of the 13 human profiles** per field (status fields read-only). Anything less means some agents are blind to it.
- [ ] **3.7b Prove it as a real user, not as an admin.** Log in as (or use Login-As on) one **Sales agent Profile** user and one **Agent Loa On-Demand** user and confirm they can actually SEE: the request box on the Lead, the AI Follow-Up Status underneath it, `Chase_With_Borrower__c` on an Opportunity condition, and their Work Items list. Admin visibility proves nothing here.
- [ ] **3.8** Force a failure (e.g. bad cred momentarily) → confirm the Error Alert email arrives.
- [ ] **3.9 Multi-email fan-out.** Send **two** borrower replies within the same minute → confirm **two** separate WF-4 executions. This was a live data-loss bug (only the first email was processed, the rest silently discarded); the dispatcher fixes it, but it is the single most important thing to re-prove in prod.
- [ ] **3.10 Auto-reply guard.** Send a reply whose subject starts `Automatic reply:` → confirm it is **dropped**, logged to `fur_question_log` with `intent = auto_reply_skipped`, and produces **no** WF-4 execution. Then confirm a normal reply in the same window still processes.
- [ ] **3.11 Ambiguous reply with an attachment.** From an address on a record with **two** open FURs, send a **no-token** reply with a file → confirm no FUR is touched, `Needs_Agent__c` is ticked, Chatter says the attachment was uploaded, and the **file appears on the Lead/Opportunity Files list** (requires §1b.4).
- [ ] **3.12 Junk-mail sanity.** Watch the mailbox for a day. If marketing mail, OTP emails or Microsoft notifications are arriving, they will each be classified and escalated as borrower replies (this happened in staging and drained the AI credits). This is the strongest argument for `docs@homesi.co` being a **dedicated** mailbox rather than a shared IT inbox.

---

## 4. Known gaps you are launching WITH (accept or fix first)

| Gap | Impact at pilot | Recommendation |
|---|---|---|
| ~~No resume after escalation (F-13)~~ | — | ✅ **FIXED 2026-08-11.** `Resume_FUR_On_WorkItem_Complete` flow, verified live in staging. Deploy to prod (§1.5). |
| ~~Opt-out not propagated to the person~~ | — | ✅ **FIXED 2026-08-11.** WF-4 now sets `HasOptedOutOfEmail__c` (Opp) / `HasOptedOutOfEmail` (Lead). **SMS opt-out still NOT propagated** — the managed-package field isn't API-visible to the integration user, and one bad field fails the whole update. Add in Phase 2 after granting FLS. |
| **No doc-level verification (WF-4 v3)** | Attachments are filed and the FUR marked "Docs Partial"; the system doesn't know *which* requested doc arrived, and won't auto-complete. | Acceptable — a human confirms. Build v3 after pilot. |
| **No FAQ auto-reply** | Every borrower question escalates to a human. | Deliberate. Mine `fur_question_log` after the pilot to build high-precision FAQ entries. |
| **No frequency cap / 4h dedupe in WF-2** | Low risk at pilot volume (one follow-up per borrower). | Build before scaling. |
| **State→timezone map not built** | Quiet hours use Eastern for everyone. | Fine for a single-branch pilot. |
| **Multi-intent replies** | "Here's my doc + a question" may be classified as one intent; the text is still logged for a human. | Acceptable at pilot. |
| **Opp `IsClosed` guard not on the email match rung** | A no-token reply could match a FUR still open on a closed loan. | Low risk; add with the close-on-Opp-close rule. |
| **Nothing closes FURs when an Opp closes** | Stale open FURs accumulate on funded/lost loans. | WF-5 stale rule catches them in 14 days. Add an explicit rule later. |

---

## 5. Rollback plan

- [ ] **Fastest kill switch:** set `fur_settings.test_mode = true` → all borrower sends redirect to the test address instantly (no deploy, no deactivation).
- [ ] **Full stop:** deactivate WF-1, WF-2, WF-4, WF-5 in n8n. Salesforce data stays intact; no borrower is messaged.
- [ ] **Emergency flow kill (Salesforce):** deploy the FlowDefinition with `<activeVersionNumber>0</activeVersionNumber>` — instant, non-Apex, reversible.
- [ ] Salesforce records (FURs, work items) are additive — leaving them in place is harmless if you pause the engine.

---

## 6. Post-cutover backlog (in priority order)

1. **SMS opt-out propagation** — add `tdc_tsw__SMS_Opt_out__c` to the consent update once FLS is granted to the integration user (email opt-out already ships).
2. **WF-4 v3**: Claude-vision doc classification → match to the requested item → per-item receipt math → auto-complete. (**Multi-intent replies are DONE** — built and verified live 2026-08-19, exec 388; no longer part of v3.)
3. **FAQ auto-reply** from mined `fur_question_log` entries (templates only, never free-formed; no rates/terms/approvals).
4. **WF-2 hardening**: frequency cap, 4h dedupe, state→TZ map, AI personalization.
5. **Token optimization** before scale: wording cache keyed on normalized condition text + switch that step to Haiku (see n8n CLAUDE.md §9).
6. **Phase 2**: WF-3 (inbound SMS) + WF-6 (reactivation drip) — both need the 360 SMS key + the consent legal call.
7. Refresh the user-guide screenshots against clean prod demo records. **The guide TEXT is current** — `Borrower_FollowUp_Agent_Guide_v10.docx` was reconciled against the as-built system on 2026-08-19 (changelog in `FUR_START_HERE.md`). Only the 10 screenshots are still from staging, and they are labelled as such on the cover.
   - ⚠️ **Do not distribute the guide until §1 FLS and the page-layout placements are done.** It instructs agents to read `AI Follow-Up Status` and to set a follow-up's `Status` to Cancelled — neither is visible or editable for the 13 working profiles yet.

---
*Generated from the as-built staging system. Companion docs: `CLAUDE.md` (n8n side), `Salesforce Workspace/CLAUDE.md`, `Borrower_FollowUp_System_Design.md`, `Borrower_FollowUp_Agent_Guide_v10.docx`.*
