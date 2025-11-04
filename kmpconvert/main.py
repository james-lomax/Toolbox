import argparse
import re
from pathlib import Path
from typing import List, Tuple


RE_IMPORT_JSON = re.compile(r"^\s*import\s+com\.squareup\.moshi\.Json\s*$")
RE_IMPORT_JSONCLASS = re.compile(r"^\s*import\s+com\.squareup\.moshi\.JsonClass\s*$")
RE_ANNOTATION_JSONCLASS = re.compile(r"^(\s*)@JsonClass\([^)]*\)\s*$")
RE_ANNOTATION_JSON = re.compile(r"^\s*@Json(?:\([^)]*\))?\s*$")
RE_ANNOTATION_JSON_WITH_NAME = re.compile(
    r"^(\s*)@Json\(\s*name\s*=\s*['\"]([^'\"]+)['\"]\s*\)\s*$"
)
RE_VAL_DECL = re.compile(r"^(\s*)val\s+([A-Za-z_][A-Za-z0-9_]*)\s*:")


def camel_to_snake(name: str) -> str:
    # Insert underscore between lower/digit and upper
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    # Handle acronym followed by normal word, e.g., URLId -> URL_Id
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s1)
    return s2.lower()


def _process_lines(
    lines: List[str], fix_names: bool, fix_all_names: bool
) -> Tuple[List[str], dict, List[str]]:
    changed = False
    stats = {
        "annotations_json_removed": 0,
        "annotations_jsonclass_replaced": 0,
        "imports_moshi_removed": 0,
        "import_serializable_added": False,
    }
    errors: List[str] = []

    # First pass: transform annotations with validation for @Json(name = ...)
    transformed: List[str] = []
    inserted_serializable = False
    inserted_serialname = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m_jsonclass = RE_ANNOTATION_JSONCLASS.match(line)
        if m_jsonclass:
            indent = m_jsonclass.group(1)
            transformed.append(f"{indent}@Serializable\n")
            stats["annotations_jsonclass_replaced"] += 1
            inserted_serializable = True
            if line != transformed[-1]:
                changed = True
            i += 1
            continue

        m_json_with_name = RE_ANNOTATION_JSON_WITH_NAME.match(line)
        if m_json_with_name:
            indent = m_json_with_name.group(1)
            json_name = m_json_with_name.group(2)
            if fix_all_names:
                # Always replace with @SerialName preserving indentation
                transformed.append(f"{indent}@SerialName(\"{json_name}\")\n")
                inserted_serialname = True
                stats["annotations_json_removed"] += 1
                changed = True
                i += 1
                continue
            # Validate against the next line (expected: val fieldName: ...)
            if i + 1 >= n:
                errors.append(
                    "Encountered @Json(name=...) without following field declaration"
                )
                # Keep processing remaining lines
                i += 1
                continue
            next_line = lines[i + 1]
            m_val = RE_VAL_DECL.match(next_line)
            if not m_val:
                errors.append(
                    "Expected a Kotlin 'val' declaration after @Json(name=...), got: "
                    + next_line.strip()
                )
                i += 1
                continue
            field_name = m_val.group(2)
            expected_snake = camel_to_snake(field_name)
            if expected_snake != json_name:
                if fix_names:
                    # Replace with @SerialName("...") preserving indentation
                    transformed.append(f"{indent}@SerialName(\"{json_name}\")\n")
                    inserted_serialname = True
                    changed = True
                    i += 1
                    continue
                else:
                    errors.append(
                        f"Field '{field_name}' serializes to '{expected_snake}', but @Json name is '{json_name}'"
                    )
            # If names match (or we recorded an error and will skip writing), drop the @Json line
            stats["annotations_json_removed"] += 1
            changed = True
            i += 1
            continue

        if RE_ANNOTATION_JSON.match(line):
            # Drop other full-line @Json annotations entirely
            stats["annotations_json_removed"] += 1
            changed = True
            i += 1
            continue

        transformed.append(line)
        i += 1

    # Second pass: imports handling (remove moshi, add kotlinx.serialization.Serializable if needed)
    has_serializable_import = any(
        l.strip() == "import kotlinx.serialization.Serializable" for l in transformed
    )
    has_serialname_import = any(
        l.strip() == "import kotlinx.serialization.SerialName" for l in transformed
    )

    result_lines: List[str] = []
    package_index = None
    import_indices: List[int] = []

    for idx, line in enumerate(transformed):
        if package_index is None and line.startswith("package "):
            package_index = idx

        if line.strip().startswith("import "):
            import_indices.append(idx)

    # Filter out moshi imports
    for line in transformed:
        if RE_IMPORT_JSON.match(line) or RE_IMPORT_JSONCLASS.match(line):
            stats["imports_moshi_removed"] += 1
            changed = True
            continue
        result_lines.append(line)

    # Decide whether to add Serializable import
    needs_serializable_import = inserted_serializable or any(
        l.strip().startswith("@Serializable") for l in result_lines
    )
    needs_serialname_import = inserted_serialname or any(
        l.strip().startswith("@SerialName(") for l in result_lines
    )

    # Find insertion anchor for imports
    last_import_idx = None
    for idx, line in enumerate(result_lines):
        if line.strip().startswith("import "):
            last_import_idx = idx

    def insert_import(import_line: str):
        nonlocal last_import_idx
        if last_import_idx is not None:
            result_lines.insert(last_import_idx + 1, import_line)
            last_import_idx += 1
        elif package_index is not None:
            insert_at = package_index + 1
            if insert_at < len(result_lines) and result_lines[insert_at].strip() == "":
                insert_at += 1
            result_lines.insert(insert_at, import_line)
            last_import_idx = insert_at
        else:
            result_lines.insert(0, import_line)
            last_import_idx = 0

    if needs_serializable_import and not has_serializable_import:
        insert_import("import kotlinx.serialization.Serializable\n")
        stats["import_serializable_added"] = True
        changed = True

    if needs_serialname_import and not has_serialname_import:
        insert_import("import kotlinx.serialization.SerialName\n")
        stats["import_serialname_added"] = True
        changed = True

    return (result_lines, {"changed": changed, **stats}, errors)


