{{template("new-tool.md", tool_name="git-mux")}}

Usage

```
git-mux branch1 colleague/branch2 branch3 etc
```

Fetches the latest branch pointers for each of these branches, creates a temporary head (no branch) with all the commits from all those branches off main so I can test them all in one go.

Fail fast on merge conflicts
