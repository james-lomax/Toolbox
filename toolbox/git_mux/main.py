import argparse
import os
import shutil
import subprocess
import sys


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error running: {' '.join(cmd)}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result


def detect_default_branch() -> str:
    """Auto-detect the default branch (main or master)."""
    for candidate in ["main", "master"]:
        for ref in [f"origin/{candidate}", candidate]:
            result = run(["git", "rev-parse", "--verify", ref], check=False)
            if result.returncode == 0:
                return candidate
    print("Error: could not detect default branch (tried main, master)", file=sys.stderr)
    sys.exit(1)


def install_git_tool():
    """Install git-mux as a git subcommand by symlinking into PATH."""
    source = shutil.which("git-mux")
    if source is None:
        print("Error: git-mux is not on PATH. Install the package first.", file=sys.stderr)
        sys.exit(1)

    # Git looks for 'git-mux' on PATH to enable 'git mux', so if git-mux
    # is already on PATH (which it is since we found it), it already works.
    # Verify by running git mux --help
    result = run(["git", "mux", "--help"], check=False)
    if result.returncode == 0:
        print(f"git-mux is already installed at {source}")
        print("You can run: git mux <branches...>")
    else:
        # Shouldn't happen if git-mux is on PATH, but handle it
        git_exec_path = run(["git", "--exec-path"]).stdout.strip()
        link = os.path.join(git_exec_path, "git-mux")
        os.symlink(source, link)
        print(f"Installed: {link} -> {source}")
        print("You can now run: git mux <branches...>")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and merge multiple branches into a temporary detached HEAD for testing"
    )
    parser.add_argument(
        "branches",
        nargs="*",
        help="Branches to merge (e.g. branch1 colleague/branch2)",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Base branch to start from (default: auto-detect main/master)",
    )
    parser.add_argument(
        "--install-git-tool",
        action="store_true",
        help="Install git-mux as a git subcommand (git mux ...)",
    )
    args = parser.parse_args()

    if args.install_git_tool:
        install_git_tool()
        return

    if not args.branches:
        parser.error("at least one branch is required")

    # Fetch latest from remote
    print("Fetching latest from remote...")
    run(["git", "fetch", "--all"])

    # Resolve base branch
    base_name = args.base if args.base else detect_default_branch()
    base_ref = f"origin/{base_name}"
    result = run(["git", "rev-parse", "--verify", base_ref], check=False)
    if result.returncode != 0:
        base_ref = base_name
        run(["git", "rev-parse", "--verify", base_ref])
    print(f"Using base: {base_ref}")

    # Resolve each branch ref before starting merges
    resolved: list[tuple[str, str]] = []
    for branch in args.branches:
        # Try origin/<branch> first, then bare name
        for ref in [f"origin/{branch}", branch]:
            result = run(["git", "rev-parse", "--verify", ref], check=False)
            if result.returncode == 0:
                resolved.append((branch, ref))
                break
        else:
            print(f"Error: could not resolve branch '{branch}'", file=sys.stderr)
            sys.exit(1)

    # Detach HEAD at the base
    run(["git", "checkout", "--detach", base_ref])
    print(f"Detached HEAD at {base_ref}")

    # Merge each branch one by one
    for branch, ref in resolved:
        print(f"Merging {branch} ({ref})...")
        result = run(
            ["git", "merge", "--no-edit", ref],
            check=False,
        )
        if result.returncode != 0:
            print(f"\nMerge conflict while merging '{branch}'.", file=sys.stderr)
            if result.stdout:
                print(result.stdout, file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            # Abort the failed merge and return to previous state
            run(["git", "merge", "--abort"], check=False)
            run(["git", "checkout", "-"], check=False)
            sys.exit(1)

    print(f"\nSuccessfully merged {len(resolved)} branches into detached HEAD.")
    print("You are now on a temporary detached HEAD — no branch was created.")


if __name__ == "__main__":
    main()
