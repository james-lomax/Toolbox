{{template("new-tool.md", tool_name="claude-template")}}

claude-template is a prompt initialising tool which allows you to build prompts using jinja2 templating, so you can construct more complicated prompts and rerun them with ease.

claude-template compiles your templated prompt file and then starts claude code with that file.

To use it, you create a template file like "my-prompt.md" and run:

```sh
claude-template my-prompt.md
```

Templates can have

{% raw %}

```markdown
{{reference("rider-api-schema.yaml")}}
```

This will automatically resolve this reference unambiguously (or fail if it’s ambiguous) to an `@path/to/file.yaml` string in this repo

You can also use

```markdown
```yaml
{{include("example.yaml")}}
```
```

To include it in the prompt verbatim

Or you can use:

```markdown
{{template("template.md", arg1="...")}}
```

To include it in this prompt rendered with some additional arguments

How the program works:

- We call with `claude-template template-file.md`
- It compiles the instructions using that template, and then executes `claude "{instructions}"`
- It executes in a shell mode so that we can properly interact with claude, and so that ctrl+c doesn’t kill the parent python process.

The program also has a `--dry` argument which simply causes the tool to print the compiled template and stop, without executing claude code.

{% endraw %}

- If the template file specified in the first argument is not found in the current directory, search all directories below the current one for a matching file. Much like with reference functions in the template, this should resolve to one file, and error if it is ambiguous. If there is ambiguity we can specify the parent path (e.g. `claude-template file.md` fails if it's ambiguous but we can do `claude-template example/file.md` to resolve this)
- Also allow an optional second argument for additional instructions which are added to the end of the prompt.

This is implemented at {{reference("claude_template/main.py")}} - please update the implementation if necessary.
