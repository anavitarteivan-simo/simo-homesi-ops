// Parses retrieved validation / sharing / duplicate / matching / assignment rules into inv/rules.summary.json.
// Usage: node analyze-rules.js <workDir>
const fs=require('fs'),path=require('path');const {XMLParser}=require('fast-xml-parser');
const S=process.argv[2];const base=path.join(S,'mdproj/force-app/main/default');
const p=new XMLParser({ignoreAttributes:true,parseTagValue:false,isArray:n=>['criteriaItems','sharingCriteriaRules','sharingOwnerRules','matchingRules','matchingRuleItems','duplicateRuleMatchingRules','ruleEntry','assignmentRule','rules'].includes(n)});
const arr=v=>v==null?[]:Array.isArray(v)?v:[v];const out={vr:[],sharing:[],dup:[],match:[],assign:[]};
for(const obj of fs.readdirSync(path.join(base,'objects'))){const d=path.join(base,'objects',obj,'validationRules');if(!fs.existsSync(d))continue;
 for(const f of fs.readdirSync(d)){const v=p.parse(fs.readFileSync(path.join(d,f),'utf8')).ValidationRule;
  out.vr.push({object:obj,name:v.fullName||f.replace('.validationRule-meta.xml',''),active:v.active==='true',formula:(v.errorConditionFormula||'').replace(/\s+/g,' ').trim(),message:(v.errorMessage||'').replace(/\s+/g,' ').trim(),field:v.errorDisplayField||'',description:(v.description||'').replace(/\s+/g,' ').trim()});}}
for(const f of fs.readdirSync(path.join(base,'sharingRules'))){const obj=f.split('.')[0];const r=p.parse(fs.readFileSync(path.join(base,'sharingRules',f),'utf8')).SharingRules;
 for(const c of arr(r.sharingCriteriaRules))out.sharing.push({object:obj,kind:'criteria',name:c.fullName,label:c.label,access:c.accessLevel,to:JSON.stringify(c.sharedTo),criteria:arr(c.criteriaItems).map((i,n)=>`${c.booleanFilter?(n+1)+') ':''}${i.field} ${i.operation} ${i.value||''}`.trim()).join(c.booleanFilter?'; ':' AND ')+(c.booleanFilter?` — logic ${c.booleanFilter}`:''),includeHV:c.includeRecordsOwnedByAll});
 for(const c of arr(r.sharingOwnerRules))out.sharing.push({object:obj,kind:'owner',name:c.fullName,label:c.label,access:c.accessLevel,to:JSON.stringify(c.sharedTo),from:JSON.stringify(c.sharedFrom)});}
const dd=path.join(base,'duplicateRules');for(const f of fs.readdirSync(dd)){const r=p.parse(fs.readFileSync(path.join(dd,f),'utf8')).DuplicateRule;out.dup.push({name:f.replace('.duplicateRule-meta.xml',''),active:r.isActive==='true',onCreate:r.actionOnInsert,onEdit:r.actionOnUpdate,matching:arr(r.duplicateRuleMatchingRules).map(m=>m.matchingRule+'('+m.matchRuleSObjectType+')').join(', ')});}
const md=path.join(base,'matchingRules');for(const f of fs.readdirSync(md)){const r=p.parse(fs.readFileSync(path.join(md,f),'utf8')).MatchingRules;for(const m of arr(r.matchingRules))out.match.push({object:f.split('.')[0],name:m.fullName,status:m.ruleStatus,items:arr(m.matchingRuleItems).map(i=>i.fieldName+':'+i.matchingMethod).join(', ')});}
const ad=path.join(base,'assignmentRules');for(const f of fs.readdirSync(ad)){const r=p.parse(fs.readFileSync(path.join(ad,f),'utf8')).AssignmentRules;for(const a of arr(r.assignmentRule))out.assign.push({object:f.split('.')[0],name:a.fullName,active:a.active,entries:arr(a.ruleEntry).length});}
fs.writeFileSync(path.join(S,'inv/rules.summary.json'),JSON.stringify(out,null,1));
console.log('vr',out.vr.length,'sharing',out.sharing.length,'dup',out.dup.length,'match',out.match.length,'assign',JSON.stringify(out.assign));
const c={};for(const s of out.sharing){const k=s.object+' '+s.kind+' '+s.access+' -> '+s.to;c[k]=(c[k]||0)+1}console.log(c);
console.log(out.sharing.filter(s=>s.kind==='owner'));console.log(out.dup);
