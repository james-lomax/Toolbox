import argparse
import difflib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, Template


def find_file(filename: str, search_root: Optional[Path] = None) -> Path:
    """
    Find a file unambiguously in the repository.

    Args:
        filename: The filename to search for
        search_root: Root directory to search from (defaults to git root or cwd)

    Returns:
        Path to the file

    Raises:
        FileNotFoundError: If file is not found
        ValueError: If multiple files with the same name are found
    """
    if search_root is None:
        # Try to find git root
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            )
            search_root = Path(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            search_root = Path.cwd()

    # Search for the file
    matches = list(search_root.rglob(filename))

    if not matches:
        raise FileNotFoundError(f"File '{filename}' not found in {search_root}")

    if len(matches) > 1:
        paths_str = "\n  ".join(str(p) for p in matches)
        raise ValueError(
            f"Ambiguous reference: multiple files named '{filename}' found:\n  {paths_str}"
        )

    return matches[0]


def reference(filename: str) -> str:
    """
    Jinja2 function to resolve a file reference to an @path string.

    Args:
        filename: The filename to reference

    Returns:
        A string like "@path/to/file.ext"
    """
    file_path = find_file(filename)
    return f"@{file_path}"


def include(filename: str) -> str:
    """
    Jinja2 function to include file contents verbatim.

    Args:
        filename: The filename to include

    Returns:
        The contents of the file
    """
    file_path = find_file(filename)
    return file_path.read_text(encoding="utf-8")


def template_function(filename: str, **kwargs: Any) -> str:
    """
    Jinja2 function to render another template with arguments.

    Args:
        filename: The template filename to render
        **kwargs: Arguments to pass to the template

    Returns:
        The rendered template
    """
    file_path = find_file(filename)
    template_content = file_path.read_text(encoding="utf-8")

    # Create a new template with the same environment
    env = Environment(loader=FileSystemLoader(file_path.parent))
    env.globals["reference"] = reference
    env.globals["include"] = include
    env.globals["template"] = template_function

    tmpl = env.from_string(template_content)
    return tmpl.render(**kwargs)


def get_git_file_content(file_path: Path, commit: str = "HEAD") -> Optional[str]:
    """
    Get the content of a file from a specific git commit.

    Args:
        file_path: Path to the file
        commit: Git commit reference (default: "HEAD")

    Returns:
        The file content as a string, or None if the file doesn't exist in that commit
    """
    try:
        # Get git root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_root = Path(result.stdout.strip())

        # Get relative path from git root
        rel_path = file_path.resolve().relative_to(git_root)

        # Get file content from git
        result = subprocess.run(
            ["git", "show", f"{commit}:{rel_path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, ValueError):
        return None


def reference_git(filename: str, commit: str = "HEAD") -> str:
    """
    Jinja2 function to resolve a file reference from a specific git commit.

    Args:
        filename: The filename to reference
        commit: Git commit reference

    Returns:
        A string like "@path/to/file.ext"
    """
    file_path = find_file(filename)
    return f"@{file_path}"


def include_git(filename: str, commit: str = "HEAD") -> str:
    """
    Jinja2 function to include file contents from a specific git commit.

    Args:
        filename: The filename to include
        commit: Git commit reference

    Returns:
        The contents of the file from the specified commit
    """
    file_path = find_file(filename)
    content = get_git_file_content(file_path, commit)
    if content is None:
        # If file doesn't exist in git, return empty string
        return ""
    return content


def template_function_git(filename: str, commit: str = "HEAD", **kwargs: Any) -> str:
    """
    Jinja2 function to render another template from a specific git commit.

    Args:
        filename: The template filename to render
        commit: Git commit reference
        **kwargs: Arguments to pass to the template

    Returns:
        The rendered template from the specified commit
    """
    file_path = find_file(filename)
    template_content = get_git_file_content(file_path, commit)
    if template_content is None:
        # If file doesn't exist in git, return empty string
        return ""

    # Create a new template with custom functions that use the same commit
    env = Environment(autoescape=False)
    env.globals["reference"] = lambda fn: reference_git(fn, commit)
    env.globals["include"] = lambda fn: include_git(fn, commit)
    env.globals["template"] = lambda fn, **kw: template_function_git(fn, commit, **kw)

    tmpl = env.from_string(template_content)
    return tmpl.render(**kwargs)


def compile_template(template_path: Path, use_git_commit: Optional[str] = None, template_kwargs: Optional[dict[str, str]] = None) -> str:
    """
    Compile a Jinja2 template file.

    Args:
        template_path: Path to the template file
        use_git_commit: If provided, compile the template using file contents from this git commit

    Returns:
        The rendered template as a string
    """
    if use_git_commit:
        # Get template content from git
        template_content = get_git_file_content(template_path, use_git_commit)
        if template_content is None:
            raise FileNotFoundError(f"Template file not found in commit {use_git_commit}: {template_path}")

        # Set up Jinja2 environment with git-aware functions
        env = Environment(autoescape=False)
        env.globals["reference"] = lambda fn: reference_git(fn, use_git_commit)
        env.globals["include"] = lambda fn: include_git(fn, use_git_commit)
        env.globals["template"] = lambda fn, **kw: template_function_git(fn, use_git_commit, **kw)

        tmpl = env.from_string(template_content)
        return tmpl.render(**(template_kwargs or {}))
    else:
        # Use current working copy
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        # Set up Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(template_path.parent),
            autoescape=False,  # We're templating markdown, not HTML
        )

        # Add custom functions to the template environment
        env.globals["reference"] = reference
        env.globals["include"] = include
        env.globals["template"] = template_function

        # Load and render the template
        template = env.get_template(template_path.name)
        return template.render(**(template_kwargs or {}))


def create_unified_diff(old_text: str, new_text: str, filename: str = "prompt") -> str:
    """
    Create a unified diff between two text strings.

    Args:
        old_text: The old version of the text
        new_text: The new version of the text
        filename: Name to use in the diff header

    Returns:
        A unified diff string, or empty string if there are no differences
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{filename} (last commit)",
            tofile=f"{filename} (working copy)",
            lineterm="",
        )
    )

    if not diff_lines:
        return ""

    return "".join(diff_lines)


def find_template_file(template_spec: str) -> Path:
    """
    Find a template file, checking current directory first, then searching subdirectories.

    Args:
        template_spec: The template filename or partial path to search for

    Returns:
        Path to the template file

    Raises:
        FileNotFoundError: If template file is not found
        ValueError: If multiple templates match the specification
    """
    search_root = Path.cwd()
    template_spec_path = Path(template_spec)

    # First check if the exact path exists (relative to cwd)
    candidate = search_root / template_spec
    if candidate.exists() and candidate.is_file():
        return candidate.resolve()

    # Search for files matching the template name
    filename = template_spec_path.name
    matches = list(search_root.rglob(filename))

    if not matches:
        raise FileNotFoundError(f"Template file '{template_spec}' not found in {search_root} or its subdirectories")

    # If template_spec includes path components, filter by partial path matching
    if len(template_spec_path.parts) > 1:
        # Filter matches that end with the specified path
        filtered_matches = []
        for match in matches:
            # Check if the match's relative path ends with the template_spec path
            try:
                rel_path = match.relative_to(search_root)
                # Check if the end of rel_path matches template_spec_path
                if len(rel_path.parts) >= len(template_spec_path.parts):
                    if rel_path.parts[-len(template_spec_path.parts):] == template_spec_path.parts:
                        filtered_matches.append(match)
            except ValueError:
                continue

        matches = filtered_matches

        if not matches:
            raise FileNotFoundError(f"Template file matching '{template_spec}' not found")

    if len(matches) > 1:
        paths_str = "\n  ".join(str(p.relative_to(search_root)) for p in matches)
        raise ValueError(
            f"Ambiguous template reference: multiple files match '{template_spec}':\n  {paths_str}\n"
            f"Please specify more of the path to disambiguate (e.g., 'subdir/{filename}')"
        )

    return matches[0].resolve()


def main():
    """Main entry point for the claude-template tool."""
    parser = argparse.ArgumentParser(
        description="Build prompts using Jinja2 templating and start Claude Code"
    )
    parser.add_argument(
        "template_file",
        help="Path to the template file to compile (filename or partial path)",
    )
    parser.add_argument(
        "additional_instructions",
        nargs="?",
        default=None,
        help="Optional additional instructions to append to the compiled template",
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="Print the compiled template without executing Claude Code",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Include a diff of changes since the last commit",
    )
    parser.add_argument(
        "-D",
        action="append",
        dest="template_args",
        default=[],
        metavar="KEY=VALUE",
        help="Pass arguments to the template (e.g. -D name=value)",
    )

    args = parser.parse_args()

    # Parse template arguments
    template_kwargs: dict[str, str] = {}
    for arg in args.template_args:
        if "=" not in arg:
            print(f"Error: Template argument must be in KEY=VALUE format, got: {arg}", file=sys.stderr)
            sys.exit(1)
        key, value = arg.split("=", 1)
        template_kwargs[key] = value

    try:
        template_path = find_template_file(args.template_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Compile the template from working copy
        compiled_working = compile_template(template_path, template_kwargs=template_kwargs)

        if args.changed:
            # Also compile from last commit
            try:
                compiled_last_commit = compile_template(template_path, use_git_commit="HEAD", template_kwargs=template_kwargs)

                # Create diff if there are changes
                diff = create_unified_diff(compiled_last_commit, compiled_working, "prompt")

                if diff:
                    # Build the final prompt with diff
                    compiled = f"{compiled_working}\n\nWe've run this prompt before, but I've made some changes, here is the diff from the last time we ran:\n\n```diff\n{diff}\n```"
                else:
                    # No changes, just use the working copy
                    compiled = compiled_working
            except (FileNotFoundError, subprocess.CalledProcessError):
                # If we can't get the last commit version, just use working copy
                print("Warning: Could not retrieve last commit version, using working copy only", file=sys.stderr)
                compiled = compiled_working
        else:
            compiled = compiled_working

        # Append additional instructions if provided
        if args.additional_instructions:
            # Additional instructions always go at the end
            compiled = f"{compiled}\n\nAdditionally:\n\n{args.additional_instructions}"

        if args.dry:
            # Just print the compiled template
            print(compiled)
            return

        # Execute claude with the compiled template
        # Use exec mode so that the claude process replaces this process
        # This allows proper signal handling (ctrl+c won't kill the parent)
        os.execvp("claude", ["claude", compiled])

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
