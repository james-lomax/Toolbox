Create or update the `{{tool_name}}` tool.

Follow the structure of tools in this repository:

- Tools are defined using Python, and each has its own python package in the toolbox package (e.g. `toolbox/example/`), with an empty `__init__.py` and a `main.py` file with a main function
    - The tool package name must follow python package naming conventions
- Tools are installed as scripts by an entry in `pyproject.toml`, e.g. `example = "toolbox.example.main:main"`

Create a python package with a suitable name in the `toolbox` package. Add `__init__.py` (empty) and `main.py` with a main function to implement the tool.

Add a script entry to pyproject.toml which links to the `{{tool_name}}` tools main function.

Do not write tests unless instructed to.
