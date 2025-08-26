#!/usr/bin/env python3
"""
Convert cleaned Mindat JSON to Leaflet-compatible GeoJSON with layers per geomaterial.

Usage:
  python scripts/to_leaflet_geojson.py \
    --in mindat_data/Iran_Mine_enriched_clean.json \
    --out-dir mindat_data/geojson

Input:
- Expects cleaned JSON from clean_mindat_json.py
- Can handle both {"results": [...]} and direct array formats
- Required fields: latitude & longitude (top-level or in detail.)
- Geomaterials are mapped from numeric IDs to human-readable names

Outputs:
1. all_mines.geojson - All mines with full properties
2. layers/*.geojson - One file per material (e.g., copper_mines.geojson)
3. layers.json - Layer metadata for easy loading:
{
  "layers": [
    {
      "id": "copper",
      "name": "Copper",
      "file": "layers/copper_mines.geojson",
      "count": 42
    },
    ...
  ]
}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def extract_coordinates(rec: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Extract [lon, lat] from various possible field names."""
    # Try explicit lat/lon fields
    if "latitude" in rec and "longitude" in rec:
        try:
            lat = float(rec["latitude"])
            lon = float(rec["longitude"])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lon, lat)
        except (ValueError, TypeError):
            pass

    # Try lat/lon
    if "lat" in rec and "lon" in rec:
        try:
            lat = float(rec["lat"])
            lon = float(rec["lon"])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lon, lat)
        except (ValueError, TypeError):
            pass

    # Try coordinates array [lon, lat]
    if "coordinates" in rec and isinstance(rec["coordinates"], (list, tuple)):
        try:
            coords = rec["coordinates"]
            if len(coords) >= 2:
                lon = float(coords[0])
                lat = float(coords[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lon, lat)
        except (ValueError, TypeError, IndexError):
            pass

    # Also check in detail. section
    detail = rec.get("detail", {})
    if isinstance(detail, dict):
        if "latitude" in detail and "longitude" in detail:
            try:
                lat = float(detail["latitude"])
                lon = float(detail["longitude"])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lon, lat)
            except (ValueError, TypeError):
                pass

    return None


def get_material_id_name() -> Dict[int, str]:
    """Hard-coded mapping of material IDs to names based on your data."""
    return {
        # From your sample data
        114: "Copper", 240: "Nickel", 406: "Gold", 433: "Silver", 447: "Lead",
        549: "Iron_Oxide", 727: "Iron", 754: "Magnetite", 836: "Chalcocite", 859: "Quartz",
        955: "Calcite", 962: "Pyrite", 1040: "Hematite", 1097: "Gypsum", 1106: "Goethite",
        1119: "Galena", 1120: "Gangue", 1144: "Fluorite", 1172: "Epidote", 1191: "Dolomite",
        1209: "Covellite", 1291: "Chrysocolla", 1304: "Barite", 1306: "Bornite", 1407: "Azurite",
        1443: "Arsenopyrite", 1641: "Chalcopyrite", 1856: "Tetrahedrite", 2011: "Uraninite",
        2156: "Sphalerite", 2265: "Skutterudite", 2298: "Smaltite", 2349: "Siegenite",
        2404: "Rammelsbergite", 2550: "Malachite", 2599: "Millerite", 2698: "Nickeline",
        2711: "Native_Copper", 2730: "Native_Silver", 2815: "Molybdenite", 2897: "Marcasite",
        2901: "Maucherite", 3106: "Linnaeite", 3184: "Libethenite", 3222: "Lautite",
        3258: "Langite", 3314: "Magnetite", 3337: "Limonite", 3357: "Linarite",
        3450: "Jarosite", 3484: "Iodargyrite", 3500: "Ilmenite", 3595: "Hematite_Variety",
        3604: "Halite", 3633: "Greenockite", 3664: "Gersdorffite", 3682: "Galena_Variety",
        3693: "Freibergite", 3727: "Sphalerite", 3876: "Erythrite", 4070: "Digenite",
        4102: "Cubanite", 4107: "Cuprite", 4113: "Cristobalite", 4327: "Cobaltite",
        4388: "Chalcanthite", 4397: "Cerussite", 6858: "Annabergite", 8601: "Uranospinite",
        9658: "Tennantite", 10936: "Silver_Amalgam", 30150: "Polybasite", 47672: "Cobalt_Bloom",
        47780: "Nickel_Bloom"
    }


