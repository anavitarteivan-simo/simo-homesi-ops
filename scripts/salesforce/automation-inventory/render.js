// Builds the automation-inventory tables (markdown fragments) from the parsed metadata.
// Usage: node render.js <workDir>
const fs = require('fs');
const path = require('path');
const S = process.argv[2];
const inv = (n) => JSON.parse(fs.readFileSync(path.join(S, 'inv', n), 'utf8'));
const flows = inv('flows.summary.json');
const rules = inv('rules.summary.json');
// Hand-written "what it does" for flows that have no Description (see README).
const purpose = JSON.parse(fs.readFileSync(path.join(__dirname, 'purposes.json'), 'utf8'));

const esc = (s) => String(s || '').replace(/\|/g, '\\|').replace(/\r?\n/g, ' ').replace(/</g, '&lt;');
const cut = (s, n) => (s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s);
const code = (s) => '`' + String(s).replace(/`/g, "'").replace(/\|/g, '\\|') + '`';
const TIMING = { RecordBeforeSave: 'before-save', RecordAfterSave: 'after-save', RecordBeforeDelete: 'before-delete', Scheduled: 'scheduled' };
const OBJ = { 'Borrower Follow-Up': 'Borrower_Follow_Up__c', 'Work Item': 'Mortgage_Condition__c', 'Feed Item': 'FeedItem',
  'Opportunity Team Member': 'OpportunityTeamMember', 'Opportunity Contact Role': 'OpportunityContactRole', 'SMS History': 'tdc_tsw__Message__c' };

function entry(f) {
  const parts = [];
  if (f.recordTriggerType) parts.push({ Create: 'on create', Update: 'on update', CreateAndUpdate: 'on create/update', Delete: 'on delete' }[f.recordTriggerType] || f.recordTriggerType);
  if (f.schedule) parts.push('runs ' + f.schedule);
  if (f.filters.length) {
    const logic = f.filterLogic && !['and', 'or'].includes(f.filterLogic) ? ` [${f.filterLogic}]` : f.filterLogic === 'or' ? ' (any)' : '';
    parts.push(f.filters.map((x) => code(x)).join(', ') + logic);
  }
  if (f.filterFormula) parts.push('formula ' + code(cut(f.filterFormula, 140)));
  if (f.requireChange) parts.push('_only when criteria become newly true_');
  if (f.scheduledPaths.length) parts.push('scheduled paths: ' + f.scheduledPaths.map((p) => code(p)).join(', '));
  return parts.join('; ') || '—';
}

function effects(f) {
  const out = [];
  const recordFields = new Set(f.recordAssigns);
  const other = [];
  for (const w of f.writes) {
    if (!w.target || w.target === '$Record' || w.target === '?') w.fields.forEach((x) => recordFields.add(x));
    else other.push(`updates ${w.target.replace(/^\$Record\./, '$Record→')}` + (w.fields.length ? ` (${w.fields.join(', ')})` : ''));
  }
  if (recordFields.size) out.push('sets ' + [...recordFields].map((x) => code(x)).join(', '));
  const oc = {}; for (const o of other) oc[o] = (oc[o] || 0) + 1;
  out.push(...Object.entries(oc).map(([o, n]) => esc(o) + (n > 1 ? ` ×${n}` : '')));
  const cc = {}; for (const c of f.creates) cc[c.object] = (cc[c.object] || 0) + 1;
  for (const [o, n] of Object.entries(cc)) out.push(`creates ${code(o)}` + (n > 1 ? ` ×${n}` : ''));
  for (const d of f.deletes) out.push(`deletes ${code(d.object)}`);
  const acts = {};
  for (const a of f.actions) {
    const k = a.type === 'emailSimple' || a.type === 'emailAlert' ? 'email' : a.type === 'apex' ? `apex ${a.name}` : a.type === 'customNotificationAction' ? 'notification' : `${a.type} ${a.name || ''}`.trim();
    acts[k] = (acts[k] || 0) + 1;
  }
  for (const [k, n] of Object.entries(acts)) out.push(n > 1 ? `${esc(k)} ×${n}` : esc(k));
  for (const s of f.subflows) out.push('subflow ' + code(s));
  if (f.screens) out.push(`${f.screens} screen(s)`);
  return out.join('; ') || '—';
}

const what = (f) => {
  if (f.description) return esc(cut(f.description, 260));
  const t = purpose[f.api] || f.label;
  const i = t.indexOf('Note:');
  return '\* ' + esc(cut(i >= 0 ? t.slice(0, i).trim() : t, 240)) + (i >= 0 ? ' ⚠️ §7' : '');
};

// ---- flows grouped by object + timing
const groups = {};
for (const f of flows) {
  const obj = f.triggerType ? (OBJ[f.object] || f.object || 'No object') : (f.processType === 'Flow' ? 'Screen flows' : f.processType === 'Survey' ? 'Surveys' : 'Autolaunched (called by other automation)');
  (groups[obj] = groups[obj] || []).push(f);
}
const order = ['Opportunity', 'Lead', 'Task', 'Mortgage_Condition__c', 'OpportunityTeamMember', 'OpportunityContactRole', 'FeedItem', 'tdc_tsw__Message__c', 'Borrower_Follow_Up__c', 'Follow_Up_Request__c', 'Event', 'Contact', 'No object', 'Screen flows', 'Autolaunched (called by other automation)', 'Surveys'];
const keys = Object.keys(groups).sort((a, b) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99));
let md = '';
let sec = 1;
for (const k of keys) {
  const list = groups[k].sort((a, b) => (TIMING[a.triggerType] || '').localeCompare(TIMING[b.triggerType] || '') || a.api.localeCompare(b.api));
  md += `### 3.${sec++} ${k} (${list.length})\n\n`;
  md += '| Flow | Timing | Fires when | What it does | Effects |\n|---|---|---|---|---|\n';
  for (const f of list) {
    md += `| ${code(f.api)} | ${TIMING[f.triggerType] || f.processType}${f.triggerOrder ? ' #' + f.triggerOrder : ''} | ${entry(f)} | ${what(f)} | ${effects(f)} |\n`;
  }
  md += '\n';
}
fs.writeFileSync(path.join(S, 'inv', 'md_flows.md'), md);

