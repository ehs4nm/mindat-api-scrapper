# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- Language: Python (requests, PyYAML, tqdm)
- Purpose: Download Mindat locality data by country, optionally enriching each locality with detail and minerals, and persist results to JSON or JSONL.
- Entry: CLI orchestrator that wires config → HTTP client → API client → repository (search strategies) → download service (save + progress).
- Important: Imports assume a package namespace named "mindat" and use relative imports inside subpackages. Prefer running as a module (python -m ...) so package context is set.

Common commands
- Create and activate a virtualenv, then install runtime deps:
```bash path=null start=null
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install requests pyyaml tqdm
```
- Set API key file location (can also be configured in config.yaml):
```bash path=null start=null
export MINDAT_API_KEY_FILE={{PATH_TO_API_KEY_TXT}}
```
- Run the downloader non-interactively (recommended: run as a module to satisfy package imports):
```bash path=null start=null
python -m mindat.main --config config.yaml --country "Iran" --page-size 200
```
- Run with interactive prompts (country/type/page size asked on stdin):
```bash path=null start=null
python -m mindat.main
```
- Disable enrichment calls to speed up scraping (skips detail and minerals endpoints):
```bash path=null start=null
python -m mindat.main --country "Iran" --no-enrich
```
Notes
- There is no test suite or linter configuration in this repo at present.
- No Makefile/pyproject/requirements.txt are present; the commands above install the minimal runtime dependencies used by the code.
- If module execution fails due to package layout, ensure you run from the project root and that the code is available under the "mindat" package namespace. The code uses relative imports (e.g., ..api_client) and absolute imports (mindat.*).

Configuration
- The application reads a YAML config (default: config.yaml) and an API key file (default: api_key.txt or $MINDAT_API_KEY_FILE).
- Minimal example config.yaml:
```yaml path=null start=null
base_url: https://api.mindat.org/v1
api_key_file: api_key.txt
page_size: 100
endpoints:
  localities: "/localities/"
  locality_detail: "/localities/{id}/"
  locality_minerals: "/localityminerals/"
search_strategies:
  # Try strategies in order until results are found, then stream all
  - { param: "ltype", value: 60 }   # ID for "Mine" type on Mindat
  - { param: "txt",   value: "Mine" }
save:
  dir: mindat_data
  format: json         # or "jsonl"
  checkpoint_every: 1
```
- Key options:
  - --config: path to YAML config; values shallow-merge over defaults in code.
  - --country: country name to query; when omitted, an interactive prompt is shown.
  - --page-size: override configured pagination size.
  - --no-enrich: skip detail and minerals calls (faster, less data).
  - Environment override: MINDAT_API_KEY_FILE takes precedence over config.api_key_file.

High-level architecture
- CLI (mindat.main, cli/prompts.py)
  - Parses args, optionally prompts for inputs, loads config, sets up logging and progress bar.
  - Wires together endpoints → HTTP session → API client → repository → download service.
- Config (mindat.config)
  - Dataclasses: Timeouts, Retries, Endpoints, SaveCfg, AppConfig.
  - load_config merges YAML over defaults; read_api_key loads token path (file required).
- HTTP (mindat.http)
  - HttpSession wraps requests.Session with retries (urllib3 Retry), auth header (Token {key}), timeouts, and JSON validation/errors.
- Endpoints (mindat.endpoints)
  - MindatEndpoints holds path templates and builds full URLs.
- API client (mindat.api_client)
  - MindatClient provides endpoint-level methods: search_localities (paged iterator), get_locality_detail, list_locality_minerals.
  - _extract_page centralizes paging extraction for both list/dict responses.
- Repository (mindat.repositories.localities_repo)
  - LocalitiesRepository encapsulates search strategy logic sourced from config.yaml; tries strategies in order until results, then streams all.
- Service (mindat.services.download_service)
  - DownloadService orchestrates: iterate localities → optional enrichment → persist via JsonAccumulator or JsonlWriter; supports progress callback.
- Utils (mindat.utils.io, mindat.utils.logging)
  - IO: atomic JSON writes, append-and-save accumulator for JSON, streaming JSONL writer.
  - Logging: writes timestamped run log into save.dir and to console.

Data and outputs
- Output directory: save.dir (default: mindat_data) is created automatically.
- File naming: {Country}_Mine_enriched.json or .jsonl depending on save.format.
- JSON format:
  - json: accumulates under a top-level { "results": [ ... ] } structure and rewrites atomically on each append.
  - jsonl: one JSON object per line, suitable for large outputs.

Troubleshooting
- ImportError for mindat.* or relative imports:
  - Ensure you execute as a module from the repository root: python -m mindat.main
  - Confirm the code resides under a package namespace (mindat/) so that relative imports inside subpackages (e.g., repositories/, services/, utils/) resolve.
- HTTP errors 401/403 indicate an invalid or missing API key; ensure MINDAT_API_KEY_FILE points to a valid token file.

