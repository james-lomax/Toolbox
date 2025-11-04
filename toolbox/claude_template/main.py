import argparse
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


def compile_template(template_path: Path) -> str:
    """
    Compile a Jinja2 template file.

    Args:
        template_path: Path to the template file

    Returns:
        The rendered template as a string
    """
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
    return template.render()


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

    args = parser.parse_args()

    try:
        template_path = find_template_file(args.template_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Compile the template
        compiled = compile_template(template_path)

        # Append additional instructions if provided
        if args.additional_instructions:
            compiled = f"{compiled}\n\n{args.additional_instructions}"

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
