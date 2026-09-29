# Borrower Follow-Up — Bucket 2 & 3 Checklist

**Created 2026-08-12.** Companion to `CLAUDE.md`. Bucket 1 (breaks the loop / false success) is **COMPLETE** — see the bottom section for what was actually fixed vs. what turned out to already be done.

> **Read this first:** every item below was re-verified against the live workflows on 2026-08-12. Items marked ✅ VERIFIED FIXED were listed as OPEN in `CLAUDE.md` but are already built. Do not re-fix them. Trust this file over `CLAUDE.md`'s OPEN list until that file is reconciled.

---

## 2026-08-17 UPDATE — branch-coverage campaign findings

Three new workflows/behaviours and four bugs found by live testing. **WF-4's architecture changed** — read this before touching it.

### WF-4 no longer polls. There is a dispatcher in front of it.

- **`FUR WF-4 Inbound Dispatcher` (`pA2IVtxuaTyFIQGK`)** — Outlook trigger → `Screen Auto-Replies` → `Auto-Reply?` → `Log Skipped Auto-Reply` / `Process One Email` (Execute Sub-workflow → WF-4, **mode each**).
- **WF-4's trigger is now an `executeWorkflowTrigger` named `New Email (docs inbox)`** — the name was preserved deliberately so `Get Attachments` and `Download Attachment`, the only two nodes that reference it, needed no change.
- [ ] **RUNBOOK ITEM: if the dispatcher is deactivated, inbound mail silently stops being processed.** WF-4 has no trigger of its own any more.
- [ ] **CUTOVER CHANGE: the mailbox repoint is now on the DISPATCHER**, not WF-4. Cutover = dispatcher's Outlook credential + WF-2's `Create Draft`/`Send Draft`. Simpler than before.
- **`FUR TEST - Inbound Email Simulator` (`66oCRAyOwmBfwLnk`)** — sends borrower-style replies from itsupportaccount to itself so WF-4 is testable without a human sending mail. Set `ACTIVE` in `Build Test Emails` to pick scenarios. **It cannot attach files** — attachment tests must be sent by hand.

### FIXED 2026-08-17 — WF-4 dropped every reply but the first in each poll

`Extract Match Keys` did `$input.first()` and returned a single item, so a poll returning 5 emails processed 1 and **silently discarded 4**, with a success status and the polling watermark moved past them permanently. Proven live exec 328 (5 in, 1 processed); fixed via the dispatcher; verified exec 331/332/334/336/337 (5 in, **5 executions**). This mattered because WF-2 sends in batches, so replies cluster.

### FIXED 2026-08-17 — a blank subject token matched a real FUR

`Match by Token` ran `WHERE Thread_Token__c = '{{ $json.token }}'` and **SOQL treats `= ''` as matching NULL**. Exactly one FUR had a null token (`a1KEm00001TOh5pMAD`, junk from the Path B leak bug), so *every* no-token email matched it as `matchSource: 'token'`. Fixed with two guards (query requires non-null; `Resolve Match` skips the rung when the token is empty) and verified exec 357 with the junk FUR still present. Junk FUR now Cancelled.

- [ ] **Root-cause follow-up: any FUR created without a `Thread_Token__c` instantly becomes a catch-all again.** Consider making Thread_Token required, or a validation rule.

### The mailbox was eating unrelated mail — and this is the real argument for `docs@homesi.co`

Because of the two bugs above, **every email in the itsupportaccount inbox was classified by Claude and escalated as a borrower reply** between 12–17 Aug: Claude marketing mail, a Claude.ai OTP login email (Spanish), Microsoft admin-consent requests, a team-join notification, QR-code spam, and an out-of-office auto-reply. Each burned an AI call and raised a false escalation. **This is very likely what exhausted the Anthropic credits.**

