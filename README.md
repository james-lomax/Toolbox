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

Usage: `claude-template template-file.md "[optional additional instructions]" [--dry] [--changed] [-D key=value]`

This tool solves a common problem with using AI coders: as context size increases, the quality of results decreases, so we typically spend a lot of time constructing prompts which specify the precise context that is required to complete a task. Templating your prompt allows you to specify how we construct this context in a reusable way.

Define a markdown file with your prompt and run `claude-template my-prompt.md` to create a prompt and start Claude Code with it.

You can also use `--dry` to simply print the prompt and stop. And you can also supply a second argument string with more instructions to append to the prompt, e.g.:

```sh
claude-template my-prompt.md "Update this feature"
```

Additionally, you can use `--changed` when you update the prompt files - this will generate a git diff of the rendered prompt as it appears in the working copy vs how it appeared in the last commit, making it easier to prompt Claude to make updates based on the changes you've made to the prompt.

```sh
claude-template my-prompt.md --changed
```

You can specify environment variables to apply to the top level prompt with e.g.:

```sh
claude-template my-prompt.md -D key=value
```

This will set the `{{key}}` template argument.

### Prompt template files

The input prompt file is considered as a jinja2 template with some special functions:

**reference(filename: str)**

```
{{reference("file-name")}}
```

This inserts an absolute path file reference from the file-name.

The template tool attempts to unambiguously resolve this reference using the path you've provided. This path need only contain the minimum information to unambiguously resolve the file, so generally you can supply just the filename. If the reference cannot be unambiguously resolved, and error is raised.

**template(filename: str, \*\*kwargs)**

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

## geojson-ads-circles

Given a file of POIs like:

```csv
Name,Address,Postcode,lat,lng
Boots,"11-19 Lower Parliament Street, Nottingham",NG1 3QS,52.9555186000,-1.1465924000
Boots,"1 Devonshire Walk, Derby",DE1 2AH,52.9200880000,-1.4733948000
```

You can generate a GeoJSON file of campaign locations with a given radius (in this case 5km) like so:

```sh
geojson-ads-circles campaign.csv campaign 5000 campaign.geojson
```

## aslog

Simplify Android Studio network log files into a readable JSON format. Decodes base64-encoded request/response payloads (including gzip-compressed ones) and extracts key fields.

```sh
aslog network-log.json                    # outputs network-log.simple.json
aslog network-log.json output.json        # explicit output path
aslog network-log.json --via-only         # only include requests to .ridewithvia.com hosts
```

## emoji-detector

Detect and describe emoji image files using Gemini. Scans a directory of `.webp`/`.png` emoji images, sends them to Gemini in batches to identify the Unicode emoji or generate a short description, and produces an HTML report.

Requires a Gemini API key at `~/.gemini_key`.

```sh
emoji-detector /path/to/emoji-images
```

Outputs `emoji-descriptions.json` (cached descriptions) and `emoji-report.html` in the target directory.

## gt-track-remote

Pull a remote branch, track it with [Graphite](https://graphite.dev), and move it onto your current stack.

```sh
gt-track-remote <branch-name>
```

This will:
1. Check out `origin/<branch-name>` as a local branch
2. Track it with `gt track`
3. Move it onto your current branch with `gt move`

## gt-close-resolved

Automatically close GitHub issues that have been resolved by commits on master. Scans the last month of commit messages for `Fixes #N` references and closes matching open issues.

```sh
gt-close-resolved          # close resolved issues
gt-close-resolved --dry    # preview what would be closed
```

## claude-schedule

Schedule Claude Code to run a prompt in a git worktree at a specified time. A daemon process manages the schedule and executes jobs when they're due.

```sh
# Schedule a job
claude-schedule 3am "Review and refactor the auth module"
claude-schedule 4:45pm "Write tests for the new API endpoints"
claude-schedule +30m "Fix the failing CI build"

# Manage the daemon
claude-schedule daemon status
claude-schedule daemon start
claude-schedule daemon stop
claude-schedule daemon restart

# Cancel a pending job
claude-schedule cancel

# Dry run (no side effects)
claude-schedule --dry 3am "some prompt"
```

Supported time formats: `3am`, `4:45pm`, `15:00`, `+5m`, `+2h`.

## git-mux

Fetch and merge multiple branches into a temporary detached HEAD for testing. Useful for verifying that several in-flight branches work together before they're merged.

```sh
git-mux branch1 branch2 colleague/branch3
git-mux --base develop branch1 branch2    # use a specific base branch
```

Can also be used as a git subcommand:

```sh
git-mux --install-git-tool
git mux branch1 branch2
```

If a merge conflict occurs, the merge is aborted and you're returned to your original branch.

## claude-crosscheck

Launch a Claude Code session that cross-checks related changes across two repositories for parity issues. Interactively prompts you to select two repos (from subdirectories of the current directory) and provide PR URLs or commit SHAs for each, then generates a parity report.

```sh
cd ~/workspace    # directory containing multiple git repos
claude-crosscheck
```

## kmpconversion

Convert Kotlin Moshi models to kotlinx.serialization.

### What it does
- Replaces `@JsonClass(...)` with `@Serializable`
- Removes field-level `@Json(...)` annotations
- Removes `import com.squareup.moshi.Json` and `import com.squareup.moshi.JsonClass`
- Adds `import kotlinx.serialization.Serializable` when needed

### Install (uv)

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

