# CLAUDE.md — Recruitment Copilot (MMI + NMLS LO Qualification)

Context doc for the Salesforce project. Covers the recruitment-copilot skill as built and verified August 2026: architecture, data contracts, and every gotcha learned against live data. The skill file itself is the source of truth for procedure; this doc is the institutional knowledge behind it.

## What it is

Daily batch qualification of Loan Officer Leads (Salesforce org `ruby-ruby-7485`) against MMI production/license data and NMLS employment history. Salesforce reads/writes go through the Salesforce Hosted MCP; Chrome (claude-in-chrome) is used only for MMI and NMLS. Capped at 30 READY_TO_CALL leads per session; every Ready-to-Call lead is assigned to the operator's Salesforce user (email asked at session start).

## Pipeline (current)

1. Canonical query pulls Leads with `Status IN ('New','Working')` and `Next_Recruitment_Check__c <= TODAY` (or null).
2. MMI Productivity Link per lead → **payload-first extraction** from `window.__NUXT__.data.lo`.
3. **Step 2F — License check** (before Gate 1): disqualifies bank/depository LOs and unlicensed LOs. 12-month re-check.
4. Gate 1 — units 14–60 in 14 months (dual-license bypass waives the band entirely).
5. Gate 2 — ≥1 buyside AND ≥1 listside agent relationship.
6. Gate 3 — Latino agent ratio ≥15% on the top-20-per-side sample.
7. NMLS Consumer Access — Gate 4 (title exclusion: Owner/President/etc.), Gate 5 (employer exclusion), tenure branch (≥6 mo → READY_TO_CALL, <6 mo → CALL_LATER).
8. Outcome write + `Recruitment_Comment__c` audit line for every gate.

## MMI data contract (verified live, Aug 2026)

Primary source: `window.__NUXT__.data.lo` — MMI is a Nuxt app; server-fetched data is serialized into global state for hydration. Complete at page load: no lazy-load, no grid virtualization loss, readable while tab panes are hidden.

| Field | Meaning | Verified against |
|---|---|---|
| `profile.FOURTEENMONTHUNITS` | Gate-1 unit count | matches rendered "Transactions 14 months" |
| `profile.ACTIVELICENSES` | active state licenses | matches Active rows in License History |
| `profile.ACTIVEREGISTRATION` | federal registrations (bank LOs) | VeraBank LO = "1" |
| `profile.ACTIVESTATEARRAY` | licensed states (JSON string) | `"TX - SML"` counts as TX |
| `nmls_history[]` | License History rows: Company/State/LicenseType/Current/StartDate/EndDate | matches AG Grid incl. virtualized rows |
| `agents[]` / `ls_agents[]` | BS/LS partner lists with `AGENT_NAME`, `PARTNERUNITS` | arrive sorted by PARTNERUNITS desc — sort defensively anyway |
| `profile.INDUSTRYTENUREMONTHS`, `COMPANYTENUREMONTHS`, `COMPANYNAME` | tenure/employer | available; NMLS still authoritative for Gate 4 Position |

Fallback chain per lead: payload → legacy innerText/DOM extraction (with scroll/wait rules) → screenshot. On first payload failure in a session: warn operator to contact IT Support, run the rediscovery diagnostic, switch to DOM fallback for the remainder — never re-probe per lead, never auto-trust a rediscovered path.

## License gate (Step 2F) — the bank-LO filter

Intent: bank/depository LOs are federally REGISTERED but hold no state license; they are not recruitable. DQ rule (both license signals must agree):

- No `Current: "Active"` row in `nmls_history` whose LicenseType is NOT registration-like (`/federal|registration|registered/i`), AND
- `ACTIVELICENSES` coalesces to 0.

`ACTIVEREGISTRATION > 0` does NOT rescue — it labels the DQ as the bank variant: reason `"No license — federally registered bank LO"`; otherwise `"No active license present (MMI License History)"`.

Write: `Recruitment_Status__c="Disqualified"`, `Next_Recruitment_Check__c = today + 12 months`, `Status` **untouched**. Gates 1–5 marked `not checked` in the comment (the only outcome allowed to carry `not checked` on MMI/Latino lines).

Verified live: NMLS 580525 (VeraBank N.A.) — empty history, `ACTIVELICENSES: null`, `ACTIVEREGISTRATION: "1"` → bank DQ. Note this LO had 27 units/14mo and would have gone READY_TO_CALL under the old skill.

## Dual-license detection — three tiers, strongest first

| Tier | Signal | Cost | Catches | Verified case |
|---|---|---|---|---|
| 1 | Active `nmls_history` row, LicenseType ~ Real Estate Salesperson/Broker | free, every lead | only states issuing RE through NMLS (e.g. CA-DRE combined RE+MLO) | LO 896004 (CA) |
| 2 | MMI Real Estate Agent Search: strict name match AND state ∈ `ACTIVESTATEARRAY` | one navigation + search | duals in all other states | LO 205993 (VA, United Realty); LO 1634703 (TX, KW Synergy, 38 listings) |
| 3 | LO's own name in their BS/LS partner lists (`_same()` matcher) | free, every lead | self-originating duals only | LO 1634703 (both sides) |