- [x] **F-4 auto-reply / OOO guard — BUILT 2026-08-17.** Lives in the dispatcher so junk never starts a WF-4 execution or spends a Claude call. Detects generated subject prefixes (EN + ES) and no-reply/system senders. **Deliberately NOT body-based** — a borrower writing "I'll be out of the office next week" is a real reply. Skips are logged with `intent = auto_reply_skipped`. Verified: 3 emails → 2 dropped+logged → 1 processed, and both auto-replies carried VALID tokens and were still refused.
- [ ] **Hardening: the rigorous version checks the `Auto-Submitted` / `X-Auto-Response-Suppress` headers**, which the Outlook trigger's `fields` output omits (needs a Graph header fetch). Add only if leakage is seen.
- [ ] **No sender allowlist.** WF-4 processes anything that arrives. Decide whether unknown senders should be dropped rather than escalated. `docs@homesi.co` being dedicated largely removes the need.
- [ ] **`itsupportaccount` is the wrong long-term mailbox** — it is a general-purpose IT account and will always receive non-borrower mail.

### BUILT 2026-08-17 — attachments on unroutable replies are no longer lost

The attachment chain hung only off `Update FUR` (matched path), so an ambiguous or unknown-sender reply carrying the borrower's documents had its text triaged and its **file left in the mailbox**, with nothing even mentioning an attachment existed. Now: a parallel branch off `Chatter Record` uploads to the **Lead/Opportunity Files list** when a single record was identified; the Chatter text states whether files were uploaded or must be fetched; `fur_question_log` gained **`has_attachments`** (boolean) and **`message_id`** columns. Both new nodes are covered by `Soft-Failure Check`, which gained a "DOCUMENT NOT FILED" escalation line.

- [ ] **Needs verification with a real attachment** — the simulator cannot attach files. Send one matched (`[FUR-xxx]` in subject) and one ambiguous (no token) reply with a file.

### FIXED 2026-08-18 — Reactivation exhaust escalated instead of closing

`WF-5 Decide Close-out` mapped exhaust actions with a substring regex `/dead/i`. `Dead_Lead_OnHold` matched by luck; **`Close_NoResponse` did not, so exhausted Reactivation FURs were escalated to a human** instead of closed. Worse, there was **no unknown-action branch at all** — any typo, any newly added cadence, or a cadence missing from `fur_cadences` silently became Escalated, so a config mistake quietly created work items with no signal.

Now: exact-match vocabulary accepting the existing values (`Escalate`, `Dead_Lead_OnHold`, `Close_NoResponse`) so **no data migration was needed**; an unrecognised or blank action **throws** so the shared Error Alert fires; and `Poll Open FURs` gained `Opportunity__c` / `Lead__c`.

**VERIFIED LIVE exec 382, two purpose-built fixtures:** `FUR-REACT-LEAD` (Reactivation on a Lead) → **Dead / No Response** (previously Escalated); `FUR-REACT-OPP` (same cadence, on an Opportunity) → **Escalated** with the reason *"cadence would close this, but it is attached to an open loan - routed to a human"*.

- [x] **SAFETY FLOOR added:** never mark a FUR Dead when there is an open Opportunity behind it. The config decides by cadence (and already encodes stake correctly — Docs/Appointment escalate, Interest/Reactivation close); this is only a backstop against a cadence being misconfigured in a way that would quietly abandon a real loan. Deliberately NOT a stake-based override of the config, which would have created two competing sources of truth.
- [x] **Decided 2026-08-17: do NOT escalate every exhaust.** Cold-outreach non-responders should close, not create work items — otherwise a 300-lead reactivation campaign generates ~270 High-priority items and agents learn to ignore the whole category, including the Docs ones that matter.
- [x] **Decided 2026-08-17: closing means closing the FUR only — never the Lead.** No Lead status write, no Discarded. `branch_mandatory_validation_rule` would block Working/On-hold/Discarded when Branch is blank, and lead status is sales-owned.
- [x] **Decided 2026-08-18: keep the unknown-action behaviour STRICT (throw), and observe.** Chosen over the softer alternatives with eyes open. **Known tradeoffs:**
  - One mistyped config row fails the whole close-out branch for that run, delaying FURs that would have closed fine. Nothing is lost — WF-5 runs daily and catches up once the row is fixed. The digest branch hangs off the trigger independently, so visibility survives.
  - **Exact matching is more brittle than the regex it replaced in one specific way:** `Dead_Lead_On_Hold` (one extra underscore) now throws, whereas the old `/dead/i` would have handled it. Same for a descriptive value like `Escalate to LOA2`.
  - `fur_cadences` is **free text in the n8n UI** — no dropdown, no validation — so a helpful-but-non-canonical value is the most likely trigger. Valid values are exactly: `Escalate`, `Dead_Lead_OnHold`, `Close_NoResponse`.
  - [ ] **If it proves annoying in practice**, the fallback design is: forgiving match (contains `escalat` → escalate; contains `dead` / `close` / `no response` → close) with an explicit unknown branch, plus skip-the-bad-row-and-continue instead of throwing. That keeps the alarm while tolerating near-misses.
