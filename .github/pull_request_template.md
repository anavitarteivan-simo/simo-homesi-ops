<!-- Policy: docs/CHANGE_POLICY.md. Delete sections that do not apply. -->

## What and why


## Systems touched
<!-- e.g. docs only · Salesforce (prod / homesi-staging) · n8n workflow <id> · Customer.io 164380 · Lambda <name> -->

## Checklist (from `/prod-preflight`)
- [ ] Orgs / workspaces stated explicitly (`--target-org prod` or `homesi-staging`, MCP server)
- [ ] Deployed and verified in `homesi-staging` first (Id: ) — or "no staging path" stated
- [ ] Relevant gotchas re-read and listed (`ORG_REFERENCE.md`, `ENGINE_REFERENCE.md` §2)
- [ ] Kill switches untouched: `fur_settings.test_mode`, `Notification_Settings__c.Test_Mode__c`
- [ ] Salesforce: `sf project deploy validate --target-org prod` result:
- [ ] Rollback:
- [ ] "Verified in prod" will mean (record / query / execution Id):
- [ ] Owning docs updated (`/sync-docs`) and dated
- [ ] No secrets, no borrower/realtor PII
