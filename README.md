# Toolbox

Miscellaneous tools I use day to day.

## Installation

For general use you can do `uv tool install .`

For development use, or to automatically update when you `git pull`, use `./reinstall.sh` which installs the tool as an editable package. You only then need to re-run `reinstall.sh` if tools are added.

## Creating a tool

Once this tool is installed, you can create new tools easily by defining them in markdown in .prompts/ - see example-tool.md to see how to do this.

Create your tool description and run:

```sh
claude-template my-tool.md
```

This will instruct Claude to build/update your tool.

## claude-template

`claude-template` is a simple tool which constructs a prompt template from markdown files. See `claude-template.md` to see how this works and how to use it.

This tool solves a common problem with using AI coders: as context size increases, the quality of results decreases, so we typically spend a lot of time constructing prompts which specify the precise context that is required to complete a task. Templating your prompt allows you to specify how we construct this context in a reusable way.

Define a markdown file with your prompt and run `claude-template my-prompt.md` to create a prompt and start Claude Code with it.

You can also use `--dry` to simply print the prompt and stop. And you can also supply a second argument string with more instructions to append to the prompt, e.g.:

```sh
claude-template my-prompt.md "Update this feature"
```

The input prompt file is considered as a jinja2 template with some special functions:

**reference(filename: str)**

```
{{reference("file-name")}}
```

This inserts an absolute path file reference from the file-name.

The template tool attempts to unambiguously resolve this reference using the path you've provided. This path need only contain the minimum information to unambiguously resolve the file, so generally you can supply just the filename. If the reference cannot be unambiguously resolved, and error is raised.

**template(filename: str, **kwargs)**

```
{{template("my-other-prompt.md", argument="value"}}
```

Renders another file as a jinja2 template. Any key-word arguments passed to template will be defined as top-level properties which can be used in the rendering of this referenced template.

The file is resolved unambiguously in the same way as for the `reference()` function.

**include(filename: str)**

```
{{include("file-name")}}
```

Include another prompt file _verbatim_ -- this file will not be rendered with Jinja2. Useful for including code directly in the prompt.

The file is resolved unambiguously in the same way as for the `reference()` function.

## cm-adb

```
cm-adb clear-booking
```

Removes any saved booking data from the app on a device connected over adb.

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

