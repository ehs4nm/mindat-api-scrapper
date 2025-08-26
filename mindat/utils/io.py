import json
from pathlib import Path
from typing import Iterable, Any

class AtomicWriter:
    def __init__(self, path: Path):
        self.path = path

    def write_json(self, obj: Any):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

class JsonAccumulator:
    """Keeps a growing list in memory and writes full JSON after each append."""
    def __init__(self, out_path: Path):
        self.out_path = out_path
        self.data = {"results": []}
        if out_path.exists():
            try:
                self.data = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {"results": []}
        self.writer = AtomicWriter(out_path)

    def append_and_save(self, item: dict):
        self.data["results"].append(item)
        self.writer.write_json(self.data)

class JsonlWriter:
    """Stream each item as a JSON line (scale-friendly)."""
    def __init__(self, out_path: Path):
        self.out_path = out_path
        self.out_path.parent.mkdir(parents=True, exist_ok=True)

    def write_one(self, item: dict):
        with self.out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