// ---- validation rules
let vr = '';
let vn = 1;
for (const obj of [...new Set(rules.vr.map((v) => v.object))]) {
  const list = rules.vr.filter((v) => v.object === obj).sort((a, b) => (b.active - a.active) || a.name.localeCompare(b.name));
  vr += `#### 4.1.${vn++} ${obj} (${list.filter((v) => v.active).length} active / ${list.length})\n\n| Rule | Active | Blocks the save when | Error shown |\n|---|---|---|---|\n`;
  for (const v of list) vr += `| ${code(v.name)} | ${v.active ? 'yes' : 'no'} | ${code(cut(v.formula, 300))} | ${esc(cut(v.message, 160))}${v.field ? ` _(on ${v.field})_` : ''} |\n`;
  vr += '\n';
}
fs.writeFileSync(path.join(S, 'inv', 'md_vr.md'), vr);

// ---- sharing rules
let sh = '| Object | Rule | Type | Access | Shared to | Records matched by |\n|---|---|---|---|---|---|\n';
for (const s of rules.sharing.sort((a, b) => a.object.localeCompare(b.object) || a.name.localeCompare(b.name))) {
  const to = Object.entries(JSON.parse(s.to)).map(([t, g]) => (g ? `${t} ${g}` : t)).join(', ');
  const from = s.from ? Object.entries(JSON.parse(s.from)).map(([t, g]) => (g ? `${t} ${g}` : t)).join(', ') : '';
  sh += `| ${s.object} | ${code(s.name)} | ${s.kind} | ${s.access} | ${esc(to)} | ${s.kind === 'owner' ? 'owned by ' + esc(from) : code(cut(s.criteria, 320))} |\n`;
}
fs.writeFileSync(path.join(S, 'inv', 'md_sharing.md'), sh);

// ---- duplicate / matching / assignment
let dm = '**Duplicate rules**\n\n| Rule | Active | On create | On edit | Matching rule |\n|---|---|---|---|---|\n';
for (const d of rules.dup) dm += `| ${code(d.name)} | ${d.active ? 'yes' : 'no'} | ${d.onCreate || ''} | ${d.onEdit || ''} | ${esc(d.matching)} |\n`;
dm += '\n**Matching rules**\n\n| Object | Rule | Status | Fields (method) |\n|---|---|---|---|\n';
for (const m of rules.match) dm += `| ${m.object} | ${code(m.name)} | ${m.status} | ${esc(m.items)} |\n`;
fs.writeFileSync(path.join(S, 'inv', 'md_dupmatch.md'), dm);

const missing = flows.filter((f) => !f.description && !purpose[f.api]).map((f) => f.api);
console.log('groups', keys.map((k) => `${k}:${groups[k].length}`).join(', '));
console.log('flows without description or purpose:', missing.length, missing.join(', '));
