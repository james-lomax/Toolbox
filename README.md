## kmpconversion

Convert Kotlin Moshi models to kotlinx.serialization.

### What it does
- Replaces `@JsonClass(...)` with `@Serializable`
- Removes field-level `@Json(...)` annotations
- Removes `import com.squareup.moshi.Json` and `import com.squareup.moshi.JsonClass`
- Adds `import kotlinx.serialization.Serializable` when needed

### Install (uv)

From the project root:

```bash
uv tool install --editable .
```

This installs the `kmpconvert` command globally (via uv's tool shim).

### Usage

```bash
# Dry run (no files written)
kmpconvert /path/to/kotlin/project --dry-run -v

# Apply changes
kmpconvert /path/to/kotlin/project -v

# Options
kmpconvert --help
```

Notes:
- Only exact, full-line annotation matches are modified (e.g., `@Json(name = "foo")`).
- The tool does not add `@SerialName` fields; it assumes your runtime config handles naming.

