// Assembles the final AUTOMATION_INVENTORY.md and checks table integrity.
// Usage: node assemble.js <workDir> <output.md>
const fs = require('fs');
const path = require('path');
const S = process.argv[2];
const OUT = process.argv[3];
const r = (n) => fs.readFileSync(path.join(S, 'inv', n), 'utf8').trim();
const own = (n) => fs.readFileSync(path.join(__dirname, n), 'utf8');
const d = own('template.md')
  .replace('{{FLOWS}}', () => r('md_flows.md'))
  .replace('{{VR}}', () => r('md_vr.md'))
  .replace('{{SHARING}}', () => r('md_sharing.md'))
  .replace('{{DUPMATCH}}', () => r('md_dupmatch.md'))
  .replace('{{FINDINGS}}', () => own('findings.md').trim());
fs.writeFileSync(OUT, d);

const cols = (l) => l.replace(/\\\|/g, '').split('|').length;
let hdr = null;
const bad = [];
d.split('\n').forEach((l, i) => {
  if (!l.startsWith('|')) { hdr = null; return; }
  if (hdr === null) { hdr = cols(l); return; }
  if (cols(l) !== hdr) bad.push(i + 1);
});
console.log('lines', d.split('\n').length, '| malformed rows', bad.length, bad.slice(0, 5), '| placeholders', (d.match(/\{\{[A-Z]+\}\}/g) || []).length);
