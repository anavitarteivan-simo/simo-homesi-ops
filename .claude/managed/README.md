# Managed settings (org-wide Claude Code rules)

`managed-settings.json` holds the "never" rules of `docs/CHANGE_POLICY.md` §3 as permission
deny rules. Once installed on a machine, they apply to **every** repo opened with Claude Code
(including the Lambda repos), and project, local or user settings cannot override them.

This file is the reference copy. It does nothing until installed.

## Install (needs admin rights on the machine)

| OS | Path |
|---|---|
| Windows | `C:\Program Files\ClaudeCode\managed-settings.json` |
| macOS | `/Library/Application Support/ClaudeCode/managed-settings.json` |
| Linux / WSL | `/etc/claude-code/managed-settings.json` |

Windows (elevated PowerShell), from the repo root:
```powershell
New-Item -ItemType Directory -Force "C:\Program Files\ClaudeCode" | Out-Null
Copy-Item .claude\managed\managed-settings.json "C:\Program Files\ClaudeCode\managed-settings.json"
```
Restart Claude Code, then ask it to run a dry-run push to main. It must be refused.

With a Claude for Work / Enterprise plan, the same JSON can be pushed from the admin console
instead of copied by hand. Source: https://code.claude.com/docs/en/managed-settings.md

## What managed settings cannot do alone

Permission rules match command **prefixes**. A bare `git push` while on `main` does not
match `git push origin main*`. The hook (`.claude/hooks/guard.py`) catches that case, and
the GitHub ruleset catches it for everyone. Keep all three layers.

Optional hardening, once every repo has the guard installed (`scripts/claude/install-policy.sh`):
- `"allowManagedHooksOnly": true` suppresses project/user hooks. The guard would then have
  to be installed as a managed hook pointing to a fixed path on the machine.
- `"allowManagedPermissionRulesOnly": true` ignores all non-managed permission rules.

Both are managed-only keys. Do not enable them before a managed copy of the guard exists.

## Changing it

Edit this file in a PR (with the matching `guard.py` rule and test), then re-install it on
each machine. Record the date installed per machine in the PR description.
