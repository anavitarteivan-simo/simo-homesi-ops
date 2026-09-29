# n8n/ — automation engine

Instance: `https://simosolutionsgroup.app.n8n.cloud`. Full reference and all gotchas:
`../docs/n8n/ENGINE_REFERENCE.md` — read §0 and §2 before editing any workflow.

**Golden rule:** Salesforce is the source of truth; n8n holds no durable state. Every workflow
rehydrates from a SOQL poll.

## Rules
- Every FUR workflow is bound to **prod** Salesforce. Treat every n8n write as a prod write.
- `fur_settings.test_mode` (Data Table `0A0KbAfzHmAHvhCl`) stays **true** unless explicitly told otherwise.
- Editing an active workflow creates a **draft**; nothing changes until it is published and the
  version IDs match. After any write, re-read the **active** version's raw node JSON before
  calling it fixed (`setNodeParameter` nests even for a single scalar).
- `test_workflow` pins credentialed nodes — a green test proves transformation logic only,
  never a SOQL query, a credential, or a send.
- Never clear a Salesforce field with a literal `""`.
- New workflows: set Settings → Error Workflow = `Error Alert (shared)` (`5gSRY0P5hpfLKmFD`).
- Do not repoint mailboxes without explicit instruction.

## workflows/
JSON exports, one file per workflow, named `<id>__<slug>.json`. Refresh with
`python3 scripts/export_workflows.py` (needs `N8N_BASE_URL` and `N8N_API_KEY` in the env).
Exports are a **record**, not the deploy path: the instance is the source of truth for n8n,
so commit a fresh export after every change to show the diff in review.
