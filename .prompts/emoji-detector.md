{{template("new-tool.md", tool_name="emoji-detector")}}

This tool reads all the image files from a directory (which contains a mix of .webp and .png files, each showing an emoji) and uses Gemini flash to determine a concise description of each one.

## Architecture

### Prompting

Here is an example of how we construct a prompt for a single emoji:

```python

# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        api_key=# TODO Read from ~/.gemini_key
    )

    model = "gemini-3-flash-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    mime_type="image/webp",
                    data=# image data
                ),
                types.Part.from_text(text="""Describe the emoji in this image in as few words as possible"""),
            ],
        ),
        types.Content(
            role="model",
            parts=[
                types.Part.from_text(text="""Sneezing face."""),
            ],
        ),
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level="HIGH",
        ),
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type = genai.types.Type.OBJECT,
            required = ["descriptions"],
            properties = {
                "descriptions": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.STRING,
                    ),
                ),
            },
        ),
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    # TODO Process response object

if __name__ == "__main__":
    generate()
```

We will construct prompts which supply multiple emojis (10 at a time) and request that the model returns a list of concise descriptions for each one.

## Processing

The tool will process 10 emojis at a time. After each response from the model, we will update a emoji-descriptions.json file in the working directory. This will contain a map of each filename (without the extension) and the description.

If the tool is interrupted and resumed, the tool will determine the remaining emojis to process by comparing the files found in the local directory with the list of already completed descriptions in the emoji-descriptions.json file.

Once all have been processed, the file will be read again and the tool will generate an html report file containing a table which shows each emoji, alongside the filename, and the description.
