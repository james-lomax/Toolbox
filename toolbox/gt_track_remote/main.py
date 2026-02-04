import argparse
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


def main():
    parser = argparse.ArgumentParser(
        description="Pull a remote branch, track it with graphite, and add it to the current stack"
    )
    parser.add_argument("branch_name", help="Name of the remote branch to track")
    args = parser.parse_args()

    branch_name = args.branch_name

    # 1. Get current branch name
    user_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    print(f"Current branch: {user_branch}")

    # 2. Checkout the remote branch
    print(f"Checking out origin/{branch_name} as {branch_name}")
    run(["git", "checkout", f"origin/{branch_name}", "-b", branch_name])

    # 3. Track with graphite
    print("Tracking branch with graphite")
    run(["gt", "track"])

    # 4. Restack onto user_branch
    print(f"Moving onto {user_branch}")
    run(["gt", "move", "-o", user_branch])

    print("Done")


if __name__ == "__main__":
    main()
