import argparse
import io
import json
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

BATCH_SIZE = 10
DESCRIPTIONS_FILE = "emoji-descriptions.json"
REPORT_FILE = "emoji-report.html"
MODEL = "gemini-3-flash-preview"
SUPPORTED_EXTENSIONS = {".webp", ".png"}


def read_api_key() -> str:
    key_path = Path.home() / ".gemini_key"
    return key_path.read_text().strip()


def read_image_as_png(path: Path) -> bytes:
    """Read an image file and return PNG bytes, converting from webp if needed."""
    if path.suffix.lower() == ".png":
        return path.read_bytes()
    img = Image.open(path)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def find_emoji_files(directory: Path) -> list[Path]:
    files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return files


def load_descriptions(directory: Path) -> dict[str, str]:
    desc_path = directory / DESCRIPTIONS_FILE
    if desc_path.exists():
        return json.loads(desc_path.read_text())
    return {}


def save_descriptions(directory: Path, descriptions: dict[str, str]):
    desc_path = directory / DESCRIPTIONS_FILE
    desc_path.write_text(json.dumps(descriptions, indent=2))


def describe_batch(client: genai.Client, files: list[Path]) -> list[str]:
    # Build an example using the first image in the batch
    example_png = read_image_as_png(files[0])

    parts: list[types.Part] = []
    for f in files:
        png_data = read_image_as_png(f)
        parts.append(types.Part.from_bytes(mime_type="image/png", data=png_data))

    parts.append(types.Part.from_text(
        text="For each image: if it shows a standard Unicode emoji, respond with that exact emoji character. Otherwise, describe it in as few words as possible. One response per image, in the same order."
    ))

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(
                    mime_type="image/png",
                    data=example_png,
                ),
                types.Part.from_text(
                    text="If this is a standard Unicode emoji, respond with that exact emoji character. Otherwise, describe it in as few words as possible."
                ),
            ],
        ),
        types.Content(
            role="model",
            parts=[
                types.Part.from_text(text="🤧"),
            ],
        ),
        types.Content(
            role="user",
            parts=parts,
        ),
    ]

    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["descriptions"],
            properties={
                "descriptions": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(type=genai.types.Type.STRING),
                ),
            },
        ),
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=config,
    )

    result = json.loads(response.text)
    return result["descriptions"]


def generate_report(directory: Path, descriptions: dict[str, str]):
    rows = ""
    for stem in sorted(descriptions.keys()):
        desc = descriptions[stem]
        # Find the actual file to embed in the report
        img_file = None
        for ext in SUPPORTED_EXTENSIONS:
            candidate = directory / f"{stem}{ext}"
            if candidate.exists():
                img_file = candidate
                break

        img_cell = ""
        if img_file:
            img_cell = f'<img src="{img_file.name}" width="64" height="64">'

        rows += f"<tr><td>{img_cell}</td><td>{stem}</td><td>{desc}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Emoji Descriptions</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
img {{ display: block; }}
</style>
</head>
<body>
<h1>Emoji Descriptions</h1>
<table>
<tr><th>Emoji</th><th>Filename</th><th>Description</th></tr>
{rows}</table>
</body>
</html>"""

    report_path = directory / REPORT_FILE
    report_path.write_text(html)
    print(f"Report written to {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Detect and describe emojis in image files using Gemini")
    parser.add_argument("directory", type=Path, help="Directory containing emoji image files (.webp, .png)")
    args = parser.parse_args()

    directory: Path = args.directory.resolve()
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory")
        return

    all_files = find_emoji_files(directory)
    if not all_files:
        print("No emoji image files found.")
        return

    descriptions = load_descriptions(directory)
    remaining = [f for f in all_files if f.stem not in descriptions]

    if remaining:
        print(f"Found {len(all_files)} emoji files, {len(remaining)} remaining to process.")
        client = genai.Client(api_key=read_api_key())

        for i in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[i:i + BATCH_SIZE]
            names = [f.stem for f in batch]
            print(f"Processing batch {i // BATCH_SIZE + 1}: {', '.join(names)}")

            results = describe_batch(client, batch)

            for file, desc in zip(batch, results):
                descriptions[file.stem] = desc

            save_descriptions(directory, descriptions)
            print(f"  Saved {len(descriptions)} descriptions so far.")
    else:
        print("All emojis already described.")

    # Reload to ensure we have the latest
    descriptions = load_descriptions(directory)
    generate_report(directory, descriptions)


if __name__ == "__main__":
    main()