Tier 2 runs ONLY when Tier 1 is negative AND it can change something: Gate 1 about to fail on the band (bypass rescue), or lead about to be written READY_TO_CALL (flag accuracy). Mid-band leads DQ'd at Gates 2–5 never run Tier 2 — their `Dual license: No` can be a false negative by design (throughput trade).

Any tier's hit → Gate-1 band waived + `Possible_Dual_License__c: true` on the outcome write + comment line records the strongest tier (`YES — RE license (State)` / `YES — agent dir (STATE, office)` / `YES — name match: "name", side`).

## Gotchas (all observed live — do not relearn these)

1. **"Discard with a future re-check" is self-contradictory in this org.** The canonical query filters `Status IN ('New','Working')`. Setting `Status = 'Discarded'` removes the lead from eligibility forever, so any `Next_Recruitment_Check__c` becomes unreachable. Re-checkable DQs must leave `Status` alone and use `Recruitment_Status__c = "Disqualified"` only.
2. **MMI payload numerics are strings, and null happens.** `FOURTEENMONTHUNITS: "16"`, `ACTIVELICENSES: "2"` — but bank LOs return `ACTIVELICENSES: null` (not `"0"`). Every read must `parseInt` and null-coalesce. A naive `=== 0` comparison silently breaks on exactly the leads the gate exists for.
3. **NMLS License History ≠ real-estate licensing.** NMLS only carries mortgage credentials. A dual LO+Realtor shows RE rows in `nmls_history` ONLY when the state issues the RE license through NMLS (CA-DRE combined license). A confirmed VA dual showed five MLO-only rows. Never conclude "not dual" from `nmls_history`.
4. **AG Grid lies by omission.** `aria-rowcount` includes header rows, and the grid virtualizes: DOM rows are a minimum, never proof of absence. This is what forced the payload-first architecture. In DOM-fallback mode, never DQ "no license" unless the grid conclusively shows zero rows.
5. **"Two independent signals" aren't independent against a payload restructure.** If MMI renames `ACTIVELICENSES` or restructures `nmls_history`, both signals read empty together → mass false DQ. Guard: before any no-license DQ, corroborate against the rendered License History grid (`gridRows === 0` + no-rows overlay). Grid disagrees → the payload is broken, not the lead.
6. **Payload strings differ from rendered strings in whitespace.** `FULLNAME: "ROSIO  ESPARZA"` (double space) vs title "ROSIO ESPARZA". Any anchor-string matching between page and payload must be whitespace-normalized. This bug silently blanked the first version of the rediscovery diagnostic.
7. **`api.mmi.run` requires a bearer token** — cookie-credentialed `fetch` from page context returns 401. Don't build on the API; drive the UI widgets and read the DOM.
8. **Typed text can silently miss the input.** A click on a stale element ref (after navigation) types into nothing; the search widget then innocently reports "The list is empty" — a false negative. Always verify the input's `value` after typing; if empty, inject via the native value setter + `dispatchEvent(new Event('input', {bubbles:true}))`. An empty-list result only counts when the input verifiably held the query.
9. **Malformed dropdown rows are safe by construction.** Some agent-search rows lack a state token and parse garbage into the state field ("Kw"). They can never satisfy the state-∈-ACTIVESTATEARRAY requirement, so no false hits — only cleanly parsed rows count.
10. **`window.__NUXT__.data.lo` is an internal implementation detail.** A frontend rebuild can rename it silently. Lead-1 sanity check cross-verifies payload vs rendered page every session. Recovery method if broken: rendered values are ground truth — scrape anchors (unit count, title name) from the page, scan large `window` objects for them (whitespace-normalized), drill to the deepest containing sub-object. The diagnostic reports candidates to IT; the session never auto-trusts a remap.
11. **MMI name matching must be strict.** "LIN CHEN" (NY) is a different person from "Lin Chien" (VA). The `_same()` matcher requires exact last-name token equality + first-name compatibility; single-sided middle names are allowed ("Amber Dawn Kimmel" = "AMBER KIMMEL"). Corroborate Tier-2 hits with state overlap, always.
12. **Legacy DOM extraction quirks (fallback mode only):** agent rows use a U+2010 hyphen (`‐`), not ASCII `-`, in `(35) Name ‐ Company`; BS/LS lists lazy-load and need scroll-wait-retry; labels extraction-confirmed across 8 leads (values 0–30 incl. 0 and 1).

## Salesforce fields touched by this skill

`Recruitment_Status__c`, `Last_Recruitment_Check__c`, `Next_Recruitment_Check__c`, `Recruitment_Comment__c` (255-char budget — keep dual-license lines short), `Possible_Dual_License__c` (checkbox, default false — omit from write unless true), `OwnerId` (READY_TO_CALL assignment), `Status` (only the permanent-DQ path sets `Discarded`; the license DQ never does).

## Open items

- No real-world test yet of a Tier-2 name collision (two different people, identical full name, overlapping state). State requirement narrows but can't close it; judgment clause + comment basis is the backstop.
- First production session should watch: lead-1 sanity check output, the first bank-LO DQ, and the first Tier-2 search under batch conditions.
- In DOM-fallback (payload-broken) sessions, the bank-LO filter is effectively suspended (conservative skip) until the skill is updated — the operator warning is what makes this visible.
