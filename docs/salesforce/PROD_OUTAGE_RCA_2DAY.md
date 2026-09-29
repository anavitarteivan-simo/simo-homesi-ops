# Salesforce Support Case — Opportunity save fails with UNKNOWN_EXCEPTION (non-admins & API)

## Severity
**Sev 1 / Business-stopping.** All non-administrator users are unable to save or update any Opportunity in production. This blocks loan pipeline updates, production-support notes, and Chatter posts on Opportunities. System Administrators are not affected.

## Org
- Production org: **Homesi / Simo Solutions Group**
- Org Id: **00DKb000000OvoRMAS**
- My Domain: **ruby-ruby-7485.my.salesforce.com**

## Summary
Since ~2:49 PM ET on 2026-07-28, **any update to an Opportunity fails with `UNKNOWN_EXCEPTION` ("An unexpected error occurred. Please include this ErrorId…")** for:
- Non-administrator users saving in the Lightning UI, and
- Any save via the REST/SOAP API (reproduced as a System Administrator through the API).

**System Administrators saving in the Lightning UI succeed** — they have Modify All Data, which bypasses sharing. This admin-only-works pattern points at the sharing/commit layer, not at code.

## Reproduction
1. As a non-admin user (e.g., **Agent Loa On-Demand** profile) OR via the REST API as any user, update any field on any Opportunity.
   - Example record: Opportunity **006Qg00000kz2lcIAA** (updating `Prod_Support_Note__c`).
2. The save fails immediately with `UNKNOWN_EXCEPTION` and a new ErrorId each time.
3. As a System Administrator (Modify All Data) in the Lightning UI, the identical save succeeds.

## Error IDs (please decode / trace internal stack)
- `530106887` (recurring core code across every API attempt)
- `1924604064-522748`
- `1486507758-96614`
- `1751704383-80896`
- `1087300778-350767`
- `621161304-296332`

Related downstream flow faults (the Opportunity commit failure surfaces as "unhandled fault" in Feed Item-triggered flows `Chatter_to_Contacted_Flow` / `Last_Action_with_Chatter` when a Chatter post is added to an Opportunity):
- `327806419-78910`
- `501570063-300660`

## Debug logs from a clean reproduction
Trace on user **It Support** (m.rodriguez, 005Kb00000B1HzJIAV); reproduced the failure via API update of Opportunity 006Qg00000kz2lcIAA:
- ApexLog **07LQg00000XIbxPMAT**
- ApexLog **07LQg00000XIbxOMAT**

**Key detail:** both logs show **Status = Success** for the Apex/flow/validation layer (≈1–1.5s, no governor limits hit), yet the DML returns `UNKNOWN_EXCEPTION`. The failure occurs at the **platform commit stage, after logged execution** — i.e., it is not an Apex/flow/validation-rule error.

## Permission-isolation tests performed (narrows it to Opportunity commit)
We temporarily granted a non-admin user (Agent Loa On-Demand profile) escalating permissions via a permission set and retested the Opportunity save each time:
- **Modify All on Contact** → Opportunity save **still fails**. (Rules out Contact access.)
- **Modify All on Contact + Modify All on Opportunity** → Opportunity save **still fails**. (Rules out object-level Opportunity access/sharing.)
- The same user **can update Leads without error**. (Failure is **specific to Opportunity**, not org-wide.)
- The **only** path that succeeds is a System Administrator with **Modify All Data** in the Lightning UI. Even a System Administrator **fails via the API**.

Conclusion: object-level access/sharing is not the cause; the failure is specific to committing an Opportunity and is only avoided by the Modify All Data + Lightning-UI path.

## What we have already ruled out
- **Not an in-progress recalculation.** Both Salesforce completion emails were received (sharing rule recalc 5:13 PM ET; OWD recalc 5:21 PM ET), and a subsequent OWD metadata deploy completed cleanly (no "operation already in progress"). The error persists after recalcs completed.
- **Not a flow / trigger / validation rule.** Debug logs show the full Apex/automation layer completes with Status = Success.
- **Not user-permission-specific.** Reproduced as a System Administrator via the API. Admin UI success is attributable to Modify All Data bypassing sharing.
- **Sharing config is back to baseline.** Contact OWD = Controlled by Parent; the temporary all-contacts sharing rule has been removed.

## Recent changes today (2026-07-28, Eastern) — likely trigger
1. **~2:49 PM ET** — Contact org-wide default changed **Controlled by Parent → Private** (Metadata API).
2. **~2:50 PM ET** — Owner-based sharing rule **"Contact_All_Internal_Read"** created (share all Contacts, Read, to All Internal Users) → launched a large ContactShare recalculation.
3. **~4–5 PM ET** — Reverted: sharing rule deleted and Contact OWD set back to **Controlled by Parent**.
4. **5:13 PM ET** — email: sharing rule recalc completed.
5. **5:21 PM ET** — email: OWD change recalc completed.
6. **After both completed and config reverted to baseline, the Opportunity save error persists.**

## Working hypothesis & request
The rapid, overlapping Contact OWD flips (Private → add rule → remove rule → back to Controlled by Parent, mixed metadata + Setup UI) appear to have left the org's **sharing state internally inconsistent**, causing a commit-time failure on Opportunity saves whenever sharing is evaluated (non-admins and API), while Modify All Data admins bypass it.

Please:
1. Decode the ErrorIds / internal stack for the transactions above.
2. Check for **orphaned or inconsistent sharing rows** on Opportunity (and related Contact/Account) sharing.
3. **Run a full org-wide sharing recalculation** / repair.
4. Advise on root cause and prevention.

## Business impact & urgency
Non-admin users cannot update Opportunities at all — this halts pipeline/processing work org-wide. Requesting expedited handling.

## Contact
- Admin: Melquiades Rodriguez — m.rodriguez@supremelending.com