- [ ] **Consider validating the config at source** rather than only reacting downstream — e.g. document the three valid values in the table, or add a startup check that reads `fur_cadences` and alerts on any unrecognised `exhaust_action` before a borrower is affected.

### Cadence config observations (from reading the live table 2026-08-18)

- [ ] **`Reactivation` runs longer than `Docs Standard`** — 14 days / 3 touches vs 12 days / 4 touches. A cold lead is chased over a longer window than a live loan's document chase. Probably not intentional; revisit when the real cadences are set.
- [ ] **Five rows specify `SMS_or_Email` / `Email_SMS` but SMS is not built.** WF-2 only tests `channel === 'exhaust'`; everything else sends email. So enabling SMS in Phase 2 will **silently change behaviour on existing cadences** rather than requiring a config change. Decide deliberately before switching SMS on.

### Unattended-running status has CHANGED

Bucket 3's headline ("nothing has ever run unattended") is now **partly out of date**: the dispatcher + WF-4 have run unattended on a 1-minute poll across 16–17 Aug, processing real inbound mail. **WF-1 Path A, WF-1 Path B, WF-2 and WF-5 are still INACTIVE** and have only been run manually. The soak proposal still stands for those four.

---

## BUCKET 2 — borrower-visible wrongness

Does not break the cadence loop. Does embarrass you in front of a borrower. Build during the soak week.

### Send gates that were designed but never built

> ### ⚠️ THE CONFIG LOOKS ENFORCED AND ISN'T (traced 2026-08-19)
>
> `Build Messages` reads only **5 of the 12** `fur_settings` keys: `test_mode`, `test_email`, `fallback_tz`, `quiet_start_hour`, `quiet_end_hour`. **Verified by tracing every reference in the jsCode.**
>
> These seven are present in the table, already populated, and **silently ignored**:
> `freq_cap_email_24h` (currently **1**) · `freq_cap_sms_24h` (**1**) · `dedupe_hours` (**4**) · `jitter_start_hour` (**9**) · `jitter_end_hour` (**11**) · `send_days` (**Mon-Sat**) · `reactivation_daily_cap` (**100**)
>
> This is worse than "not built". Anyone reading `fur_settings` would reasonably conclude a one-email-per-day cap is enforced, because the value is right there. **Whoever operates this will be misled.** Either implement the gates or add a comment column marking the unread keys as not-yet-wired.

- [ ] **Frequency cap — ≤1 email per person per 24h.** Spec calls this a hard send-gate. **Not built** (`freq_cap_email_24h` is set but never read). Needs a cross-FUR query — the cap keys on the *person* (email+phone), not the record id, per F-7. A borrower with two open FURs currently gets two emails the same morning.
- [ ] **4-hour dedupe.** `dedupe_hours = 4` is set but never read. Unbuilt.
- [ ] **`send_days = Mon-Sat` is not read either.** `Build Messages` hardcodes the weekend rule as `wd === 'Sun'`, so the setting has no effect. Changing it does nothing.
- [ ] **Quiet hours are single-timezone.** `Build Messages` computes `blockedByQuiet` from `fur_settings.fallback_tz` (ET) for **every** borrower. A Pacific borrower can receive mail at 6am local. Needs the state→TZ map the design calls for, with ET as fallback only.
- [ ] **9–11am jitter** — designed, not implemented. `jitter_start_hour` / `jitter_end_hour` are set but never read.

### Data / routing wrongness

