{{template("new-tool.md", tool_name="gt-close-resolved")}}

This tool automatically closes resolved issues in github by reading the commit log on master.

This solves an issue in which PRs that we create with Graphite do not register as properly "merged", so do not auto close issues on github.

Assume the tool is run from the repository of interest.

The tool will read the list of open issues on Github, then it will search the commits on master from the last month for text `Fixes #<issue number>`. If you find exactly that text in the message for a commit, you can close the issue.

A dry run mode exists in which you run `gt-close-resolved --dry` and it simply prints the issues we're resolving (along with the title of each issue and the PR link that resolves it) without closing it. When `--dry` isn't specified, the same messages are printed but each issue is closed as completed.
