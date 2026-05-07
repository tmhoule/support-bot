import json
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path


@dataclass
class Watermark:
    last_run: datetime
    sha: str | None = None
    error_count: int = 0
    last_error: str | None = None


class WatermarkStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def get(self, source: str) -> Watermark | None:
        d = self._data.get(source)
        if not d:
            return None
        return Watermark(
            last_run=datetime.fromisoformat(d["last_run"]),
            sha=d.get("sha"),
            error_count=d.get("error_count", 0),
            last_error=d.get("last_error"),
        )

    def set(self, source: str, last_run: datetime, sha: str | None = None) -> None:
        wm = Watermark(last_run=last_run, sha=sha, error_count=0, last_error=None)
        self._data[source] = {"last_run": wm.last_run.isoformat(), "sha": wm.sha, "error_count": 0, "last_error": None}
        self._flush()

    def record_failure(self, source: str, error: str) -> None:
        cur = self._data.get(source, {"last_run": datetime.now(UTC).isoformat(), "sha": None, "error_count": 0, "last_error": None})
        cur["error_count"] = cur.get("error_count", 0) + 1
        cur["last_error"] = error
        self._data[source] = cur
        self._flush()

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def all(self) -> dict[str, Watermark]:
        return {k: self.get(k) for k in self._data}