- [x] **DOWNGRADED 2026-08-19 — `Owning_Role__c` is WRITE-ONLY. No runtime effect.** Path A hardcodes `LOA1` and Path B writes `Sales Agent`, but a trace of all seven workflows found **zero readers**: no SOQL selects it, no jsCode mentions it, nothing routes, filters or branches on it. So Path A's arguably-wrong `LOA1` on LOA2-stage work is a **reporting/data-quality** wart, not a defect. Fix it if you plan to report on the field; otherwise it is cosmetic.
- [x] **CLOSED 2026-08-19 — "Path A writes blank asks without unticking" is NOT a defect. Do not "fix" it by unticking.**

  Path A still writes `ask: sendable ? ask : ''` and leaves `Chase_With_Borrower__c = true`. The original note here proposed unticking the row as the root-cause fix. **That would have been actively wrong**, and would have regressed the blank-ask work already done:

  - `Get Unchased Conditions` selects `Is_Complete__c = false AND Chase_With_Borrower__c = false`, and `Build Messages` turns that into `outcome = 'Chase Cancelled'`.
  - So unticking a blank-ask row would make WF-2 complete the FUR as **"Chase Cancelled"** — asserting the agent called the chase off when they never did. A false record of why a document was never collected.
  - It would also zero `blankAsk`, disabling the `Needs Wording?` escalation guard and the new needs-wording work item, since both key on `Chase_With_Borrower__c = true`.

  **Keeping the tick ON is the correct semantics:** the LOA genuinely does want this chased, the robot simply cannot word it yet. Automation must not silently reverse a human's stated intent.

  The state `open + ticked + blank ask` is now fully accounted for: detected by `Get Blank-Ask Conditions`, prevented from causing false completion by `Needs Wording?`, and surfaced to a human by the Path A needs-wording work item. The only thing left is that WF-2 needs three condition queries rather than two — a design wart with no consequence, not a bug.
- [x] **FIXED 2026-08-19 — partial blank-ask no longer silent.** WF-2's `Needs Wording?` only fires when `docCount == 0`, so a FUR with 2 worded + 1 un-worded condition sent the email with 2 items and the third was never chased. The un-worded row *was* visible in the Work Items list but **indistinguishable**: Priority Normal, `Due_Date__c` **null** (so it dropped out of Due Today / This Week / Overdue — the views agents work from), and `Latest_Note__c` empty, with the only explanation in `Chase_Latest_Note__c`. Path A now mirrors Path B: a separate **High**-priority work item, due +1bd, owned by the LOA who ticked the box, deduped **one per FUR** (3 un-wordable conditions → 1 item), note stating explicitly that *"the follow-up email is going out WITHOUT them."* **VERIFIED LIVE exec 387** — 2 un-wordable conditions produced exactly 1 item (`a1IEm00000AQXc6MAH`).
  - Deliberately **NOT** named `AI Follow-Up…`: that prefix would collide with the escalate sub-workflow's `Name LIKE 'AI Follow-Up%'` dedupe (it would hijack the item and overwrite the note with a borrower question) **and** would trigger `Resume_FUR_On_WorkItem_Complete` on completion, bumping the cadence step on a FUR that was never escalated. Named `Needs borrower wording`, deduped on `Name LIKE 'Needs borrower wording%'`.
  - Does **not** touch the LOA's condition row — the org rule that automation never writes `Latest_Note__c` on a human-created record is respected. The new work item is automation-created, so writing its own note is legitimate.
  - [ ] Owner is coded as the condition's `OwnerId` with a fallback to `005Em00000E99YfIAJ`. Only the fallback has been exercised (test conditions were API-created and already owned by the integration user). Prove with a real human owner. The fallback Id is a **staging** hardcode — already on the cutover list.

