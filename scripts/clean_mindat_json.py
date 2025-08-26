#!/usr/bin/env python3
"""
Clean a Mindat JSON export by:
- Flattening nested dict fields into a single level (dot-notation keys)
- Removing empty fields (None, "", whitespace-only, [], {})
- Resolving duplicate keys by preference (nested vs top-level)

Usage examples:
  python scripts/clean_mindat_json.py \
    --in mindat_data/Iran_Mine_enriched.json \
    --out mindat_data/Iran_Mine_enriched_clean.json

Options:
  --prefer {nested,top}   When a flattened key collides with an existing key, prefer value
                          coming from the nested dict ('nested') or existing/top-level ('top').
                          Default: nested

Input formats supported:
- JSON object with a top-level {"results": [...]} list (default output of this repo when format=json)
- JSON array of objects
Output format mirrors input: if input had "results", output will too; otherwise a JSON array.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def is_empty_value(v: Any) -> bool:
    if v is None:
        return True
    # Preserve booleans (False is not considered empty here)
    if isinstance(v, bool):
        return False
    # Consider numeric zeros as empty (0, 0.0)
    if isinstance(v, (int, float)):
        return v == 0
    if isinstance(v, str):
        # Remove if string is empty, whitespace-only, or just "0"
        stripped = v.strip()
        return len(stripped) == 0 or stripped == "0"
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) == 0
    return False


def flatten_dict(d: Dict[str, Any], parent: str = "", sep: str = ".") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        key = f"{parent}{sep}{k}" if parent else k
        if isinstance(v, dict):
            out.update(flatten_dict(v, key, sep=sep))
        else:
            out[key] = v
    return out


def merge_with_preference(base: Dict[str, Any], extra: Dict[str, Any], prefer_nested: bool = True) -> Dict[str, Any]:
    out = dict(base)
    for k, v in extra.items():
        if k in out:
            # if identical, keep one
            if out[k] == v:
                continue
            # conflict: choose based on preference
            if prefer_nested:
                out[k] = v
            # else keep existing
        else:
            out[k] = v
    return out


def clean_record(rec: Dict[str, Any], prefer_nested: bool = True) -> Dict[str, Any]:
    # Step 1: remove empty top-level fields early
    pruned: Dict[str, Any] = {k: v for k, v in rec.items() if not is_empty_value(v)}

    # Step 2: separate nested dict fields to flatten; keep non-dict as-is
    flat_accum: Dict[str, Any] = {}
    passthrough: Dict[str, Any] = {}

    for k, v in pruned.items():
        if isinstance(v, dict):
            flat_part = flatten_dict(v, parent=k)
            flat_accum = merge_with_preference(flat_accum, flat_part, prefer_nested=prefer_nested)
        else:
            passthrough[k] = v

    # Step 3: merge flattened into top-level according to preference
    # Note: After flattening, keys look like "detail.name"; they generally won't collide with top-level keys.
    merged = merge_with_preference(passthrough, flat_accum, prefer_nested=prefer_nested)

    # Step 4: drop empty values post-merge
    cleaned = {k: v for k, v in merged.items() if not is_empty_value(v)}
    return cleaned


def clean_records(recs: Iterable[Dict[str, Any]], prefer_nested: bool = True) -> list[Dict[str, Any]]:
    return [clean_record(r, prefer_nested=prefer_nested) for r in recs]


def main() -> None:
    ap = argparse.ArgumentParser("clean-mindat-json")
    ap.add_argument("--in", dest="inp", required=True, help="Path to input JSON file")
    ap.add_argument("--out", dest="out", required=True, help="Path to output JSON file")
    ap.add_argument("--prefer", choices=["nested", "top"], default="nested",
                    help="When flattened keys collide, prefer nested or existing/top-level value")
    args = ap.parse_args()

    inp = Path(args.inp)
    outp = Path(args.out)
    if not inp.exists():
        raise SystemExit(f"Input file not found: {inp}")

    raw_text = inp.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    prefer_nested = args.prefer == "nested"

    if isinstance(data, dict) and isinstance(data.get("results"), list):
        cleaned = clean_records(data["results"], prefer_nested=prefer_nested)
        out_data = {"results": cleaned}
    elif isinstance(data, list):
        cleaned = clean_records(data, prefer_nested=prefer_nested)
        out_data = cleaned
    else:
        raise SystemExit("Unsupported input JSON shape. Expected {\"results\": [...]} or a list of objects.")

    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote cleaned file → {outp}")


if __name__ == "__main__":
    main()

