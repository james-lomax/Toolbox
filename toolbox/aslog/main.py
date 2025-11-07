import argparse
import base64
import gzip
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def decode_payload(base64_payload: str) -> dict[str, Any] | None:
    """
    Decode a base64-encoded payload to JSON.

    Tries to:
    1. Decode base64 to bytes
    2. Try decoding as UTF-8 JSON
    3. If that fails, try decompressing with gzip first, then decoding as UTF-8 JSON

    Args:
        base64_payload: Base64-encoded string

    Returns:
        Decoded JSON object or None if decoding fails
    """
    if not base64_payload:
        return None

    try:
        # Decode base64
        decoded_bytes = base64.b64decode(base64_payload)

        # Try direct JSON decode
        try:
            decoded_str = decoded_bytes.decode('utf-8')
            return json.loads(decoded_str)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

        # Try gzip decompress then JSON decode
        try:
            decompressed = gzip.decompress(decoded_bytes)
            decoded_str = decompressed.decode('utf-8')
            return json.loads(decoded_str)
        except (gzip.BadGzipFile, UnicodeDecodeError, json.JSONDecodeError):
            pass

    except Exception:
        pass

    return None


def parse_response_time(headers: dict[str, str]) -> str | None:
    """
    Parse the response time from headers.

    Looks for the 'date' header and converts it to ISO8601 format.

    Args:
        headers: Response headers dictionary

    Returns:
        ISO8601 formatted timestamp or None if parsing fails
    """
    date_str = headers.get('date')
    if not date_str:
        return None

    try:
        # Parse HTTP date format: "Thu, 06 Nov 2025 15:28:50 GMT"
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        # Format as ISO8601 with 'Z' suffix
        return dt.strftime('%Y-%m-%dT%H%M%SZ')
    except Exception:
        return None


def simplify_log_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Simplify a single Android Studio log entry.

    Args:
        entry: Original log entry

    Returns:
        Simplified log entry
    """
    duration_microseconds = entry.get('duration-microseconds', 0)
    duration_secs = round(duration_microseconds / 1_000_000, 2)

    request_body = decode_payload(entry.get('request-payload-base64', ''))
    response_body = decode_payload(entry.get('response-payload-base64', ''))

    response_headers = entry.get('response-headers', {})
    response_time = parse_response_time(response_headers)

    return {
        'duration-secs': duration_secs,
        'method': entry.get('method', ''),
        'url': entry.get('url', ''),
        'request-body': request_body,
        'response-time': response_time,
        'response-status': entry.get('response-code', 0),
        'response-body': response_body,
    }


def is_via_url(url: str) -> bool:
    """
    Check if a URL is for a Via host (ends with .ridewithvia.com).

    Args:
        url: URL to check

    Returns:
        True if the URL host ends with .ridewithvia.com
    """
    # Extract host from URL and check if it ends with .ridewithvia.com
    match = re.match(r'https?://([^/]+)', url)
    if match:
        host = match.group(1)
        return host.endswith('.ridewithvia.com')
    return False


def process_log_file(
    input_path: Path,
    output_path: Path,
    via_only: bool = False
) -> None:
    """
    Process an Android Studio log file and output simplified JSON.

    Args:
        input_path: Path to input JSON file
        output_path: Path to output JSON file
        via_only: If True, only include requests to .ridewithvia.com hosts
    """
    try:
        # Read input file
        with open(input_path, 'r', encoding='utf-8') as f:
            log_entries = json.load(f)

        if not isinstance(log_entries, list):
            print("Error: Input file must contain a JSON array", file=sys.stderr)
            sys.exit(1)

        # Process entries
        simplified_entries = []
        for entry in log_entries:
            # Filter by Via if requested
            if via_only and not is_via_url(entry.get('url', '')):
                continue

            simplified = simplify_log_entry(entry)
            simplified_entries.append(simplified)

        # Write output file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(simplified_entries, f, indent=2)

        print(f"Processed {len(log_entries)} entries, output {len(simplified_entries)} entries to {output_path}")

    except FileNotFoundError:
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the aslog tool."""
    parser = argparse.ArgumentParser(
        description="Convert Android Studio log files to simplified JSON format"
    )

    parser.add_argument(
        'input_file',
        help='Input JSON log file'
    )

    parser.add_argument(
        'output_file',
        nargs='?',
        help='Output JSON file (default: input_file with .simple.json extension)'
    )

    parser.add_argument(
        '--via-only',
        action='store_true',
        help='Only include requests to .ridewithvia.com hosts'
    )

    args = parser.parse_args()

    # Determine input and output paths
    input_path = Path(args.input_file)

    if args.output_file:
        output_path = Path(args.output_file)
    else:
        # Derive output filename from input
        if input_path.suffix == '.json':
            output_path = input_path.with_suffix('.simple.json')
        else:
            output_path = input_path.parent / f"{input_path.name}.simple.json"

    # Process the log file
    process_log_file(input_path, output_path, args.via_only)


if __name__ == "__main__":
    main()