def get_marker_type(rec: Dict[str, Any]) -> str:
    """Determine marker type based on locality type and attributes."""
    loc_type = str(rec.get("locality_type", "")).lower()
    if "mine" in loc_type:
        status = str(rec.get("status", "")).lower()
        if "active" in status:
            return "active_mine"
        elif "abandoned" in status or "historical" in status:
            return "abandoned_mine"
        return "mine"
    elif "prospect" in loc_type:
        return "prospect"
    elif "occurrence" in loc_type:
        return "occurrence"
    return "default"


def build_description(rec: Dict[str, Any]) -> str:
    """Build rich HTML description for popup."""
    parts = []

    # Name and type
    name = rec.get("txt") or rec.get("name")
    if name:
        parts.append(f"<h3>{name}</h3>")
    if "locality_type" in rec:
        parts.append(f"<p><strong>Type:</strong> {rec['locality_type']}</p>")
    if "status" in rec:
        parts.append(f"<p><strong>Status:</strong> {rec['status']}</p>")

    # Location
    loc_parts = []
    if "country" in rec:
        loc_parts.append(rec["country"])
    if "region" in rec:
        loc_parts.append(rec["region"])
    if loc_parts:
        parts.append(f"<p><strong>Location:</strong> {', '.join(loc_parts)}</p>")

    # Description
    if "description_short" in rec:
        parts.append(f"<p>{rec['description_short']}</p>")

    # Geomaterials
    if "geomaterials" in rec:
        parts.append(f"<p><strong>Materials:</strong> {', '.join(rec['geomaterials'])}</p>")

    # Mindat link
    if "id" in rec:
        parts.append(f'<p><a href="https://www.mindat.org/loc-{rec["id"]}.html" target="_blank">View on Mindat.org</a></p>')

    return "\n".join(parts)


def extract_elements_from_string(elements_str: str) -> List[str]:
    """Extract element symbols from elements string like '-As-Cu-Ni-O-H-Cl-Ca-P-U-C-Ba-S-Fe-Ti-Al-Si-Co-Mg-Mn-Pb-K-Ag-Na-Bi-Zn-'"""
    if not elements_str:
        return []
    # Remove leading/trailing dashes and split by dash
    elements = [e.strip() for e in elements_str.strip('-').split('-') if e.strip()]
    return elements

def clean_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant properties, focusing mainly on coordinates and geomaterials."""
    # Only require valid coordinates
    coords = extract_coordinates(rec)
    if not coords:
        return {}
    
    props = {}

    # Core identity
    if "id" in rec:
        props["id"] = f"mindat_{rec['id']}"
    name = rec.get("txt") or rec.get("name")
    if name:
        props["name"] = str(name).strip()

    # Type and status
    if "locality_type" in rec:
        props["type"] = str(rec["locality_type"]).strip()
    if "status" in rec:
        props["status"] = str(rec["status"]).strip()

    # Location
    if "country" in rec:
        props["country"] = str(rec["country"]).strip()
    if "region" in rec:
        props["region"] = str(rec["region"]).strip()

    # Description
    if "description_short" in rec:
        props["description"] = str(rec["description_short"]).strip()

    # Materials - look for geomaterials in flattened structure
    materials = set()
    mat_id_name = get_material_id_name()

    # Check for detail.geomaterials (flattened key)
    if "detail.geomaterials" in rec and isinstance(rec["detail.geomaterials"], list):
        for mat_id in rec["detail.geomaterials"]:
            if isinstance(mat_id, (int, str)):
                try:
                    mat_int = int(mat_id)
                    if mat_int in mat_id_name:
                        materials.add(mat_id_name[mat_int])
                    else:
                        # For unknown IDs, just use the ID as name
                        materials.add(f"Material_{mat_int}")
                except ValueError:
                    pass

    # Fallback to elements field for basic material categories
    if not materials:
        elements_str = rec.get("elements") or rec.get("detail.elements", "")
        elements = extract_elements_from_string(elements_str)
        # Group by major economic elements
        major_elements = {"Cu": "Copper", "Au": "Gold", "Ag": "Silver", "Pb": "Lead", 
                         "Zn": "Zinc", "Fe": "Iron", "Ni": "Nickel", "Co": "Cobalt",
                         "Mo": "Molybdenum", "U": "Uranium", "S": "Sulfide"}
        for elem in elements:
            if elem in major_elements:
                materials.add(major_elements[elem])

    # If still no materials, create a generic category
    if not materials:
        materials.add("Unknown_Material")

    props["geomaterials"] = sorted(materials)

    # Rich description
    props["description"] = build_description(rec)

    # Marker type
    props["marker_type"] = get_marker_type(rec)

    return props


def group_by_material(features: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group features by material type for layer generation."""
    layers: Dict[str, List[Dict[str, Any]]] = {}

    for feature in features:
        props = feature["properties"]
        if "geomaterials" in props:
            for mat in props["geomaterials"]:
                if mat not in layers:
                    layers[mat] = []
                layers[mat].append(feature)

    return layers


