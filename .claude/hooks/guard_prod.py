#!/usr/bin/env python3
"""PreToolUse guard for simo-homesi-ops.

Forces a confirmation prompt ("ask") before anything that can change a production
system: Salesforce CLI writes against prod (or with no explicit --target-org), write-type
MCP calls to the prod Salesforce / n8n / Customer.io servers, and anything touching the
FUR kill switch. Reads are never blocked.

Emits nothing (normal permission flow) when the call is not risky.
"""
import json
import re
import sys

PROD_ALIASES = {"prod"}
PROD_MARKERS = (
    "ruby-ruby-7485.my.salesforce.com",
    "00DKb000000OvoRMAS",
)
# Prod usernames: exact match, so the ".staging" sandbox username is not caught.
PROD_USERNAMES = {
    "m.rodriguez@supremelending.com",
    "sfintegrations@citylendinginc.com",
}

SF_WRITE = re.compile(
    r"\bsf\s+(project\s+deploy\s+(start|resume|quick)"
    r"|project\s+delete"
    r"|data\s+(create|update|delete|upsert|import|bulk)"
    r"|data\s+\w+\s+(bulk|resume)"
    r"|apex\s+run"
    r"|org\s+(delete|create)"
    r"|config\s+set\s+target-org)\b"
)
SF_SAFE_FLAGS = re.compile(r"--dry-run\b|\bproject\s+deploy\s+validate\b")
TARGET = re.compile(r"(?:--target-org|-o)[=\s]+(\S+)")

MCP_WRITE = re.compile(
    r"(create|update|delete|upsert|insert|merge|deploy|publish|activate|deactivate"
    r"|archive|execute|run|send|trigger|start|stop|pause|resume|import)",
    re.IGNORECASE,
)
MCP_PROD_SERVERS = ("salesforce-prod", "n8n", "customerio")


def ask(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def check_bash(cmd: str) -> None:
    if "fur_settings" in cmd or "Test_Mode__c" in cmd:
        ask("KILL SWITCH: this command references fur_settings / Test_Mode__c. "
            "Only proceed on an explicit instruction.")
    if not SF_WRITE.search(cmd) or SF_SAFE_FLAGS.search(cmd):
        return
    m = TARGET.search(cmd)
    target = m.group(1).strip("'\"") if m else None
    if target is None:
        ask("Salesforce write with NO --target-org. The default org can change; "
            "pass --target-org explicitly.")
    if (target in PROD_ALIASES or target in PROD_USERNAMES
            or any(mk in target for mk in PROD_MARKERS)):
        ask(f"PRODUCTION Salesforce write (target-org={target}). "
            "Was this deployed and verified in homesi-staging first?")


def check_mcp(tool: str, tool_input: dict) -> None:
    # tool names look like mcp__<server>__<tool>
    parts = tool.split("__")
    server = parts[1].lower() if len(parts) > 2 else ""
    name = parts[-1]
    payload = json.dumps(tool_input)
    is_write = bool(MCP_WRITE.search(name))
    if is_write and ("fur_settings" in payload or "test_mode" in payload.lower()):
        ask("KILL SWITCH: this call writes fur_settings / test_mode. "
            "Only proceed on an explicit instruction.")
    if is_write and server.startswith(MCP_PROD_SERVERS):
        ask(f"PRODUCTION write via MCP ({server} → {name}). Confirm before it runs.")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # never break the session because of the guard itself
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}
    if tool == "Bash":
        check_bash(tool_input.get("command", ""))
    elif tool.startswith("mcp__"):
        check_mcp(tool, tool_input)


if __name__ == "__main__":
    main()