- [x] **FIXED 2026-08-19 — automation work items showed a BLANK task name in the widget.** The `mortgageChecklist` LWC binds its editable "Task" box to `Condition_Name_LTA__c`, not `Name`. Every automation-created work item set `Name` only, so the box rendered empty for the agent. Mirror image of the bug `backfill_work_item_names.apex` fixed. Now writes both fields in: escalate sub `Create Work Item (Opp)` + `(Lead)`, Path B `Create Detail WorkItem`, Path A `Create Wording Item`. (Path B `Create Doc Rows` was already correct.)
  - [ ] **Backfill needed for rows created before the fix — ALL 14 open automation work items in staging have a null LTA.** Script written: `Salesforce Workspace/scripts/backfill_workitem_lta.apex` (idempotent). Run in staging, and again in prod after cutover.
  - Note: `Condition_Name_LTA__c` is a Long Text Area and **cannot be filtered in SOQL**, so the blank check has to happen in Apex — see Salesforce CLAUDE.md §3.1.
  - [ ] Staging holds **4 duplicate** open items named `AI Follow-Up - FUR-OPPTEST1` on one FUR, created before the escalation dedupe existed. Historical artifacts; dedupe now verified working (exec 320). Clean up when convenient.
- [ ] **WF-2 `outcome` lies on the blank-ask branch.** For a blank-ask FUR, `Build Messages` still computes `outcome = 'All Docs Received'`. Harmless today because that item routes to escalation and never reaches `Complete FUR` — becomes a live bug if anyone rewires that branch.
- [ ] **Lead work items get null `Agent_Role__c`.** `Set_LOA_Work_Item_Agent_Role` only stamps Opp-tied items. Fine for sales-agent context; confirm it doesn't break LOA reporting.

### WF-4 reply handling

- [x] **FIXED 2026-08-19 — multi-intent classification.** `Classify Reply` returned ONE intent, so "here are my statements, also what are my closing costs?" was labelled `will_send` and the question never reached a human — it survived only as an `AI_Summary__c` line. Now returns independent booleans (`opt_out`, `not_interested`, `has_question` + `question_text`, `wants_call`, `will_send_docs`) and `Decide Update` escalates on the **flags** rather than on a single winning label. **VERIFIED LIVE exec 388**, four real emails in one batch: docs+question → `question+will_send` → **Escalated**; opt_out+question → `opt_out+question` → **Opted Out** with consent propagated; plain question → Escalated; plain will_send → Awaiting Reply +2bd with **no** false escalation.
  - **`Escalation_Reason__c` now holds only the QUESTION**, not the borrower's whole message — a real improvement in what the agent reads. The AI summary gains `[documents also received/promised]` so a human doesn't re-ask for docs that already arrived.
  - **`intent` deliberately still emits the ORIGINAL single-label vocabulary.** The `Opted Out?` branch tests `intent === 'opt_out'` and `Log Question` writes it to `fur_question_log`. Making it a compound string would have silently stopped consent propagation — a compliance failure with no error. Multi-intent lives in the decision logic plus a separate `intents` field.
  - Flags are coerced explicitly (`v === true || v === 'true'`) because the Information Extractor can return stringified booleans and `!!'false'` is TRUE — the same trap already hit on `hasAttachments`.
  - [x] **Multi-intent with a REAL attachment — VERIFIED LIVE 2026-08-19** (hand-sent, since the simulator cannot attach files). `intents: question+will_send`, `docs=Y`, status **Escalated** with the question in `Escalation_Reason__c`, **and** the file uploaded: `3 elitebook laptops.pdf`, `ContentDocumentLink 06AEm00000RewvOMAR`, written one second *before* the FUR update. Confirms the upload branch is genuinely independent of status — the document files even when the reply escalates instead of going to Docs Partial.
