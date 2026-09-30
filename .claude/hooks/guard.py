#!/usr/bin/env python3
"""PreToolUse guard for simo-homesi-ops.

Enforces docs/CHANGE_POLICY.md inside Claude Code. Two decisions:

- "deny": the change path is forbidden for Claude (push/commit to main, force push, local
  Lambda/serverless deploys, prod Salesforce deploys of unmerged code).
- "ask":  allowed, but a human must confirm (prod writes, kill switches, repo settings,
  AWS writes, reading secrets).

Reads are never blocked. When nothing matches, the guard prints nothing and the normal
permission flow applies. The guard fails CLOSED: if it crashes it asks rather than
silently letting the call through.

Runs on Python 3.8+ (invoked by guard.sh). Tests: .claude/hooks/test_guard.py
"""
import json
import os
import re
import shlex
import subprocess
import sys

POLICY = "docs/CHANGE_POLICY.md"

# --- Salesforce -------------------------------------------------------------------------
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
SF_PROD_DEPLOY = re.compile(r"\bsf\s+project\s+deploy\s+(start|quick)\b")
SF_SAFE_FLAGS = re.compile(r"--dry-run\b|\bproject\s+deploy\s+validate\b")
TARGET = re.compile(r"(?:--target-org|-o)[=\s]+(\S+)")

# --- Git / GitHub -----------------------------------------------------------------------
PROTECTED_BRANCHES = {"main", "master"}
GIT_COMMITTING = {"commit", "merge", "cherry-pick", "revert", "am"}

# --- AWS / Lambda -----------------------------------------------------------------------
# Deploys of Lambdas / stacks go through each repo's CI, never from a laptop.
LOCAL_DEPLOY = re.compile(
    r"\b(?:serverless|sls)\s+(?:deploy|remove|rollback)\b"
    r"|\bsam\s+(?:deploy|delete|sync)\b"
    r"|\bcdk\s+(?:deploy|destroy)\b"
    r"|\bamplify\s+(?:publish|push)\b"
    r"|\baws\s+lambda\s+(?:update-function-code|update-function-configuration|publish-version"
    r"|create-function|delete-function|create-alias|update-alias|delete-alias"
    r"|put-function-concurrency|add-permission|remove-permission)\b"
    r"|\baws\s+cloudformation\s+(?:deploy|create-stack|update-stack|delete-stack)\b"
)
AWS_SECRET_READ = re.compile(
    r"\baws\s+secretsmanager\s+get-secret-value\b"
    r"|\baws\s+ssm\s+get-parameters?\b.*--with-decryption"
)
AWS_WRITE = re.compile(
    r"\baws\s+[\w-]+\s+(?:create|delete|put|update|remove|terminate|modify|attach|detach"
    r"|start|stop|reboot|run|invoke|publish|send|tag|untag|restore|reset|revoke|authorize"
    r"|set|enable|disable|import|register|deregister|associate|disassociate)[\w-]*\b"
    r"|\baws\s+s3\s+(?:rm|mv|sync|cp|rb|mb)\b"
)

# --- MCP --------------------------------------------------------------------------------
MCP_WRITE = re.compile(
    r"(create|update|delete|upsert|insert|merge|deploy|publish|activate|deactivate"
    r"|archive|execute|run|send|trigger|start|stop|pause|resume|import)",
    re.IGNORECASE,
)

SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]|\$\(|`")
WRAPPERS = {"npx", "npm", "pnpm", "yarn", "bunx", "sudo", "time", "command", "exec",
            "env", "nohup", "xargs"}
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

RANK = {"ask": 1, "deny": 2}


# --- helpers that touch the machine (patched in tests) ------------------------------------
def _git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd or ".", *args], capture_output=True,
                             text=True, timeout=5)
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_branch(cwd):
    """Current branch name, or None if unknown / detached."""
    b = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    return None if b in (None, "HEAD") else b


def sf_source_problem(cwd):
    """Why the working tree is not a merged, clean copy of origin/main (None if it is)."""
    top = _git(cwd, "rev-parse", "--show-toplevel")
    if top is None:
        return "not inside a git repository"
    if _git(top, "status", "--porcelain", "--", "salesforce") not in ("",):
        return "salesforce/ has uncommitted changes"
    _git(top, "fetch", "--quiet", "origin", "main")
    head = _git(top, "rev-parse", "HEAD")
    main = _git(top, "rev-parse", "origin/main")
    if head is None or main is None:
        return "could not resolve HEAD / origin/main"
    if head != main:
        return "HEAD is not origin/main (deploy prod only from merged, up-to-date main)"
    return None


# --- parsing ----------------------------------------------------------------------------
def _tokens(segment):
    try:
        toks = shlex.split(segment, posix=True)
    except ValueError:
        toks = segment.split()
    while toks and ENV_ASSIGN.match(toks[0]):
        toks.pop(0)
    return toks


def _strip_ref(ref):
    for prefix in ("refs/heads/", "refs/remotes/origin/"):
        if ref.startswith(prefix):
            return ref[len(prefix):]
    return ref


# --- rules ------------------------------------------------------------------------------
def check_git(toks, cwd):
    """toks start with 'git'. Returns list of (decision, reason)."""
    i = 1
    while i < len(toks) and toks[i].startswith("-"):
        if toks[i] in ("-C", "-c") and i + 1 < len(toks):
            if toks[i] == "-C":
                cwd = os.path.join(cwd or ".", toks[i + 1])
            i += 2
        else:
            i += 1
    if i >= len(toks):
        return []
    sub, args = toks[i], toks[i + 1:]

    if sub in GIT_COMMITTING:
        branch = git_branch(cwd)
        if branch in PROTECTED_BRANCHES:
            return [("deny", f"git {sub} on protected branch '{branch}'. Create a branch "
                             f"(area/short-description) and open a PR. See {POLICY}.")]
        return []

    if sub != "push":
        return []

    flags = [a for a in args if a.startswith("-")]
    positional = [a for a in args if not a.startswith("-")]
    for f in flags:
        if (f in ("--force", "--force-if-includes", "--mirror", "--all")
                or f.startswith("--force-with-lease")
                or (re.fullmatch(r"-[a-zA-Z]+", f) and "f" in f)):
            return [("deny", f"git push {f} is forbidden (rewrites or mass-pushes shared "
                             f"history). See {POLICY}.")]
    deleting = any(f in ("--delete", "-d") for f in flags)
    refspecs = positional[1:]
    if not refspecs:
        branch = git_branch(cwd)
        if branch in PROTECTED_BRANCHES:
            return [("deny", f"git push from '{branch}' pushes straight to a protected "
                             f"branch. Push a feature branch and open a PR. See {POLICY}.")]
        return []
    for spec in refspecs:
        if spec.startswith("+"):
            return [("deny", f"force refspec '{spec}' is forbidden. See {POLICY}.")]
        src, _, dst = spec.partition(":")
        target = dst if dst else src
        if target == "HEAD":
            target = git_branch(cwd) or "HEAD"
        if _strip_ref(target) in PROTECTED_BRANCHES:
            verb = "delete" if deleting or (dst and not src) else "push to"
            return [("deny", f"git push would {verb} protected branch "
                             f"'{_strip_ref(target)}'. Open a PR instead. See {POLICY}.")]
    return []


def check_gh(toks):
    if len(toks) < 3:
        return []
    group, cmd, rest = toks[1], toks[2], toks[3:]
    if group == "pr" and cmd == "merge":
        if "--admin" in rest:
            return [("deny", "gh pr merge --admin bypasses branch rules. See " + POLICY)]
        return [("ask", "Merging a PR. Confirm it was reviewed and its checklist is complete.")]
    if group == "repo" and cmd in ("edit", "delete", "rename", "archive"):
        return [("ask", f"gh repo {cmd} changes repository settings. Confirm first.")]
    if group == "api":
        method = None
        for j, t in enumerate(toks):
            if t in ("-X", "--method") and j + 1 < len(toks):
                method = toks[j + 1].upper()
            elif t.startswith("--method="):
                method = t.split("=", 1)[1].upper()
        writes_fields = any(t in ("-f", "-F", "--field", "--raw-field", "--input")
                            for t in toks)
        if (method and method != "GET") or (method is None and writes_fields):
            return [("ask", "gh api write call (may change repo settings, rulesets or "
                            "visibility). Confirm first.")]
    return []


def check_sf(cmd, cwd):
    findings = []
    if not SF_WRITE.search(cmd) or SF_SAFE_FLAGS.search(cmd):
        return findings
    m = TARGET.search(cmd)
    target = m.group(1).strip("'\"") if m else None
    if target is None:
        return [("ask", "Salesforce write with NO --target-org. The default org can change; "
                        "pass --target-org explicitly.")]
    is_prod = (target in PROD_ALIASES or target in PROD_USERNAMES
               or any(mk in target for mk in PROD_MARKERS))
    if not is_prod:
        return findings
    if SF_PROD_DEPLOY.search(cmd):
        problem = sf_source_problem(cwd)
        if problem:
            return [("deny", f"PRODUCTION deploy blocked: {problem}. Merge the PR, "
                             f"`git switch main && git pull`, then deploy. Break-glass "
                             f"procedure: {POLICY}.")]
    findings.append(("ask", f"PRODUCTION Salesforce write (target-org={target}). "
                            "Was this deployed and verified in homesi-staging first?"))
    return findings


def _command_tokens(seg):
    """Tokens of the program actually run in a segment, without launcher prefixes
    (npx, sudo, time...), so `grep "serverless deploy"` is not mistaken for a deploy."""
    toks = _tokens(seg)
    while toks and toks[0] in WRAPPERS:
        toks = toks[1:]
        while toks and (toks[0].startswith("-") or ENV_ASSIGN.match(toks[0])
                        or toks[0] in ("exec", "dlx")):
            toks = toks[1:]
    if toks:
        head = os.path.basename(toks[0]).lower()
        for ext in (".exe", ".cmd", ".bat"):
            if head.endswith(ext):
                head = head[: -len(ext)]
        toks = [head] + toks[1:]
    return toks


def check_command(toks, cwd):
    head, line = toks[0], " ".join(toks)
    if head == "git":
        return check_git(toks, cwd)
    if head == "gh":
        return check_gh(toks)
    if head == "sf" and SF_WRITE.search(line):
        return check_sf(line, cwd)
    if head in ("serverless", "sls", "sam", "cdk", "amplify", "aws"):
        if LOCAL_DEPLOY.search(line):
            return [("deny", "Local deploy of a Lambda / stack is forbidden: push a branch to "
                             "that service's repo, open a PR, and let its CI deploy. "
                             f"See {POLICY}.")]
        if AWS_SECRET_READ.search(line):
            return [("ask", "This prints a secret value from AWS. Never paste it into the "
                            "repo or the conversation. Confirm first.")]
        if AWS_WRITE.search(line):
            return [("ask", "AWS write call (prod account). Confirm first.")]
    return []


def check_bash(cmd, cwd):
    findings = []
    # Kill switches: any mention at all, wherever it appears.
    if "fur_settings" in cmd or "Test_Mode__c" in cmd:
        findings.append(("ask", "KILL SWITCH: this command references fur_settings / "
                                "Test_Mode__c. Only proceed on an explicit instruction."))
    seg_cwd = cwd
    for seg in SEGMENT_SPLIT.split(cmd):
        toks = _command_tokens(seg)
        if not toks:
            continue
        if toks[0] == "cd" and len(toks) >= 2:
            seg_cwd = os.path.join(seg_cwd or ".", toks[1])
            continue
        findings += check_command(toks, seg_cwd)
    return findings


def _is_prod_server(server):
    s = server.lower()
    if "salesforce" in s:
        return not any(x in s for x in ("staging", "sandbox"))
    return (any(x in s for x in ("n8n", "customerio", "customer_io", "customer-io",
                                 "bigquery", "aws"))
            or s in ("make", "claude_ai_make"))


def check_mcp(tool, tool_input):
    # mcp__<server>__<tool>; the server part may itself contain "__".
    body = tool[len("mcp__"):]
    server, _, name = body.rpartition("__")
    payload = json.dumps(tool_input)
    is_write = bool(MCP_WRITE.search(name))
    findings = []
    if is_write and ("fur_settings" in payload or "test_mode" in payload.lower()):
        findings.append(("ask", "KILL SWITCH: this call writes fur_settings / test_mode. "
                                "Only proceed on an explicit instruction."))
    if is_write and _is_prod_server(server):
        findings.append(("ask", f"PRODUCTION write via MCP ({server} -> {name}). "
                                "Confirm before it runs."))
    return findings


def decide(data):
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}
    if tool == "Bash":
        return check_bash(tool_input.get("command", ""), data.get("cwd"))
    if tool.startswith("mcp__"):
        return check_mcp(tool, tool_input)
    return []


def emit(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        findings = decide(json.loads(raw) if raw.strip() else {})
    except Exception as exc:  # fail closed
        emit("ask", f"GUARD ERROR ({type(exc).__name__}: {exc}). The prod guard could not "
                    "check this call. Confirm manually.")
        return
    if not findings:
        return
    top = max(RANK[d] for d, _ in findings)
    decision = "deny" if top == RANK["deny"] else "ask"
    reasons = [r for d, r in findings if RANK[d] == top]
    emit(decision, " | ".join(dict.fromkeys(reasons)))


if __name__ == "__main__":
    main()
