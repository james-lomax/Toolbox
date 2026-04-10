import os
import sys
from pathlib import Path


def find_git_repos() -> list[Path]:
    """Find all immediate subdirectories that are git repositories."""
    cwd = Path.cwd()
    repos = []
    for child in sorted(cwd.iterdir()):
        if child.is_dir() and (child / ".git").exists():
            repos.append(child)
    return repos


def prompt_select_repo(repos: list[Path], prompt_msg: str, exclude: Path | None = None) -> Path:
    """Prompt the user to select a repository from a list."""
    available = [r for r in repos if r != exclude]
    if not available:
        print("Error: No repositories available to select.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{prompt_msg}")
    for i, repo in enumerate(available, 1):
        print(f"  {i}) {repo.name}")

    while True:
        try:
            choice = input("\nSelect number: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                return available[idx]
        except (ValueError, EOFError):
            pass
        print("Invalid selection, try again.")


def prompt_refs(repo_name: str) -> str:
    """Prompt user to paste PR URLs and/or commit SHAs for a repo."""
    print(f"\nPaste the relevant PR URLs and/or commit SHAs for {repo_name}.")
    print("(Enter a blank line when done)")
    lines = []
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        lines.append(line)

    if not lines:
        print("Error: You must provide at least one PR or commit.", file=sys.stderr)
        sys.exit(1)

    return "\n".join(lines)


def build_prompt(
    repo1: Path,
    refs1: str,
    repo2: Path,
    refs2: str,
) -> str:
    repo1_abs = repo1.resolve()
    repo2_abs = repo2.resolve()

    return f"""\
You are reviewing changes made across two platforms to check for parity issues.

Two repositories have had related changes made. Your job is to review all the commits
and PR diffs from each repository and identify any issues where the implementations
are not in parity — missing features, behavioral differences, inconsistencies, or
anything that looks like it was implemented on one platform but not the other.

## Repository 1: {repo1.name}
Path: {repo1_abs}

References (PR URLs and/or commit SHAs):
{refs1}

## Repository 2: {repo2.name}
Path: {repo2_abs}

References (PR URLs and/or commit SHAs):
{refs2}

## Instructions

1. For each reference above, use `git` and/or `gh` commands to review the changes:
   - For commit SHAs: run `git -C <repo_path> show <sha>` to see the diff
   - For PR URLs: use `gh pr view <url>` and `gh pr diff <url>` to review the PR
   - Note: the changes may span multiple PRs/commits on each platform, and they may
     not cleanly rebase together — review each independently.

2. After reviewing all changes from both repositories, produce a parity report:
   - List features/changes found in repo 1 that are missing or different in repo 2
   - List features/changes found in repo 2 that are missing or different in repo 1
   - Flag any behavioral differences, naming inconsistencies, or logic discrepancies
   - Note any areas where the implementations diverge in approach and whether that
     divergence is likely to cause issues

3. If everything looks good, say so — don't invent problems.

Start by reviewing all the references now."""


def main():
    repos = find_git_repos()
    if len(repos) < 2:
        print("Error: Need at least 2 git repositories in the current directory.", file=sys.stderr)
        sys.exit(1)

    repo1 = prompt_select_repo(repos, "Select the first repository:")
    refs1 = prompt_refs(repo1.name)

    repo2 = prompt_select_repo(repos, "Select the second repository:", exclude=repo1)
    refs2 = prompt_refs(repo2.name)

    prompt = build_prompt(repo1, refs1, repo2, refs2)

    print("\nLaunching Claude...")
    os.execvp("claude", ["claude", prompt])


if __name__ == "__main__":
    main()