- [ ] **Message-ID match rung (waterfall Stage 2) not built.** Full waterfall is token → **In-Reply-To Message-ID** → Opp email → Lead email. The Message-ID rung is missing; data is already there (`Outbound_Message__c.Message_Id__c`, External ID + Unique). Needs a Graph header fetch because the Outlook trigger's `fields` mode omits In-Reply-To. Insert between `Match by Token` and `Match by Opp Email`.
- [ ] **`Get FUR` lacks `alwaysOutputData`** — deliberately deferred 2026-08-12, **re-reviewed and knowingly left open 2026-08-19.** This is the last remaining WF-4 item, and the only one still described as "deferred."
  - **What breaks.** `Resolve Match` resolves a single open FUR and `Matched?` routes true, then `Get FUR` re-queries that FUR **by Id**. With no `alwaysOutputData`, zero rows means the node emits nothing, `Classify Reply` is skipped, and the entire chain dies while the execution reports **success** — no FUR update, no unmatched log, no `Notify Unmatched`, no Error Alert. The dispatcher's poll watermark has already moved, so that reply is gone permanently. Same silent-loss shape as the bugs closed this campaign, on a far rarer trigger.
  - **Why it is rare.** It needs the FUR deleted or made inaccessible to the integration user in the sub-second window *between* the match query and the re-query. Nothing in normal operation deletes FURs — terminal FURs are Cancelled/Completed, never removed — and the token rung has no status filter, so even a closed FUR still returns a row.
  - **⚠️ One of the two original reasons for deferring is now OBSOLETE.** The stated risk was that editing a published WF-4 could let normalization strip `Log Unmatched`'s three literal empty-string columns. Those are now `={{ '' }}` expressions (see the item below), a full trace found zero literal `""` anywhere, and WF-4 has since been edited five times without incident. **Only the "rare trigger" argument still stands.** Anyone re-reading this should not treat the edit as risky.
  - **The obvious fix is WRONG on its own.** Adding `alwaysOutputData` alone pushes an empty `{}` into `Classify Reply` — burning an Anthropic call on empty text — after which `Decide Update` reads `fur.Id` as undefined and `Update FUR` hard-fails on an empty recordId. Loud (the Error Alert fires), which beats silence, but wasteful and confusing to diagnose.
  - **Correct fix, ~10 minutes:** `alwaysOutputData: true` **plus** a guard `If` on `$json.Id` immediately after `Get FUR`, routing the empty branch into the existing `Log Unmatched` → `Notify Unmatched` path. A FUR that vanished mid-flight genuinely *is* unmatched, so this reuses machinery already proven live (exec 218). Note the logged `ai_summary` will be blank, since `Log Unmatched` reads `Resolve Match`'s `reason`, which is empty on a successful match — set a distinct reason if that matters.
  - **Priority: lowest open item in Bucket 2.** The unwired send gates and the config-that-lies problem are both worth more than this. Do it opportunistically, the next time WF-4 is open for another reason.
- [x] **CLOSED 2026-08-19 — `Log Unmatched` empty strings already fixed.** Both `fur_id` and `fur_name` are `={{ '' }}` expressions, and `record_id` now maps to `Resolve Match`'s recordId. Fixed incidentally when the `has_attachments` / `message_id` columns were added. The dispatcher's `Log Skipped Auto-Reply` uses the same expression form.
  - **A full trace of all seven workflows found ZERO literal `""` values in any Salesforce field write.** The anti-normalization pattern is applied consistently.

- [x] **CLOSED 2026-08-19 — two keyless `customFieldsValues` entries investigated and PROVEN WORKING.** A trace flagged `Untick Duplicate Row` (Path A) `{"fieldId":"Borrower_Doc_Ask__c"}` and `Clear Box` (Path B) `{"fieldId":"AI_Followup_Request__c"}` as having no `value` key — the same shape as the twice-regressed `Set Escalated`. **Both actually clear their field.** Evidence: `Clear Box` — exec 313 left `AI_Followup_Request__c` null and `Has_AI_Followup_Request__c` false on both leads. `Untick Duplicate Row` — exec 400, a condition seeded with `Borrower_Doc_Ask__c = "SENTINEL-must-be-cleared-by-Untick-Duplicate-Row"` came out **null** with the survivor's ask untouched.
  - **⚠️ This means the CLAUDE.md rule is stated more broadly than the evidence supports.** A keyless entry does NOT universally omit the field from the PATCH — so `Set Escalated`'s original failure had some other or additional cause. Keep using the expression pattern (it is provably safe), but do not assume every keyless entry is broken, and do not "fix" these two by analogy.
  - **Testing lesson:** the first attempt at this test proved nothing, because the Opportunity's FUR had been flipped to Opted Out by the earlier opt-out test, so Path A created a fresh FUR and took the `link` path instead of `dup`. **Shared fixtures drift as tests mutate them — re-check the assumption, don't remember it.**

### Deploy / cutover items → **moved to `PROD_Cutover_Checklist.md`**

