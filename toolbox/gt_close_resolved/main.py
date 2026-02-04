import argparse
import json
import re
import subprocess
import sys


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running: {' '.join(cmd)}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def get_open_issues() -> list[dict]:
    output = run(["gh", "issue", "list", "--state", "open", "--json", "number,title", "--limit", "1000"])
    return json.loads(output)


def get_commit_messages_last_month() -> str:
    return run(["git", "log", "master", "--since=1 month ago", "--format=%H %s%n%b"])


def find_fixing_commit(issue_number: int, log_output: str) -> str | None:
    for line in log_output.splitlines():
        if f"Fixes #{issue_number}" in line:
            # Extract the commit hash if this is a subject line (starts with hash)
            parts = line.split(" ", 1)
            if len(parts[0]) == 40:
                return parts[0]
            return ""
    return None


def get_pr_url_for_commit(commit_hash: str) -> str | None:
    if not commit_hash:
        return None
    output = run(["gh", "api", f"/search/issues?q=sha:{commit_hash}+type:pr", "--jq", ".items[0].html_url"])
    return output if output and output != "null" else None


def close_issue(issue_number: int):
    run(["gh", "issue", "close", str(issue_number), "--reason", "completed"])


def main():
    parser = argparse.ArgumentParser(
        description="Close GitHub issues that have been resolved by commits on master"
    )
    parser.add_argument("--dry", action="store_true", help="Print what would be closed without closing")
    args = parser.parse_args()

    issues = get_open_issues()
    if not issues:
        print("No open issues found.")
        return

    log_output = get_commit_messages_last_month()

    found_any = False
    for issue in issues:
        number = issue["number"]
        title = issue["title"]
        commit_hash = find_fixing_commit(number, log_output)
        if commit_hash is None:
            continue

        found_any = True
        pr_url = get_pr_url_for_commit(commit_hash)
        pr_info = f" (PR: {pr_url})" if pr_url else ""

        if args.dry:
            print(f"Would close #{number}: {title}{pr_info}")
        else:
            print(f"Closing #{number}: {title}{pr_info}")
            close_issue(number)

    if not found_any:
        print("No resolved issues found in recent commits.")


if __name__ == "__main__":
    main()