def process_file(
    path: Path, write: bool, fix_names: bool, fix_all_names: bool
) -> Tuple[dict, List[str]]:
    text = path.read_text(encoding="utf-8")
    orig_lines = text.splitlines(keepends=True)
    new_lines, meta, errors = _process_lines(orig_lines, fix_names, fix_all_names)

    if (not errors) and meta["changed"] and write:
        path.write_text("".join(new_lines), encoding="utf-8")

    return (
        {
            "path": str(path),
            **meta,
        },
        errors,
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert Kotlin models from Moshi annotations to kotlinx.serialization. "
            "Replaces @JsonClass(...) with @Serializable, removes @Json(...) annotations, "
            "and updates imports."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root directory to scan recursively (default: current directory)",
    )
    parser.add_argument(
        "--ext",
        default=".kt",
        help="File extension to include (default: .kt)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--fix-names",
        action="store_true",
        help=(
            "Replace mismatched @Json(name=...) with @SerialName(...) and add its import instead of erroring"
        ),
    )
    group.add_argument(
        "--fix-all-names",
        action="store_true",
        help=(
            "Replace all @Json(name=...) annotations with @SerialName(...) and add its import"
        ),
    )
    # No verbose output; tool remains silent on success

    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        raise SystemExit(f"Path does not exist: {root}")

    files: List[Path] = [p for p in root.rglob(f"*{args.ext}") if p.is_file()]

    any_errors = False
    for f in files:
        meta, errors = process_file(
            f,
            write=not args.dry_run,
            fix_names=args.fix_names,
            fix_all_names=args.fix_all_names,
        )
        if errors:
            any_errors = True
            print(str(f))
            for e in errors:
                print(f"- {e}")
    if any_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
