from dataclasses import dataclass, field
from pathlib import Path
import os, yaml

@dataclass
class Timeouts:
    connect: int = 10
    read: int = 40

@dataclass
class Retries:
    total: int = 6
    backoff_factor: float = 1.2
    status_forcelist: list[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])

@dataclass
class Endpoints:
    localities: str = "/localities/"
    locality_detail: str = "/localities/{id}/"
    locality_minerals: str = "/localityminerals/"

@dataclass
class SaveCfg:
    dir: str = "mindat_data"
    format: str = "json"
    checkpoint_every: int = 1

@dataclass
class AppConfig:
    base_url: str = "https://api.mindat.org/v1"
    api_key_file: str = "api_key.txt"
    timeouts: Timeouts = field(default_factory=Timeouts)
    retries: Retries = field(default_factory=Retries)
    page_size: int = 100
    endpoints: Endpoints = field(default_factory=Endpoints)
    search_strategies: list[dict] = field(default_factory=list)
    save: SaveCfg = field(default_factory=SaveCfg)

def load_config(path: str | Path) -> AppConfig:
    cfg = AppConfig()
    if Path(path).exists():
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        # shallow merge for simplicity
        for k, v in raw.items():
            if hasattr(cfg, k):
                if isinstance(getattr(cfg, k), (Timeouts, Retries, Endpoints, SaveCfg)):
                    nested = getattr(cfg, k)
                    for nk, nv in v.items():
                        setattr(nested, nk, nv)
                else:
                    setattr(cfg, k, v)
    # env override for key path
    cfg.api_key_file = os.getenv("MINDAT_API_KEY_FILE", cfg.api_key_file)
    return cfg

def read_api_key(file: str) -> str:
    p = Path(file)
    if not p.exists():
        raise FileNotFoundError(f"API key file not found: {file}")
    return p.read_text(encoding="utf-8").strip()
