# Borrower Follow-Up — Branch Coverage Report

**Campaign run 2026-08-12 → 2026-08-18, staging org (`homesi-staging`).**
Companion to `CLAUDE.md` (how it works) and `FUR_Bucket_2_3_Checklist.md` (what's left). **This file records what is PROVEN, and how.**

---

## How to read this

Every row names a branch, the scenario that exercised it, the **n8n execution id**, and the evidence. The `Proof` column is the important one:

| Proof | Meaning |
|---|---|
| **LIVE** | Ran unpinned against real Salesforce. Real SOQL, real writes, real AI calls, verified afterwards by querying Salesforce — not by reading node output. |
| **PINNED** | Ran with `test_workflow` pin data. Proves transformation logic ONLY. **Cannot** validate a query's SELECT/WHERE list, a credential, or a send. |

**Why this distinction is the whole point.** This project already contains one "VERIFIED exec 231" that was worthless: the test pinned the Salesforce node, so the pinned rows contained a field the SOQL didn't actually select, and a compliance gate passed on data that would never exist live. Treat PINNED as "the code is shaped right", never as "it works".

Unless stated otherwise, every row below is **LIVE**.

---

## WF-1 Path A — Condition Chase (`bfvPz2pwKQnK8ozG`)

Execs **277, 278, 299, 306**. 15 of 16 branches.

| Branch | Scenario | Exec | Evidence |
|---|---|---|---|
| Needs FUR? TRUE → Create | Lead with no open Docs FUR | 277 | New FUR `a1KEm00001TOzHFMA1` |
| Needs FUR? FALSE → reuse | Opp + ES Lead already had open Docs FURs | 277 | `needCreate:false`, existing ids returned |
| Existing-FUR language wins | ES FUR + English condition text | 277 | Asks returned in Spanish, accents intact |
| Dup Condition? FALSE → Link | 5 distinct doc types | 277 | `action:'link'` ×5 |
| Dup Condition? TRUE → Untick | Bank statements already chased | 277 | TEST-B1 `a1IEm00000AIIgpMAH` → `Chase_With_Borrower__c=false`, ask nulled |
| Raise Surviving? TRUE | New ask of 3 months vs open 1 month | 277 | Survivor `a1IEm000008wEnaMAE` count **1→3**, note "Ask raised from 1 to 3" |
| Raise Surviving? FALSE | Equal counts (1 vs 1) | 278 | TRUE branch empty, FALSE branch 1 item |
| `sendable=false` → blank ask | LDP/GSA internal item | 277 | TEST-A2 ask blank, note "Needs wording - agent review" |
| `other` does NOT type-merge | Utility bill vs LDP/GSA | 278 | Negative control — stayed `action:'link'` |
| **Untyped row matched via `guessType`** | New LOE vs legacy row with `doc_type:"Other"` | 278 | Deduped against `a1IEm000008wEnbMAE` — **the fix** |
| Two identical `other` merge by name | Same occupancy questionnaire twice | 299 | TEST-E1 duped against TEST-E2 within one batch |
| Closed-Opportunity guardrail | Condition on a Closed Lost Opp | 299 | Absent from **both** `Plan Opps` and `Expand Conditions`; DB untouched |
| Converted-Lead guardrail | Condition on a converted Lead | 306 | Absent from both filters; DB untouched |
| Both lookups set → Opp wins | Condition with Opp **and** Lead | 299 | `targetType:Opportunity`, `leadId` emptied |
| `Type__c` filter in find-or-create | Opp already had an **Interest Check** FUR | 306 | Created a NEW Docs FUR `a1KEm00001TPTlZMAX` rather than reusing it |

⬜ **Untested:** `Get Existing Docs FURs` returning zero rows *overall* — see Deliberate Gaps.

---

## WF-1 Path B — Request Box (`NQBD7I86IlIsj47Z`)

Execs **313, 314, 315, 316**. 16 of 16 branches.

| Branch | Scenario | Exec | Evidence |
|---|---|---|---|
| Needs Detail? FALSE | Named documents in the box | 313 | Normal create/reuse path |
| Needs FUR? TRUE → Create | Lead with no open FUR of that Type | 313 | New FUR `a1KEm00001TPqGjMAL` |
| Needs FUR? FALSE → reuse | Lead+Type already open | 313 | ×2 |
| Existing-FUR ES beats English note | English staff note on Spanish thread | 313 | Row created as "Página de declaración del seguro de propietario" |
| New Doc? TRUE → Create rows | Pay stubs + driver's licence | 313 | 2 rows created |
| New Doc? FALSE → Update, larger wins | 24 months vs open 12 | 313 | `a1IEm00000AIIn7MAH` **12→24**, note "Ask raised from 12 to 24" |
| Equal-count suppression | Purchase contract already open at 1 | 313 | Emitted nothing; existing row untouched |
| Seed Language? TRUE | Lead with blank `Preferred_Language__c` | 313 | Seeded EN |
| Seed Language? FALSE | Lead already ES | 313 | Skipped |
| **`guessType` vs human-created row** | Pay stub request vs row with **NULL** `Chase_State__c` | 313 | No duplicate created — the case that matters most, since LOAs never write Chase_State |
| Skip Already Flagged (fingerprint) | Unchanged vague text | 314 | `Skip Already Flagged` → `[]`, `Parse Request` **never ran**, **zero Claude sub-runs**, 2s execution |
| Needs Detail? TRUE | Three vague requests | 315 | All flagged with fresh fingerprints |
| Has Detail Item? TRUE → Update | 2 leads with existing items | 315 | Both updated in place |
| Has Detail Item? FALSE → Create | 1 lead with no item | 315 | New item `a1IEm00000ALL8XMAX` |
| Chatter Ask Agent | Vague request, owner known | 315 | Feed `0D5Em000010WYHNKA4`, real `@mention` |
| Has Item To Close? → Close | Vague request later clarified | 316 | `a1IEm00000AGvm9MAD` → **Completed**, "Request clarified"; other leads' items untouched |
| Interest Check routing + Lead+Type key | "Still interested?" on a Lead with an open **Docs** FUR | 316 | New Interest FUR, `docsJson: []` |

> Exec 315 is also the **regression test for the exec-270 flattening bug** — a mixed create/update batch across 3 leads, the exact shape that used to silently lose a lead.

---

## WF-2 — Cadence Engine (`nG8hwck9RsoJZiQb`)

Execs **275 (PINNED), 276, 322, 324**. All branches except quiet hours.

| Branch | Scenario | Exec | Evidence |
|---|---|---|---|
| Safety gate | Zero due FURs | 276 | Confirmed `test_mode:true`, `test_email` = m.rodriguez; zero sends; also validated the new `Get Blank-Ask Conditions` SOQL live |
| **Opted-out Lead skipped** | `HasOptedOutOfEmail = true` | 322 | Absent from `Build Messages` output |
| **Opted-out Opportunity skipped** | `HasOptedOutOfEmail__c = true` | 322 | Absent — the gate your notes flagged as recorded-then-ignored |
| Closed Opportunity skipped | `IsClosed = true` | 322 | Absent |
| Needs Wording? TRUE → escalate | FUR with only blank-ask conditions | 322 | `Escalate Missing Wording`, `subExecutionsCount:1` — **not** falsely completed |
| Docs Left? TRUE → All Docs Received | FUR with no open conditions | 322 | `a1KEm00001TPvzZMAT` Completed |
| Docs Left? TRUE → Chase Cancelled | FUR with only unchased conditions | 322 | `a1KEm00001TPvecMAD` Completed with the honest outcome |
| Docs Left? FALSE → send | 5 due FURs with worded docs | 322 | draft→Mark FUR→Record Outbound Msg→send; **5 sends** |
| Message-Id capture | Same run | 322/324 | **6 `Outbound_Message__c`** rows with real Graph `internetMessageId` |
| Spanish template + doc list | ES FUR, 4 ES docs | 322 | Spanish subject, body and bullet list |
| Non-doc cadence with docCount 0 | Interest Standard step 0 | 322 | Sent normally — guard is doc-cadence only |
| Step-specific template | Step 2 | 322 | `docs_step2` ("Still need a few documents") |
| Opp first-name derivation | Opp "Melquiades Rodriguez" | 324 | "Hi Melquiades" — after fixing a regression I introduced |

⬜ **Untested:** quiet-hours skip. Both live runs fell inside 09:00–19:00 ET; the pinned run had quiet hours disabled deliberately.

---

## WF-5 — Housekeeping + Digest (`vNLsXCapVmrP5GIC`)

Execs **317, 382**. All branches.

> ⚠️ **WF-5 has NEVER been published.** `activeVersionId` is `null` — not stale, absent. Every test below is a **manual execution of the draft**, which validates the logic but means nothing is deployed and the 8am ET schedule has never fired. Publishing activates that schedule and is a deliberate go/no-go decision.

| Branch | Scenario | Exec | Evidence |
|---|---|---|---|
| Exhausted → Escalated | Docs Standard step 4 ≥ maxStep 3, Next Touch cleared | 317 | `a1KEm00001TKWlhMAH` → Escalated |
| Exhausted → Dead | Interest Standard step 2 ≥ maxStep 2 | 317 | `a1KEm00001TOStBMAX` → Dead + Outcome "No Response" |
| Stale → Escalated | Last Outbound 20 days back | 317 | "Stale - no activity for 20 days" |
| In-cadence skipped | 7 of 10 polled FURs | 317 | Untouched; `a1KEm00001TPtT7MAL` still Active with Next Touch intact |
| Escalated? TRUE → sub | 2 escalations | 317 | `subExecutionsCount: 2` |
| Escalated? FALSE → close-out | 1 Dead | 317 | Single `Update FUR (close-out)` — no double write |
| Next Touch cleared | All 3 closed-out | 317 | All `Next_Touch_At__c` null |
| Digest branch independent | Same run | 317 | "7 open, 4 escalated"; `Send Digest` delivered |
| **Exhaust action `Close_NoResponse` → Dead** | Reactivation on a **Lead**, step 2 | 382 | `FUR-REACT-LEAD` → **Dead / No Response**. Previously Escalated — the `/dead/i` bug |
| **Live-loan safety floor** | Same cadence on an **Opportunity** | 382 | `FUR-REACT-OPP` → **Escalated**, reason *"cadence would close this, but it is attached to an open loan - routed to a human"* |
| `Poll Open FURs` SELECT change | Added `Opportunity__c` / `Lead__c` | 382 | Proven live — a pinned test could not have validated a SELECT change, and the floor fired, which requires the new field |

---

## Escalate & Notify sub-workflow (`vJKvJpOZUxrhqOKY`)

Execs **272, 273, 274 (PINNED for structure), 317, 320 (LIVE)**.

| Branch | Exec | Proof | Evidence |
|---|---|---|---|
| Multi-FUR drop **reproduced** | 272 | PINNED | 2 FURs in → `Prep` emitted 1 → whole Lead branch never ran, status success |
| Multi-FUR **fixed**, key-indexed | 273 | PINNED | 3 targets, `Get FUR` rows **reversed**, one zero-row target → correct pairing. Index-pairing would have swapped them |
| Unresolved FUR surfaced | 274 | PINNED | Partial attrition reached `Soft-Failure Alert` |
| Target is Opp? TRUE | 317 | **LIVE** | Work item `a1IEm00000ALNALMA5` on the Opportunity |
| Target is Opp? FALSE | 317 | **LIVE** | Work item `a1IEm00000ALJUuMAP` on the Lead |
| `Needs_Agent__c` written | 317 | **LIVE** | **true** on both the Opportunity and the Lead — these are best-effort nodes, so only field values prove it |
| Has Task? TRUE → Update | 320 | **LIVE** | Same item updated in place: Created 20:22:10, Modified 20:24:20, still exactly **1** item |
| `Is_Complete__c=false` dedupe filter | 317 | **LIVE** | A **Completed** July item on the same FUR was correctly ignored, not reopened |
| `mode: "each"` isolation | 317 | **LIVE** | 2 items → 2 sub-executions |

⬜ **Untested:** `Soft-Failure Check` firing on a genuine node failure.

---

## WF-4 — Reply Handler + Dispatcher (`7nVnALsJHaPseTVt`, `pA2IVtxuaTyFIQGK`)

Execs **328, 331–337, 352, 357, 360, 364, 370, 373, 376, 378, 381**. All branches. Every one LIVE, driven by real email.

| Branch | Scenario | Exec | Evidence |
|---|---|---|---|
| Multi-email drop **reproduced** | 5 emails in one poll | 328 | Trigger emitted 5, `Extract Match Keys` emitted **1**, 4 replies destroyed, status success |
| Multi-email **fixed** | Same 5 re-sent | 331/332/334/336/337 | **5 emails → 5 executions** |
| Token match — `will_send` | "I'll send them tomorrow" | 331-337 | Awaiting Reply, Next Touch +2bd |
| Token match — `question` | "All pages or just summary?" | 331-337 | Escalated, borrower's words in `Escalation_Reason__c` |
| Token match — `wants_call` | "Can someone call me?" | 331-337 | Escalated |
| Token match — `not_interested` (Spanish) | "ya decidí no continuar" | 331-337 | Dead / Not Interested, AI summary in Spanish |
| Token match — `opt_out` | "STOP. Remove me" | 331-337 | Opted Out + Outcome Opted Out |
| **Opt-out propagation** | Same | 331-337 | `HasOptedOutOfEmail__c` = **true** on the Opportunity |
| Phantom empty-token match **reproduced** | No-token email | 352 | `matched:true, matchSource:'token'` against a NULL-token FUR |
| Phantom match **fixed** | Same, junk FUR still present | 357 | `matched:false, reason:'no match'` |
| Unmatched → log + notify | Unknown sender | 357 | `fur_question_log` row 28, `Notify Unmatched` sent, **zero AI calls** |
| Ambiguous → flag + Chatter | Lead with 2 open FURs | 360 | `Needs_Agent__c` true, Chatter `0D5Em000010gdOBKAY`, row 29 |
| Auto-reply guard — dropped | EN + ES OOO, **both carrying valid tokens** | 364 | 2 dropped and logged (rows 31, 32), zero AI calls |
| Auto-reply guard — passed | Genuine reply in same batch | 364 | 1 WF-4 execution from 3 emails |
| Opportunity-email rung | Address on an Opp with 1 open FUR | 373 | `matchSource:'opp_email'` |
| Lead-email rung | Same email, address moved to a Lead | 376 | `matchSource:'lead_email'` — proves precedence is real |
| **Matched + attachment** | Token + PDF | 378 | Docs Partial; `ContentDocumentLink 06AEm00000RcKBAMA3` → **7 laptops.pdf** on the FUR |
| **Ambiguous + attachment rescue** | No token + PDF | 381 | No FUR touched; `ContentDocumentLink 06AEm00000RcqJ0MAJ` → **3 hp laptops.pdf** on the **Lead**; row 36 `has_attachments=true` |
| `First_Response_At__c` idempotency | Repeat replies | 370/376 | Preserved at 2026-08-14, never overwritten |
| **Multi-intent: docs + question** | "Attached are my statements. Also, what are my closing costs?" | 388 | `intents: question+will_send` → **Escalated**; `Escalation_Reason__c` = only the question; summary tagged `[documents also received/promised]` |
| **Multi-intent: opt-out + question** | "Please stop emailing me. Also who is my loan officer?" | 388 | `intents: opt_out+question` → **Opted Out** + `HasOptedOutOfEmail = true` on the Lead — terminal correctly wins and consent still propagates |
| Multi-intent regression: question only | Unchanged scenario | 388 | Escalated; came back `question+will_send` because the text genuinely contains both |
| Multi-intent regression: will_send only | Unchanged scenario | 388 | Awaiting Reply +2bd — **no false escalation** |

| **Multi-intent + REAL attachment** | Hand-sent: bank statement attached **and** "when will we be able to close?" | 2026-08-19 | `intents: question+will_send`, `docs=Y` → **Escalated** with only the question in `Escalation_Reason__c`, **and** `3 elitebook laptops.pdf` filed via `ContentDocumentLink 06AEm00000RewvOMAR`. Proves the upload branch is independent of status |

> The last row is the one that could have failed silently: when a reply both sends documents and asks a question, status goes to Escalated rather than Docs Partial. If the upload branch had been status-dependent, the FUR would have looked correctly escalated while the borrower's document vanished. The `ContentDocumentLink` timestamp (16:25:31) precedes the FUR update (16:25:32), confirming both ran.

> Exec 378 matters beyond the upload: `Get Attachments` and `Download Attachment` reference `$('New Email (docs inbox)').item.json.id`, and after the trigger swap that id arrives via the dispatcher's field mapping. It proves the Graph message id survives the hand-off — the one real risk in that rework.

---

## Bugs this campaign found

| # | Bug | Severity | Status |
|---|---|---|---|
| 1 | **WF-4 discarded all but the first email per poll** | Live data loss — borrower replies, documents and opt-outs destroyed silently | Fixed (dispatcher) |
| 2 | **Blank subject token matched a NULL-token FUR** | Live mis-routing — all non-token mail attached to one junk FUR and escalated | Fixed (2 guards) |
| 3 | **Mailbox pollution** — spam, OTP emails, Microsoft notices and an OOO auto-reply all classified and escalated as borrower replies | Wasted AI spend, false escalations; likely drained the Anthropic credits | Fixed (F-4 guard) |
| 4 | **Attachments lost on unroutable replies** | Borrower documents left in the mailbox, nothing said one existed | Fixed (rescue upload) |
| 5 | **Dedupe blind to untyped rows** — every human-ticked condition | Live double-ask; borrower asked twice in one email | Fixed (`guessType`, both paths) |
| 6 | **Blank-ask FURs stamped "All Docs Received"** | False success; overstates collection | Fixed (`Needs Wording?`) |
| 7 | **Sub-workflow collapsed N FURs to 1** | Latent — `mode: each` on both callers made it unreachable | Fixed |
| 8 | **`Set Escalated` never cleared `Next_Touch_At__c`** | Masked by a Salesforce flow; a documented "FIXED" claim was false for a day | Fixed (expression form) |
| 9 | **Lead work-item dedupe key asymmetric** | FUR-B's escalation hijacked FUR-A's work item | Fixed |
| 10 | **F-4 auto-reply guard never built** | Designed in the spec, absent in code | Built |
| 11 | **Signature blocks in agent-facing text** on the unmatched path | Cosmetic but degrades every triage note | Fixed |
| 12 | **Reactivation `Close_NoResponse` fails `/dead/i`**, and there was **no unknown-action branch** — any typo or new cadence silently became Escalated | Cold-outreach non-responders escalated to humans; any config mistake created work items with no signal | Fixed (exact vocabulary + throw on unknown + live-loan floor), verified exec 382 |
| 13 | **My own regression**: over-escaped regex reintroduced "Hi there" on every Opportunity email | Caught by test, fixed | Fixed |

---

## Deliberate gaps — chosen, not overlooked

| Gap | Why left |
|---|---|
| `Get Existing Docs FURs` returning zero rows *overall* | Proving it means cancelling every open Docs FUR in staging, destroying the fixture set the other five workflows depend on. `alwaysOutputData` is set and the create path is proven four times over. |
| WF-2 quiet-hours skip | Needs a run outside 09:00–19:00 ET, or a `fur_settings` edit (no update-row tool available via MCP). Cheap to prove any evening. |
| `Soft-Failure Check` on a real failure | Requires deliberately breaking a credential mid-run. |
| Frequency cap / 4h dedupe | **Not built.** Nothing to test — see Bucket 2. |
| Multi-intent replies ("here's my doc, also a question") | Known v3 limitation; classifier returns one intent. |

---

## Test harness now in place

| Workflow | Id | Purpose |
|---|---|---|
| **FUR TEST - Inbound Email Simulator** | `66oCRAyOwmBfwLnk` | Sends borrower-style replies from itsupportaccount into itself — the mailbox the dispatcher polls. Set `ACTIVE` in `Build Test Emails` to pick scenarios. **Cannot attach files** — attachment tests must be sent by hand. |
| **FUR WF-4 Inbound Dispatcher** | `pA2IVtxuaTyFIQGK` | Polls the mailbox, screens auto-replies, invokes WF-4 once per email (`mode: each`). |

Scenario keys available: `will_send`, `question`, `wants_call`, `not_interested`, `opt_out`, `no_token`, `ooo_en`, `ooo_es`.

### Fixtures left in staging (so this is re-runnable)

- **Conditions:** TEST-A1/A2, B1/B2, C1/C2, D1 (closed Opp), E1/E2 (identical `other`), F1 (both lookups), G1 (converted Lead), G2, plus a human-style row with NULL `Chase_State__c` (`a1IEm00000AK21VMAT`)
- **FURs:** `FUR-WF2-WORDING` (blank-ask only), `FUR-WF2-ALLDOCS` (no conditions), `FUR-WF2-CANCELLED` (unchased only)
- **Ambiguity fixture:** Lead `00QEm00000eR2F5MAK` (Demo Borrower) holds 2 open FURs and currently carries `m.rodriguez@supremelending.com`
- **Single-match fixture:** Lead `00QEm00000eSi5WMAS` carries `itsupportaccount@simosolutionsgroup.com`
- Opportunity `006Em00000oa7uDIAQ` is **Closed Lost** deliberately (closed-Opp gates)

> Reverting any of these addresses changes which rung a no-token email hits. Check `Lead.Email` / `Opportunity.Email__c` before interpreting a match-rung result.

---

## Rules this campaign reinforced

1. **Never use `setNodeParameter`.** Its JSON Pointer root is the node, so `/parameters/...` nests into a dead copy and the node keeps its old value while the write reports success. Use `updateNodeParameters` + `replace: true`. I broke this rule myself mid-campaign and shipped a stale scenario list.
2. **Never clear a Salesforce field with a literal `""`.** n8n strips parameters equal to the node default, so the entry silently reverts to keyless on the next edit *to any node in that workflow*. Bind an expression that resolves to empty.
3. **A rewrite of a whole Code node risks the 200 lines you didn't mean to change.** My "Hi there" regression came from re-typing a regex during an unrelated edit. Re-read the rendered code after every write, not just the execution output.
4. **Any find-or-create test needs ≥2 targets, one per branch, with the query node's rows SHUFFLED and one zero-row target.** Same-order tests can't distinguish key-indexing from index-pairing.
5. **A pinned test can never validate a query, a credential or a send.**
6. **`create_workflow_from_code` and `addNode` auto-bind the wrong Salesforce credential** — it picks "Salesforce - Prod". Always check `autoAssignedCredentials` and rebind to Sandbox `8j2Z1Q8YwHHvR9nn`. Hit again this campaign.
7. **The dangerous bugs here all report success.** Every one of items 1–9 above left a green execution. Coverage matters more than error handling in a system whose failure mode is silence.
