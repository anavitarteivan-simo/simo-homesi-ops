#!/usr/bin/env bash
# Read-only: queries prod and retrieves flow + rule metadata into <workDir> (keep it OUTSIDE the repo).
# Usage: ./fetch.sh <workDir> [targetOrg=prod]
set -euo pipefail
WORK="${1:?usage: fetch.sh <workDir> [targetOrg]}"
ORG="${2:-prod}"
INV="$WORK/inv"; MD="$WORK/mdproj"
mkdir -p "$INV" "$MD/force-app"

echo "== org check ($ORG)"
sf data query -o "$ORG" --json -q "SELECT Id, Name, IsSandbox FROM Organization" > "$INV/org.json"
node -e "const o=require(process.argv[1]).result.records[0];console.log(o.Id,o.Name,'IsSandbox='+o.IsSandbox)" "$INV/org.json"

echo "== inventory queries"
sf data query -o "$ORG" --json -q "SELECT DurableId, ApiName, Label, ProcessType, TriggerType, RecordTriggerType, TriggerObjectOrEventLabel, IsActive, ActiveVersionId, LatestVersionId, NamespacePrefix, IsOverridable, LastModifiedDate, LastModifiedBy FROM FlowDefinitionView ORDER BY ApiName" > "$INV/flows.json"
# EntityDefinition.QualifiedApiName across all objects fails with an internal error — select the Id instead.
sf data query -o "$ORG" --json --use-tooling-api -q "SELECT Id, ValidationName, EntityDefinitionId, Active, NamespacePrefix, LastModifiedDate FROM ValidationRule" > "$INV/vr.json"
sf data query -o "$ORG" --json --use-tooling-api -q "SELECT Name, TableEnumOrId, Status, NamespacePrefix, UsageBeforeInsert, UsageAfterInsert, UsageBeforeUpdate, UsageAfterUpdate, UsageBeforeDelete, UsageAfterDelete, UsageAfterUndelete, LastModifiedDate FROM ApexTrigger ORDER BY TableEnumOrId, Name" > "$INV/triggers.json"
sf data query -o "$ORG" --json -q "SELECT Id, Name, SobjectType, Active FROM AssignmentRule ORDER BY SobjectType, Name" > "$INV/ar.json"
sf data query -o "$ORG" --json -q "SELECT Id, DeveloperName, MasterLabel, SobjectType, IsActive, NamespacePrefix FROM DuplicateRule ORDER BY SobjectType, DeveloperName" > "$INV/dr.json"
sf data query -o "$ORG" --json -q "SELECT Id, DeveloperName, MasterLabel, SobjectType, RuleStatus, NamespacePrefix FROM MatchingRule ORDER BY SobjectType, DeveloperName" > "$INV/mr.json"
for t in SharingCriteriaRule SharingOwnerRule AutoResponseRule EscalationRule; do
  sf org list metadata -o "$ORG" -m "$t" --json > "$INV/md_$t.json"
done

# Resolve custom-object Ids (01I…) used by validation rules to API names.
ids=$(node -e "const r=require(process.argv[1]).result.records;console.log([...new Set(r.map(x=>x.EntityDefinitionId).filter(x=>/^01I/.test(x)))].map(x=>\"'\"+x+\"'\").join(','))" "$INV/vr.json")
if [ -n "$ids" ]; then
  sf data query -o "$ORG" --json --use-tooling-api -q "SELECT DurableId, QualifiedApiName FROM EntityDefinition WHERE DurableId IN ($ids)" > "$INV/entities.json"
else
  echo '{"result":{"records":[]}}' > "$INV/entities.json"
fi

echo "== retrieve metadata"
cd "$MD"
[ -f sfdx-project.json ] || printf '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"63.0"}' > sfdx-project.json
node -e "
const [inv]=process.argv.slice(1);const R=n=>require(inv+'/'+n).result.records;
const ent=Object.fromEntries(R('entities.json').map(e=>[e.DurableId.slice(0,15),e.QualifiedApiName]));
const obj=id=>ent[String(id).slice(0,15)]||id;
const fl=R('flows.json').filter(x=>x.IsActive&&!x.NamespacePrefix).map(x=>'Flow:'+x.ApiName);
const vr=R('vr.json').map(x=>'ValidationRule:'+obj(x.EntityDefinitionId)+'.'+x.ValidationName);
const sh=['SharingCriteriaRule','SharingOwnerRule'].flatMap(t=>{const r=require(inv+'/md_'+t+'.json').result;return (Array.isArray(r)?r:r?[r]:[]).map(x=>x.fullName.split('.')[0])});
const other=[...new Set(sh)].map(o=>'SharingRules:'+o)
  .concat([...new Set(R('ar.json').map(x=>'AssignmentRules:'+x.SobjectType))])
  .concat([...new Set(R('mr.json').map(x=>'MatchingRules:'+x.SobjectType))])
  .concat(R('dr.json').map(x=>'DuplicateRule:'+x.SobjectType+'.'+x.DeveloperName));
require('fs').writeFileSync('md_list.txt',[...fl,...vr,...other].join('\n'));
console.log('components: flows',fl.length,'validation rules',vr.length,'other',other.length);" "$INV"
args=()
while IFS= read -r m || [ -n "$m" ]; do [ -n "$m" ] && args+=(--metadata "$m"); done < md_list.txt  # last line has no newline
sf project retrieve start "${args[@]}" --target-org "$ORG" --wait 30 --json > retrieve.json
node -e "const j=require('./retrieve.json');const f=(j.result&&j.result.files)||[];const bad=f.filter(x=>x.state==='Failed');console.log('retrieved',f.length,'failed',bad.length);if(j.status!==0||bad.length){console.error(j.message||bad);process.exit(1)}"

echo "== active-version check"
# A retrieve returns the LATEST flow version. For any file that is not Active, fetch the ACTIVE version.
for f in force-app/main/default/flows/*.flow-meta.xml; do
  api=$(basename "$f" .flow-meta.xml)
  status=$(grep -o '<status>[A-Za-z]*</status>' "$f" | tail -1 | sed 's/<[^>]*>//g')
  if [ "$status" != "Active" ]; then
    id=$(node -e "const r=require(process.argv[1]).result.records.find(x=>x.ApiName===process.argv[2]);console.log(r.ActiveVersionId)" "$INV/flows.json" "$api")
    sf data query -o "$ORG" --use-tooling-api --json -q "SELECT Id, VersionNumber, Status, Metadata FROM Flow WHERE Id = '$id'" > "active_$api.json"
    echo "  $api: latest is $status -> using active version $id"
  fi
done
echo "done. next: ./run.sh $WORK <repo>/docs/salesforce/AUTOMATION_INVENTORY.md"
