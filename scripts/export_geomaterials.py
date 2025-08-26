import argparse
from pathlib import Path
from typing import List, Dict

from mindat.config import load_config, read_api_key
from mindat.http import HttpSession
from mindat.utils.io import AtomicWriter


def fetch_all_geomaterials(http: HttpSession, base_url: str, page_size: int) -> List[Dict]:
    """
    Fetch all geomaterials by following pagination until 'next' is None.
    Returns a list of geomaterial objects.
    """
    url = f"{base_url}/geomaterials/"
    params = {"format": "json", "page_size": page_size}

    out: List[Dict] = []
    page = http.get_json(url, params)
    results = page.get("results") if isinstance(page, dict) else None
    if isinstance(results, list):
        out.extend(results)
    next_url = page.get("next") if isinstance(page, dict) else None

    while next_url:
        page = http.get_json(next_url)
        results = page.get("results") if isinstance(page, dict) else None
        if isinstance(results, list):
            out.extend(results)
        next_url = page.get("next") if isinstance(page, dict) else None

    return out


def main():
    ap = argparse.ArgumentParser("export-geomaterials")
    ap.add_argument("--config", default="config.yaml", help="Path to YAML config (default: config.yaml)")
    ap.add_argument("--page-size", type=int, default=None, help="Override configured page size")
    ap.add_argument("--out", default=None, help="Output file path (default: save.dir/geomaterials.json)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.page_size:
        cfg.page_size = args.page_size

    # Resolve output path
    out_path = Path(args.out) if args.out else Path(cfg.save.dir) / "geomaterials.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Auth + HTTP
    api_key = read_api_key(cfg.api_key_file)
    http = HttpSession(cfg.base_url, cfg.retries, cfg.timeouts, api_key)

    # Fetch and persist
    items = fetch_all_geomaterials(http, cfg.base_url, cfg.page_size)
    writer = AtomicWriter(out_path)
    writer.write_json({"results": items})

    print(str(out_path))


if __name__ == "__main__":
    main()
