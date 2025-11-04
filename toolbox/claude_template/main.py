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


def main():
    """Main entry point for the claude-template tool."""
    parser = argparse.ArgumentParser(
        description="Build prompts using Jinja2 templating and start Claude Code"
    )
    parser.add_argument(
        "template_file",
        help="Path to the template file to compile",
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="Print the compiled template without executing Claude Code",
    )

    args = parser.parse_args()

    template_path = Path(args.template_file).expanduser().resolve()

    try:
        # Compile the template
        compiled = compile_template(template_path)

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