def convert_to_geojson(records: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, List[Dict[str, Any]]]]:
    """Convert records to main GeoJSON and material-specific layers."""
    features = []

    for rec in records:
        coords = extract_coordinates(rec)
        if not coords:
            continue  # Skip records without valid coordinates

        props = clean_record(rec)
        if not props:
            continue  # Skip if cleaning failed

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": coords
            },
            "properties": props
        }
        features.append(feature)

    main_geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # Group features by material
    material_layers = group_by_material(features)

    return main_geojson, material_layers


def main() -> None:
    ap = argparse.ArgumentParser("mindat-to-geojson")
    ap.add_argument("--in", dest="inp", required=True,
                   help="Path to input JSON (cleaned Mindat data)")
    ap.add_argument("--out-dir", required=True,
                   help="Directory for output GeoJSON files")
    args = ap.parse_args()

    inp = Path(args.inp)
    out_dir = Path(args.out_dir)
    if not inp.exists():
        raise SystemExit(f"Input file not found: {inp}")

    data = json.loads(inp.read_text(encoding="utf-8"))

    # Handle both {"results": [...]} and direct array formats
    records = data["results"] if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise SystemExit("Input must be a JSON array or {results: [...]} object")

    # Convert to GeoJSON and get material layers
    main_geojson, material_layers = convert_to_geojson(records)

    total = len(main_geojson["features"])
    skipped = len(records) - total
    print(f"Converted {total} mines to GeoJSON features")
    if skipped > 0:
        print(f"Skipped {skipped} records (missing coordinates)")

    # Create output directories
    out_dir.mkdir(parents=True, exist_ok=True)
    layers_dir = out_dir / "layers"
    layers_dir.mkdir(exist_ok=True)

    # Write main GeoJSON
    with (out_dir / "all_mines.geojson").open("w", encoding="utf-8") as f:
        json.dump(main_geojson, f, ensure_ascii=False, indent=2)

    # Write per-material layers
    for material, features in material_layers.items():
        layer_data = {
            "type": "FeatureCollection",
            "features": features
        }
        material_file = f"{material.lower().replace(' ', '_')}_mines.geojson"
        with (layers_dir / material_file).open("w", encoding="utf-8") as f:
            json.dump(layer_data, f, ensure_ascii=False, indent=2)

    # Write layer metadata
    layer_info = {
        "layers": [
            {
                "id": material.lower().replace(" ", "_"),
                "name": material,
                "file": f"layers/{material.lower().replace(' ', '_')}_mines.geojson",
                "count": len(features)
            }
            for material, features in material_layers.items()
        ]
    }
    with (out_dir / "layers.json").open("w", encoding="utf-8") as f:
        json.dump(layer_info, f, ensure_ascii=False, indent=2)

    print(f"\nCreated {len(material_layers)} material layers:")
    for material, features in material_layers.items():
        print(f"  - {material}: {len(features)} mines")

    print("\nUse in Leaflet like this:")
    print("""
    // Define marker icons per type
    const markerIcons = {
      active_mine: L.icon({ iconUrl: 'markers/active_mine.png', ... }),
      abandoned_mine: L.icon({ iconUrl: 'markers/abandoned_mine.png', ... }),
      mine: L.icon({ iconUrl: 'markers/mine.png', ... }),
      prospect: L.icon({ iconUrl: 'markers/prospect.png', ... }),
      occurrence: L.icon({ iconUrl: 'markers/occurrence.png', ... }),
      default: L.icon({ iconUrl: 'markers/default.png', ... })
    };

    // Load layer metadata
    fetch('geojson/layers.json')
      .then(response => response.json())
      .then(metadata => {
        // Create layer groups
        const layers = {};
        const overlays = {};

        // Load each material layer
        metadata.layers.forEach(layer => {
          fetch(layer.file)
            .then(response => response.json())
            .then(data => {
              layers[layer.id] = L.geoJSON(data, {
                pointToLayer: (feature, latlng) => {
                  const icon = markerIcons[feature.properties.marker_type] || markerIcons.default;
                  return L.marker(latlng, { icon }).bindPopup(feature.properties.description);
                }
              });
              overlays[layer.name] = layers[layer.id];
              // Add to map and layer control
              layers[layer.id].addTo(map);
              L.control.layers(null, overlays).addTo(map);
            });
        });
      });
    """)


if __name__ == "__main__":
    main()
