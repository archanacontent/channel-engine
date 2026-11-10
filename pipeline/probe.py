"""Checks every source without writing or uploading anything.

    python -m pipeline.probe
Prints, per series, how many unused records are available and the first headline.
"""
import itertools
import json
from pathlib import Path

from sources.fetch import SERIES

used = set(json.loads(Path("state/used.json").read_text())) if Path("state/used.json").exists() else set()
for slug, series in SERIES.items():
    for name, fn in series.items():
        try:
            recs = list(itertools.islice(fn(used), 8))
            first = recs[0]["headline"] if recs else "-"
            print(f"{slug:20} {name:22} {len(recs):>2}+  {first[:70]}")
        except Exception as e:
            print(f"{slug:20} {name:22} ERROR {e}")
