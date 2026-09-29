# Project skills

Claude Code loads skills from `.claude/skills/<name>/SKILL.md`.

The handover (Part 12, Appendix G) lists three business skills that live on the departing
admin's machine. Copy each folder here when you get it:

| Skill | Folder to create | Notes |
|---|---|---|
| `salesforce-lead-import` | `.claude/skills/salesforce-lead-import/` | Writes `NEW.csv` / `IN_QUESTION.csv` — point its output at `data/` (git-ignored, PII). |
| `recruitment-copilot` | `.claude/skills/recruitment-copilot/` | Needs Salesforce MCP + a browser for MMI / NMLS. Keep one version only (there were two). |
| `fha-lrs-binder` | `.claude/skills/fha-lrs-binder/` | Uses AWS + heavy borrower PII. The skill's code can live here; binders and eFolders never do. Do not re-enable it with the AWS **root** key. |

Before committing a skill, scan it for hardcoded secrets or borrower data.
