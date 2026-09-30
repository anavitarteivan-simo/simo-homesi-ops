# reports/

Short, dated reports for people (managers, the team): incident reports, inventories, system and
architecture summaries. They are **snapshots** — the living truth stays in `docs/` (see
`docs/INDEX.md`), and a report links to the doc it summarises instead of copying it.

## Conventions

- File name: `YYYY-MM-DD-<topic-in-kebab-case>.pdf` (e.g. `2026-09-29-inventario-automatizaciones-salesforce.pdf`).
- Keep the source next to it in `src/` with the same base name (`.html`), so it can be corrected
  and re-rendered. Render with headless Edge:
  `msedge --headless=new --no-pdf-header-footer --print-to-pdf=<out.pdf> file:///<path>/src/<name>.html`
- Language: Spanish (audience is the team), unless the report says otherwise.
- **No borrower / realtor PII.** Use record Ids and loan numbers, never borrower names, emails or phones.
- A report is not updated after the fact; publish a new dated one instead.

## Index

| Date | Report | Summarises |
|---|---|---|
| 2026-09-29 | [Incidencia: Owner revertido en loans F30EEP](2026-09-29-incidencia-owner-f30eep.pdf) | `docs/salesforce/ORG_REFERENCE.md` gotcha #31 |
| 2026-09-29 | [Inventario de automatizaciones de Salesforce](2026-09-29-inventario-automatizaciones-salesforce.pdf) | `docs/salesforce/AUTOMATION_INVENTORY.md` |
