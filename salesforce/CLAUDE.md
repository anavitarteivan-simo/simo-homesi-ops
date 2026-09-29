# salesforce/ — SFDX project

Run every `sf` command from this directory. Full reference: `../docs/salesforce/ORG_REFERENCE.md`
(read its numbered gotchas before any deploy).

## Before any deploy
1. `--target-org` on every command — `prod` or `homesi-staging`. The default is staging; never rely on it.
2. Deploy and verify in `homesi-staging` first. For prod, run a validation first:
   `sf project deploy validate --manifest manifest/<file>.xml --target-org prod`
3. Prefer small, explicit manifests in `manifest/` over deploying all of `force-app`.
4. `sourceApiVersion` is **65.0**. Flows authored at 66.0 need a manifest with `<version>66.0</version>`.

## Rules that caused real incidents
- Record-triggered flow entry criteria: `RecordTypeId` = the Id, **never** `RecordType.DeveloperName` (gotcha #30, 2-day outage).
- Flows activate in a **second** deploy — a version cannot be activated in the deploy that creates it (#24).
- New fields need FLS in the same deploy; grant it on the Admin profile by **Id** `00eKb000000aw4EIAQ` /
  PermissionSet `0PSKb0000019iVGOAY`, never by the label "System Administrator" (duplicate profile trap).
- A field "exists" only when the deploy reports `created: true|false` — `FieldDefinition`/`SELECT` hide fields without FLS.
- Adding a picklist value also requires assigning it to the record type (#29).
- Report/list-view inline edit reads the classic page layout, not Dynamic Forms (#28).
- New flows: `CanvasMode = AUTO_LAYOUT_CANVAS` (#22).

## After a prod deploy
Record what went live, with prod Ids and date, in the owning doc (see `../docs/INDEX.md`),
then commit metadata + doc change together.
