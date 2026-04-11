import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Any


def get_field(row: Dict[str, str], *candidates: str) -> str | None:
    """Look up a field by trying candidate names case-insensitively."""
    lower_map = {k.lower(): k for k in row}
    for c in candidates:
        actual_key = lower_map.get(c.lower())
        if actual_key is not None:
            return row[actual_key]
    return None


def require_field(row: Dict[str, str], *candidates: str) -> str:
    value = get_field(row, *candidates)
    if value is None:
        raise KeyError(f"Missing required field (tried: {', '.join(candidates)})")
    return value


def create_circle_feature(row: Dict[str, str], radius: float) -> Dict[str, Any]:
    lat = float(require_field(row, "lat", "latitude"))
    lng = float(require_field(row, "lng", "lon", "longitude"))
    name = require_field(row, "name")
    address = require_field(row, "address")

    postcode = get_field(row, "postcode")
    if postcode:
        address = f"{address}, {postcode}"

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lng, lat]
        },
        "properties": {
            "subType": "Circle",
            "radius": radius,
            "Name": name,
            "Address": address,
            "lat": lat,
            "lng": lng
        }
    }


def process_csv_to_geojson(
    input_file: Path,
    keyword: str,
    radius: float,
    output_file: Path
) -> None:
    features: list[Dict[str, Any]] = []

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            feature = create_circle_feature(row, radius)
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "name": keyword,
        "features": features
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=4)


def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV POI data to GeoJSON with circle features"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Input CSV file with POI data (Name, Address, Postcode (optional), lat, lng)"
    )
    parser.add_argument(
        "keyword",
        type=str,
        help="Keyword/name for the feature collection"
    )
    parser.add_argument(
        "radius",
        type=float,
        help="Circle radius in meters"
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Output GeoJSON file path"
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        raise SystemExit(f"Input file does not exist: {args.input_file}")

    process_csv_to_geojson(
        args.input_file,
        args.keyword,
        args.radius,
        args.output_file
    )


if __name__ == "__main__":
    main()
