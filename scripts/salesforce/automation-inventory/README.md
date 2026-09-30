# automation-inventory

Regenerates [`docs/salesforce/AUTOMATION_INVENTORY.md`](../../../docs/salesforce/AUTOMATION_INVENTORY.md)
from the live prod org. **Read-only**: SOQL / Tooling queries and a metadata retrieve; nothing is
deployed or written to the org.

## Run

Needs `sf` (alias `prod` authenticated), Node 20+ and bash (Git Bash on Windows). Use a work
directory **outside the repo** — it receives ~200 metadata files.

```bash
WORK=/tmp/automation-inventory-$(date +%F)          # any empty folder outside the repo
./fetch.sh "$WORK" prod                             # ~3 min, read-only against prod
./run.sh   "$WORK" ../../../docs/salesforce/AUTOMATION_INVENTORY.md
git diff --stat ../../../docs/salesforce/AUTOMATION_INVENTORY.md
```

`run.sh` prints `malformed rows 0 | placeholders 0` when the tables are well-formed.

## Files

| File | Role | Edit by hand? |
|---|---|---|
| `fetch.sh` | Org check, inventory queries, metadata retrieve, fetches the **active** version of any flow whose latest version is a draft | no |
| `analyze-flows.js` | Flow XML → `inv/flows.summary.json` (entry criteria, fields written, records created, emails, Apex, fault-path hazards) | no |
| `analyze-rules.js` | Rules XML → `inv/rules.summary.json` | no |
| `render.js` | Summaries → markdown tables | no |
| `assemble.js` | `template.md` + tables + `findings.md` → the final doc; checks table integrity | no |
| `template.md` | Prose of the doc: summary counts, how-to-read, hazards, appendix | **yes** — update the counts and "changes since last inventory" each run |
| `findings.md` | §7 Findings to review, tagged [Verified]/[Likely] | **yes** — re-check and rewrite each run |
| `purposes.json` | One-sentence "what it does" for flows that have **no Description** in Salesforce (74 on 2026-09-29) | **yes** |

## Keeping `purposes.json` honest

- The table uses the flow's own Description when it has one, else `purposes.json` (shown with a
  leading `*`). A "Note:" in a purpose is moved out of the table and must be covered in `findings.md`.
- New flows without a Description render with their label only — add a sentence here, written
  from the **active** version's metadata (`inv/flows.summary.json` + the XML in the work dir).
- Better: give the flow a Description in Salesforce, then delete its entry here.

## Gotchas

- A metadata retrieve returns the flow's **latest** version. `fetch.sh` checks `<status>` and, for
  non-Active files, saves the active version from the Tooling API as `mdproj/active_<ApiName>.json`;
  `analyze-flows.js` prefers that file.
- `|` inside a markdown table cell must be escaped even inside backticks; `render.js` does it.
- Do not paste borrower PII into `purposes.json` / `findings.md`; refer to "a hard-coded address".
