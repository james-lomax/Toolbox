{{template("new-tool.md", tool_name="claude-crosscheck")}}

Helps a user launch a claude session to cross check PRs across two platforms.

Takes the user through a CLI wizard:

- First you select the first repository
- And then are prompted to paste all of the relevant PRs and commits
- Then prompts for second repository
- And prompted to paste the relevant PRs and commits for the second one

Then the program prepares prompt prompt telling claude to read all of the PRs and commits from each platform on their respective repositories and review the change set to find issues of non-parity.

Launching claude can work similar to how it does for claude-template, where the user is launched into a claude session with the prompt and it takes over the tty so the user can continue asking questions.

Claude must be instruction to use git and/or gh commands to review the commits made for each platform. But consider they may be made in separate PRs and therefore might not cleanly rebase together.

The command will be run in a directory which will have a set of sub-directories, some of which will be git repositories. Detect all the git repository directories and present them each as options, excluding the first option when prompting for the second option.