Everything that only matters *at cutover* now lives in one place, so it can't drift between two files. That includes: FLS on the 13 profiles, the integration user (F-16), real Appendix-A templates + unsubscribe + NMLS footer, **all page-layout related lists**, the `Chase Cancelled` picklist value, hardcoded staging pod URLs / record-type Ids / owner Ids, `test_mode = false`, digest recipient, activation order, and the mailbox repoint.

**This file is for defects and gaps in the built system. That file is for what has to happen to go live.** If an item is "wrong today regardless of environment" it belongs here; if it's "must be changed when we deploy" it belongs there.

---

## BUCKET 3 — untested / unknown

Needs a test, not a fix. **This is the section that actually gates MVP.**

- [ ] **No unattended multi-touch cadence run has ever happened.** Every "VERIFIED LIVE" note is one hand-triggered record, usually with credentialed nodes pinned. WF-1 Path A, WF-1 Path B, WF-2 and WF-5 are all **INACTIVE**. There is zero evidence about touch 2 → touch 3, or about two FURs landing on the same person.
  - **Proposed soak:** publish WF-1/WF-2/WF-5 with `fur_settings.test_mode = true`, run one week, seeded matrix: 1 Lead FUR, 1 Opp FUR, 1 Spanish, 1 person with two FURs, 1 that receives a reply, 1 that receives nothing. All mail lands on `m.rodriguez@supremelending.com`.
- [ ] **Volume behavior unknown.** `Poll Due FURs` caps at `LIMIT 200`. Unknown: what a 40-FUR morning looks like, Outlook throttling, Anthropic token spend at real condition volume, whether the 15-minute schedule overlaps itself.
- [ ] **FURs never close when their Opportunity closes.** WF-2 skips closed Opps so no email goes out, but the FUR sits open forever. Needs a close-on-Opp-close rule (WF-5).
- [ ] **Escalation rot-guard (>2 business days) not built** — an escalated FUR with an ignored work item sits indefinitely. `Resume_FUR_On_WorkItem_Complete` handles the happy path only.
- [ ] **Task logging in WF-2 not built** (spec calls for logging each touch as a Task).
- [ ] **SMS channel entirely unbuilt** — WF-3, 360 SMS credential, STOP handling, `tdc_tsw__SMS_Opt_out__c` in the consent PATCH (excluded today because the managed-package field is invisible to the integration user and one invalid field fails the whole PATCH).
- [ ] **AI personalization of templates not built** (static templates today — which is also why WF-2 burns zero AI tokens).
- [ ] **Cutover inventory:** 4 hardcoded staging pod URLs (WF-4 `Flag Needs Agent`, `Chatter Record`, `Propagate Opt-Out`; sub `Chatter @mention`); 3 hardcoded org Ids (RT `012Em00000ANGRJIA5` ×2 work-item creates, default owner `005Em00000E99YfIAJ`); hardcoded test recipients in WF-4 `Notify Unmatched` and WF-5 `Send Digest`; Salesforce flows `Clear_Next_Touch_On_FUR_Stop`, `Resume_FUR_On_WorkItem_Complete`, `Repoint_FUR_On_Lead_Convert` are staging-only and must be deployed to prod; `Outcome__c` picklist value `Chase Cancelled` must exist in prod.
- [ ] **Credential bindings cannot be audited via MCP** (`get_workflow_details` does not return them) and **two different credentials are both named "Salesforce - Prod"**. Eyeball every Salesforce node's credential in the n8n UI before cutover.

---

## Cross-cutting lessons worth enforcing

