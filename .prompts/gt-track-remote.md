{{template("new-tool.md", tool_name="gt-track-remote")}}

This tool automates the process of pulling a remote branch, tracking it with graphite and then adding it to the current stack.

Usage:

```
gt-track-remote <branch-name>
```

Steps:

1. Use git to get the current branch name and store this as user_branch
2. Checkout the remote branch with `git checkout origin/<branch-name> -b <branch-name>`
3. Track the branch `gt track`
4. Restack onto the user_branch: `gt move -o <user_branch>`
