"""Tests for guard.py — every rule in docs/CHANGE_POLICY.md §3 has a case here.

Run:  python .claude/hooks/test_guard.py        (CI runs it on every PR)
Git state is faked: no test touches a real repo or network.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import guard  # noqa: E402


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "/repo"}


def mcp(tool, **tool_input):
    return {"tool_name": tool, "tool_input": tool_input}


def verdict(data):
    findings = guard.decide(data)
    if not findings:
        return None
    return "deny" if any(d == "deny" for d, _ in findings) else "ask"


class Base(unittest.TestCase):
    branch = "repo/feature"
    sf_problem = None

    def setUp(self):
        self._orig = (guard.git_branch, guard.sf_source_problem)
        guard.git_branch = lambda cwd: self.branch
        guard.sf_source_problem = lambda cwd: self.sf_problem

    def tearDown(self):
        guard.git_branch, guard.sf_source_problem = self._orig

    def check(self, cases):
        for data, expected in cases:
            label = data["tool_input"].get("command", data["tool_name"])
            with self.subTest(label):
                self.assertEqual(verdict(data), expected)


class GitOnFeatureBranch(Base):
    def test_rules(self):
        self.check([
            (bash("git push"), None),
            (bash("git push -u origin repo/feature"), None),
            (bash("git push origin HEAD"), None),
            (bash("git commit -m 'x'"), None),
            (bash("git push origin main"), "deny"),
            (bash("git push origin HEAD:main"), "deny"),
            (bash("git push origin feature:refs/heads/master"), "deny"),
            (bash("git push origin :main"), "deny"),
            (bash("git push --delete origin main"), "deny"),
            (bash("git push --force origin repo/feature"), "deny"),
            (bash("git push -f"), "deny"),
            (bash("git push -uf origin x"), "deny"),
            (bash("git push --force-with-lease"), "deny"),
            (bash("git push origin +repo/feature"), "deny"),
            (bash("git push --all"), "deny"),
            (bash("git status && git log --oneline -3"), None),
            (bash("git -C other/repo push origin main"), "deny"),
        ])


class GitOnMain(Base):
    branch = "main"

    def test_rules(self):
        self.check([
            (bash("git push"), "deny"),
            (bash("git push origin HEAD"), "deny"),
            (bash("git commit -m 'x'"), "deny"),
            (bash("git add . && git commit -m 'x'"), "deny"),
            (bash("git merge repo/feature"), "deny"),
            (bash("git cherry-pick abc123"), "deny"),
            (bash("git pull"), None),
            (bash("git switch -c repo/new"), None),
            (bash("git push -u origin repo/new"), None),
        ])


class GitHub(Base):
    def test_rules(self):
        self.check([
            (bash("gh pr create --fill"), None),
            (bash("gh pr view 5"), None),
            (bash("gh pr merge 5 --squash"), "ask"),
            (bash("gh pr merge 5 --admin --squash"), "deny"),
            (bash("gh repo edit --visibility private"), "ask"),
            (bash("gh api repos/o/r/rulesets"), None),
            (bash("gh api -X PUT repos/o/r/rulesets/1 --input r.json"), "ask"),
            (bash("gh api repos/o/r/rulesets -f name=x"), "ask"),
        ])


class Salesforce(Base):
    def test_rules(self):
        self.check([
            (bash("sf data query -q 'SELECT Id FROM Lead' --target-org prod"), None),
            (bash("sf project deploy start -x m.xml --target-org homesi-staging"), None),
            (bash("sf project deploy validate -x m.xml --target-org prod"), None),
            (bash("sf project deploy start -x m.xml --dry-run --target-org prod"), None),
            (bash("sf project deploy start -x m.xml"), "ask"),
            (bash("sf project deploy start -x m.xml --target-org prod"), "ask"),
            (bash("sf data update record -s Lead -i 00Q -v 'A=1' -o prod"), "ask"),
            (bash("sf project deploy start -o m.rodriguez@supremelending.com"), "ask"),
            (bash("cd salesforce && sf apex run -f x.apex --target-org prod"), "ask"),
        ])

    def test_prod_deploy_from_unmerged_code(self):
        self.sf_problem = "HEAD is not origin/main"
        self.check([
            (bash("sf project deploy start -x m.xml --target-org prod"), "deny"),
            (bash("sf project deploy quick --job-id 0Af --target-org prod"), "deny"),
            (bash("sf project deploy start -x m.xml --target-org homesi-staging"), None),
            (bash("sf data update record -s Lead -i 00Q -v 'A=1' -o prod"), "ask"),
        ])


class KillSwitches(Base):
    def test_rules(self):
        self.check([
            (bash("sf data update record -s Notification_Settings__c "
                  "-v 'Test_Mode__c=false' -o homesi-staging"), "ask"),
            (mcp("mcp__claude_ai_n8n__update_data_table_row", table="fur_settings"), "ask"),
            (mcp("mcp__claude_ai_n8n__get_workflow", id="fur_settings"), None),
        ])


class AwsAndLambda(Base):
    def test_rules(self):
        self.check([
            (bash("serverless deploy --stage prod"), "deny"),
            (bash("npx sls deploy"), "deny"),
            (bash("sam deploy --guided"), "deny"),
            (bash("cdk deploy"), "deny"),
            (bash("aws lambda update-function-code --function-name processFile --zip-file x"),
             "deny"),
            (bash("aws cloudformation deploy --template-file t.yml"), "deny"),
            (bash("aws lambda list-functions"), None),
            (bash("aws lambda get-function --function-name processFile"), None),
            (bash("aws logs tail /aws/lambda/processFile"), None),
            (bash("aws secretsmanager describe-secret --secret-id x"), None),
            (bash("aws secretsmanager get-secret-value --secret-id x"), "ask"),
            (bash("aws lambda invoke --function-name processFile out.json"), "ask"),
            (bash("aws s3 rm s3://bucket/key"), "ask"),
            (bash("aws s3 ls s3://bucket"), None),
            (bash("aws events delete-rule --name r"), "ask"),
            (bash("env AWS_PROFILE=x npx serverless deploy"), "deny"),
            (bash("C:/tools/sam.exe deploy"), "deny"),
        ])

    def test_mentions_are_not_commands(self):
        self.check([
            (bash('grep -rn "serverless deploy" docs'), None),
            (bash("echo 'never run sam deploy' > note.txt"), None),
            (bash("cat > f.json <<'EOF'\n\"Bash(serverless deploy*)\",\nEOF"), None),
            (bash('grep "sf data update" -r salesforce'), None),
            (bash('echo "git push origin main"'), None),
            (bash("npm run deploy"), None),
        ])


class Mcp(Base):
    def test_rules(self):
        self.check([
            (mcp("mcp__claude_ai_Salesforce_-_sObject_prod__updateSobjectRecord"), "ask"),
            (mcp("mcp__claude_ai_Salesforce_-_sObject_prod__soqlQuery"), None),
            (mcp("mcp__claude_ai_Salesforce_-_sObject_sandbox__updateSobjectRecord"), None),
            (mcp("mcp__salesforce-prod__deploy_metadata"), "ask"),
            (mcp("mcp__salesforce-staging__deploy_metadata"), None),
            (mcp("mcp__Salesforce_Metadata_prod___deploy"), "ask"),
            (mcp("mcp__claude_ai_Customer_io__update_campaign"), "ask"),
            (mcp("mcp__claude_ai_n8n__publish_workflow"), "ask"),
            (mcp("mcp__claude_ai_n8n__search_workflows"), None),
            (mcp("mcp__claude_ai_Make__run_scenario"), "ask"),
            (mcp("mcp__claude_ai_Google_Cloud_BigQuery__execute_sql"), "ask"),
        ])


class Plumbing(unittest.TestCase):
    """End-to-end through the real script: stdin/stdout contract and fail-closed."""

    def run_guard(self, stdin_bytes):
        out = subprocess.run([sys.executable, os.path.join(HERE, "guard.py")],
                             input=stdin_bytes, capture_output=True)
        return out.returncode, out.stdout.decode()

    def test_deny_output_shape(self):
        code, out = self.run_guard(json.dumps(bash("serverless deploy")).encode())
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_silent_when_harmless(self):
        self.assertEqual(self.run_guard(json.dumps(bash("ls")).encode()), (0, ""))

    def test_non_ascii_input(self):
        data = bash("echo 'préstamo ñ' && serverless deploy")
        code, out = self.run_guard(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_fails_closed_on_garbage(self):
        code, out = self.run_guard(b"{not json")
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")


if __name__ == "__main__":
    unittest.main(verbosity=1)
