// Parses retrieved flow metadata into a structured summary (inv/flows.summary.json).
// Usage: node analyze-flows.js <workDir>
// Uses mdproj/active_<ApiName>.json (Tooling API, ACTIVE version) when fetch.sh wrote one,
// because a metadata retrieve returns the LATEST version, which may be a draft.
const fs = require('fs');
const path = require('path');
const { XMLParser } = require('fast-xml-parser');

const S = process.argv[2];
const flowDir = path.join(S, 'mdproj/force-app/main/default/flows');
const inv = require(path.join(S, 'inv/flows.json')).result.records;
const ARR = new Set(['filters', 'inputAssignments', 'recordUpdates', 'recordCreates', 'recordDeletes', 'recordLookups',
  'actionCalls', 'subflows', 'decisions', 'rules', 'conditions', 'assignments', 'assignmentItems', 'scheduledPaths',
  'loops', 'screens', 'formulas', 'variables', 'inputParameters', 'outputAssignments', 'waits', 'collectionProcessors',
  'transforms', 'customErrors', 'customErrorMessages', 'apexPluginCalls', 'orchestratedStages']);
const parser = new XMLParser({ ignoreAttributes: true, isArray: (name) => ARR.has(name), parseTagValue: false });

const arr = (v) => (v == null ? [] : Array.isArray(v) ? v : [v]);
const val = (v) => {
  if (v == null) return '';
  if (typeof v !== 'object') return String(v);
  for (const k of ['stringValue', 'elementReference', 'booleanValue', 'numberValue', 'dateValue', 'dateTimeValue']) {
    if (v[k] != null) return k === 'elementReference' ? '{!' + v[k] + '}' : String(v[k]);
  }
  return '';
};
const cond = (f) => `${f.field || f.leftValueReference || ''} ${f.operator || ''} ${val(f.value || f.rightValue)}`.trim();

function load(api) {
  const active = path.join(S, 'mdproj', `active_${api}.json`);
  if (fs.existsSync(active)) return require(active).result.records[0].Metadata; // tooling JSON of the ACTIVE version
  const xml = fs.readFileSync(path.join(flowDir, `${api}.flow-meta.xml`), 'utf8');
  return parser.parse(xml).Flow;
}

const out = [];
for (const d of inv.filter((x) => x.IsActive && !x.NamespacePrefix)) {
  const f = load(d.ApiName);
  const start = f.start || {};

  // Resolve variable / lookup names to their sObject type, and fields assigned on those variables.
  const vars = {};
  for (const v of arr(f.variables)) if (v.objectType) vars[v.name] = v.objectType + (String(v.isCollection) === 'true' ? '[]' : '');
  for (const l of arr(f.recordLookups)) if (l.object) vars[l.name] = l.object;
  const varFields = {};
  const recordAssigns = [];
  for (const a of arr(f.assignments)) {
    for (const it of arr(a.assignmentItems)) {
      const ref = it.assignToReference || '';
      if (ref.startsWith('$Record.')) { recordAssigns.push(ref.slice(8)); continue; }
      const i = ref.indexOf('.');
      if (i > 0 && ref.charAt(0) !== '$') {
        const v = ref.slice(0, i);
        (varFields[v] = varFields[v] || new Set()).add(ref.slice(i + 1));
      }
    }
  }

  const writes = [];
  for (const u of arr(f.recordUpdates)) {
    const target = u.inputReference ? (vars[u.inputReference] || u.inputReference) : u.object || '?';
    const fields = arr(u.inputAssignments).map((a) => a.field);
    if (!fields.length && u.inputReference && varFields[u.inputReference]) fields.push(...varFields[u.inputReference]);
    writes.push({ el: u.name, target, fields, filters: arr(u.filters).map(cond), fault: !!u.faultConnector });
  }
  const creates = arr(f.recordCreates).map((c) => ({ el: c.name, object: c.object || vars[c.inputReference] || c.inputReference || '?',
    fields: arr(c.inputAssignments).map((a) => a.field), fault: !!c.faultConnector }));
  const deletes = arr(f.recordDeletes).map((c) => ({ el: c.name, object: c.object || vars[c.inputReference] || c.inputReference || '?' }));
  const lookups = [...new Set(arr(f.recordLookups).map((l) => l.object).filter(Boolean))];
  const actions = arr(f.actionCalls).map((a) => ({ el: a.name, type: a.actionType, name: a.actionName, fault: !!a.faultConnector }));
  const subflows = arr(f.subflows).map((s) => s.flowName);
  const filters = arr(start.filters).map(cond);

  const hazards = [];
  const after = start.triggerType === 'RecordAfterSave';
  for (const a of actions) if (after && /email/i.test(a.type || '') && !a.fault) hazards.push(`email action ${a.el} has no fault path (a send failure rolls back the save)`);
  for (const x of filters) if (/^[A-Za-z0-9_]+\.[A-Za-z]/.test(x)) hazards.push(`entry filter uses a cross-object field: ${x}`);

  out.push({
    api: d.ApiName, label: f.label || d.Label, description: (f.description || '').replace(/\s+/g, ' ').trim(),
    processType: d.ProcessType, triggerType: d.TriggerType || '', recordTriggerType: d.RecordTriggerType || '',
    object: start.object || d.TriggerObjectOrEventLabel || '', runInMode: f.runInMode || '',
    triggerOrder: start.triggerOrder || '', requireChange: String(start.doesRequireRecordChangedToMeetCriteria || '') === 'true',
    filterLogic: start.filterLogic || '', filters, filterFormula: (start.filterFormula || '').replace(/\s+/g, ' ').trim(),
    schedule: start.schedule ? `${start.schedule.frequency || ''} ${start.schedule.startTime || ''}`.trim() : '',
    scheduledPaths: arr(start.scheduledPaths).map((p) => `${p.name || p.pathType || 'path'}: ${p.offsetNumber || ''} ${p.offsetUnit || ''} ${p.timeSource || ''} ${p.recordField || ''}`.trim()),
    writes, recordAssigns: [...new Set(recordAssigns)], creates, deletes, lookups, actions, subflows,
    decisions: arr(f.decisions).length, screens: arr(f.screens).length, loops: arr(f.loops).length,
    lastModified: d.LastModifiedDate.slice(0, 10), lastModifiedBy: d.LastModifiedBy || '', hazards,
  });
}
fs.writeFileSync(path.join(S, 'inv/flows.summary.json'), JSON.stringify(out, null, 1));
console.log('flows summarized:', out.length);
console.log('with description:', out.filter((x) => x.description).length);
console.log('hazards:', out.filter((x) => x.hazards.length).map((x) => x.api + ' -> ' + x.hazards.join(' | ')).join('\n'));
