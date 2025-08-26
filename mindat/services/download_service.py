from pathlib import Path
from typing import Callable
from ..mindat.api_client import MindatClient
from ..repositories.localities_repo import LocalitiesRepository
from ..utils.io import JsonAccumulator, JsonlWriter

class DownloadService:
    """
    Orchestrates: search → (optional) enrich → save.
    No CLI here; CLI supplies callbacks for progress if needed.
    """
    def __init__(self, client: MindatClient, repo: LocalitiesRepository,
                 out_dir: Path, save_format: str = "json", checkpoint_every: int = 1):
        self.client, self.repo = client, repo
        self.out_dir = Path(out_dir); self.out_dir.mkdir(parents=True, exist_ok=True)
        self.save_format = save_format
        self.checkpoint_every = checkpoint_every

    def _writer(self, filename: str):
        p = self.out_dir / filename
        if self.save_format == "jsonl":
            return "jsonl", JsonlWriter(p)
        return "json", JsonAccumulator(p)

    def download_country_mines(self, country: str,
                               enrich: bool = True,
                               progress_cb: Callable[[int], None] | None = None) -> Path:
        fname = f"{country.replace(' ', '_')}_Mine_enriched.{ 'jsonl' if self.save_format=='jsonl' else 'json' }"
        mode, writer = self._writer(fname)
        count = 0

        for loc in self.repo.iter_mines_in_country(country):
            item = dict(loc)  # raw locality
            if enrich:
                # Mindat enrichment only — no text interpretation
                detail = self.client.get_locality_detail(loc["id"], expand_geomaterials=True)
                item["detail"] = detail
                # optional: also fetch explicit locality minerals list (purely endpoint-based)
                try:
                    mins = self.client.list_locality_minerals(loc["id"])
                    item["locality_minerals"] = mins
                except Exception:
                    pass

            # persist
            if mode == "jsonl":
                writer.write_one(item)
            else:
                writer.append_and_save(item)
            count += 1
            if progress_cb: progress_cb(count)
        return self.out_dir / fname
