---
description: Checklist before any change reaches production
---
Before touching production for: $ARGUMENTS

1. Confirm which systems and orgs are affected, and state the exact `--target-org` / MCP server.
2. Show evidence it was deployed and verified in `homesi-staging` (or say plainly that no staging path exists).
3. Re-read the relevant gotchas: `docs/salesforce/ORG_REFERENCE.md` (numbered list) and/or
   `docs/n8n/ENGINE_REFERENCE.md` §2. List the ones that apply.
4. Check the kill switches are untouched: `fur_settings.test_mode` and `Notification_Settings__c.Test_Mode__c`.
5. For Salesforce: run `sf project deploy validate ... --target-org prod` and report the result.
6. State the rollback: what to redeploy or deactivate if it goes wrong.
7. List what "verified in prod" will mean — the record, query or execution you will check afterwards.

Stop and wait for my go-ahead. Do not run the prod change in this command.
