import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict, Any


def create_circle_feature(row: Dict[str, str], radius: float) -> Dict[str, Any]:
    """
    Create a GeoJSON feature for a circle (represented as a Point with radius property).

    Args:
        row: CSV row dictionary with Name, Address, Postcode (optional), lat, lng
        radius: Circle radius in meters

    Returns:
        GeoJSON feature dictionary
    """
    lat = float(row["lat"])
    lng = float(row["lng"])

    # Build address with postcode if available
    address = row["Address"]
    if "Postcode" in row and row["Postcode"]:
        address = f"{address}, {row['Postcode']}"

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lng, lat]
        },
        "properties": {
            "subType": "Circle",
            "radius": radius,
            "Name": row["Name"],
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
    """
    Convert CSV file with POI data to GeoJSON with circle features.

    Args:
        input_file: Path to input CSV file
        keyword: Name/keyword for the feature collection
        radius: Circle radius in meters
        output_file: Path to output GeoJSON file
    """
    features: List[Dict[str, Any]] = []

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