- [ ] **Never use `setNodeParameter`.** Its JSON Pointer root is the node, so the path that *looks* right (`/parameters/...`) nests into a dead `parameters.parameters` copy and the node keeps its old value while the write reports success. Use `updateNodeParameters` with `replace: true` for every change, scalar or not. This bug has landed 3+ times, once silently invalidating a documented "FIXED".
- [ ] **A "FIXED" note is worthless unless the raw node JSON was re-read AFTER the write** — and in `activeVersion`, not the draft.
- [ ] **Never clear a Salesforce field with a literal `""`.** n8n normalization strips any parameter equal to the node default, and `""` is the default, so the entry reverts to the keyless form and the field is omitted from the PATCH entirely. Bind an expression that resolves to empty (`={{ $json.nextTouch }}`) — non-empty in the JSON, empty at runtime. This is why WF-4's `Update FUR` never regressed and the sub's `Set Escalated` regressed twice.
- [ ] **Normalization also strips default-valued keys on nodes you did not touch** (`operation: "query"`, `operation: "create"`, `resource: "message"`). Harmless, but it changes the `validate_workflow` warning signature and looks exactly like nesting damage. Confirm by behavior.
- [ ] **`create_workflow_from_code` / `addNode` auto-binds the wrong Salesforce credential** — it picks "Salesforce - Prod". Always check `autoAssignedCredentials` in the response and rebind to **Salesforce - Sandbox `8j2Z1Q8YwHHvR9nn`**. Hit again 2026-08-12 on WF-2's new node.
- [ ] **Any find-or-create test needs ≥2 targets, at least one per branch, the query node's rows in SHUFFLED order, and one zero-row target.** A same-order test cannot distinguish key-indexing from index-pairing, and a single-target test proves nothing at all.
- [ ] **A pinned test can never validate a query's SELECT/WHERE list** — only transformation logic. Any query change needs a real SOQL run.
- [ ] **Salesforce MCP servers:** `4bed0244…` = **STAGING** (`m.rodriguez@supremelending.com.staging`). `0f15eecd…` = **PRODUCTION**. Confirm with `getUserInfo` before any DML.

---

## Appendix — Bucket 1 outcome (2026-08-12)

**Genuinely fixed this session:**

| Fix | Evidence |
|---|---|
| Sub-workflow `Prep` collapsed N FURs to 1, silently dropping escalations | exec 272 proved the drop; exec 273/274 prove the fix with reversed row order + a zero-row target |
| Unresolved FUR vanished with a success status | Now hard-fails when none resolve (fires the shared Error Alert); partial attrition reaches Soft-Failure Alert |
| Lead work-item dedupe hijack | `Get Open WorkItem (Lead)` rekeyed `Lead__c` → `Follow_Up_Request__c`, symmetric with the Opp branch |
| `Set Escalated` never cleared `Next_Touch_At__c` | Root cause was normalization stripping `""`; now an expression. Behavioral proof is masked by `Clear_Next_Touch_On_FUR_Stop`, which holds the invariant from the Salesforce side regardless |
| Blank-ask FURs stamped "All Docs Received" having collected nothing | New `Get Blank-Ask Conditions` query + `Needs Wording?` branch escalating to a human. exec 275 verified all four routes |

**Listed as OPEN in `CLAUDE.md` but ALREADY BUILT (do not re-fix):**

- ✅ WF-4 `Soft-Failure Check` + `Soft-Failure Alert` — published, scans `Propagate Opt-Out` / `Flag Needs Agent` / `Chatter Record`, with an explicit "OPT-OUT NOT RECORDED — ACTION REQUIRED" line. `CLAUDE.md` calls this the highest remaining risk.
- ✅ Opportunity emails greeting "Hi there" — WF-2 derives the first name from `Opportunity__r.Name`, stripping program prefixes and trailing loan numbers.
- ✅ Path A array-index pairing — `Prep Update` pairs via `pairedItem` with an index fallback.
- ✅ Path A doc dedupe — fully built, including the 39-token vocabulary, alias map, accent-stripping, `'other'` name-only matching, and larger-ask-wins.
- ✅ Path A `Language__c: "EN"` hardcode — now binds `={{ $json.lang }}` from `Preferred_Language__c`, with existing-FUR language winning.
- ✅ `Repoint_FUR_On_Lead_Convert` — user confirmed live-tested and working 2026-08-12.
- ✅ The "3 dangling test FURs" — two are already Cancelled with `Next_Touch_At__c` null; `FUR-MRZABGFY0` has a legitimate open worded condition and would behave correctly. **Cancelling it would have killed a real chase.** All 5 open FURs in staging verified: zero at risk of false completion.

**The real conclusion:** most of the apparent bug count was **stale bookkeeping, not broken code**. The code is meaningfully ahead of `CLAUDE.md`. That file's OPEN list needs reconciling before it is used to make a go/no-go call — an inaccurate readiness doc is now the bigger risk than the software.
