"""Common test utilities."""

from __future__ import annotations

import json
from pathlib import Path
from shapely import wkt
from shapely.geometry.base import BaseGeometry
from typing import Any
SAMPLES_DIR = Path(__file__).parent / "data" / "samples"

def load_wkt(text: str) -> BaseGeometry:
    return wkt.loads(text)


def same_geometry(a: str | BaseGeometry, b: str | BaseGeometry) -> bool:
    """Topological equality (independent of vertex order)."""
    ga = load_wkt(a) if isinstance(a, str) else a
    gb = load_wkt(b) if isinstance(b, str) else b
    return ga.equals(gb)

def load_sample(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
