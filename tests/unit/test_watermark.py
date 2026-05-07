from datetime import datetime, UTC
from indexer.watermark import WatermarkStore


def test_roundtrip(tmp_path):
    s = WatermarkStore(tmp_path / "wm.json")
    assert s.get("github") is None
    now = datetime.now(UTC)
    s.set("github", now, sha="abc")
    again = WatermarkStore(tmp_path / "wm.json")
    wm = again.get("github")
    assert wm.sha == "abc"
    assert wm.last_run.replace(microsecond=0) == now.replace(microsecond=0)
