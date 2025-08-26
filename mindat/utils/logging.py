import logging
from pathlib import Path
from datetime import datetime

def setup_logger(name="mindat", out_dir="mindat_data") -> logging.Logger:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(Path(out_dir) / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8")
    fh.setFormatter(fmt); log.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt); log.addHandler(ch)
    return log
