import argparse
from pathlib import Path
from tqdm import tqdm

from mindat.config import load_config, read_api_key
from mindat.endpoints import MindatEndpoints
from mindat.utils.logging import setup_logger
from mindat.http import HttpSession
from mindat.api_client import MindatClient
from mindat.repositories.localities_repo import LocalitiesRepository
from mindat.services.download_service import DownloadService
from .prompts import Questioner

def main():
    ap = argparse.ArgumentParser("mindat-downloader")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--country", default=None)
    ap.add_argument("--type", dest="ltype", default="Mine")
    ap.add_argument("--page-size", type=int, default=None)
    ap.add_argument("--no-enrich", action="store_true", help="Do not call detail/minerals endpoints")
    args = ap.parse_args()

    cfg = load_config(args.config)
    log = setup_logger(out_dir=cfg.save.dir)

    api_key = read_api_key(cfg.api_key_file)
    if args.page_size: cfg.page_size = args.page_size

    # Build endpoints + HTTP
    ep = MindatEndpoints(
        base_url=cfg.base_url,
        localities=cfg.endpoints.localities,
        locality_detail=cfg.endpoints.locality_detail,
        locality_minerals=cfg.endpoints.locality_minerals,
    )
    http = HttpSession(cfg.base_url, cfg.retries, cfg.timeouts, api_key)
    client = MindatClient(http, ep, page_size=cfg.page_size)

    # Inputs
    if args.country:
        country = args.country
    else:
        q = Questioner().ask()
        country = q.country
        if q.page_size: client.page_size = q.page_size

    # Repo wired with strategies from config (facts that change)
    repo = LocalitiesRepository(client, cfg.search_strategies)

    # Service (pure orchestration)
    svc = DownloadService(
        client=client,
        repo=repo,
        out_dir=Path(cfg.save.dir),
        save_format=cfg.save.format,
        checkpoint_every=cfg.save.checkpoint_every
    )

    bar = tqdm(unit="loc")
    def tick(_): bar.update(1)

    out = svc.download_country_mines(country, enrich=not args.no_enrich, progress_cb=tick)
    bar.close()
    log.info(f"Saved → {out}")

if __name__ == "__main__":
    main()
