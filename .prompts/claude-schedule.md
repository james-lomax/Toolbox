{{template("new-tool.md", tool_name="claude-schedule")}}

`claude-schedule` allows you to schedule running claude in a worktree.

## Usage

```sh
claude-schedule 3am "My prompt"
```

Immediately creates a worktree from the repo of the CWD on a new branch off the current branch in the CWD.

Ensures the daemon is started and schedules the prompt for execution on the worktree at 3am

`--dry` runs the command in dry mode, having no side effects but the same output.

## Execution of the claude prompt

Then, at the scheduled time the daemon will run the claude prompt in the worktree with the following arguments:

```python
cmd = [
    "claude",
    "--model", "opus",
    "-p",
    "--verbose"
    "--permission-mode", "bypassPermissions",
    prompt,
]
```

The stdout and stderr of the execution of this will be recorded and saved in `~/.toolbox/claude-schedule/<time>.log`

## Service

claude schedule runs a daemon service that out-lives the CLI command.

```sh
# Start with this (automatically start if not already running)
claude-schedule daemon start

# Restart with
claude-schedule daemon restart

# Check it's running
claude-schedule daemon status

# Stop with
claude schedule-daemon stop
```

The daemon does not need to survive restarts. Keep it simple.
