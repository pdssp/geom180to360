"""Polygons whose outer ring goes around a pole.

A polar footprint is often described by a ring that goes around the pole
without having a vertex at ±90°, for example
``POLYGON ((0 80, 90 75, 180 80, -90 85, 0 80))``. In the lon/lat plane, this
ring has no meaning: it forms a band with no thickness or that overlaps itself.
This module recognizes it and replaces it with the cap it encloses.
"""

from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import GeometryCollection, LinearRing, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .geometry_utils import EPS, assemble, keep_dimension, translate

__all__ = ["resolve_polar_rings"]

_WORLD_180 = box(-180, -90, 180, 90)


def _wrap_dlon(dlon: np.ndarray) -> np.ndarray:
    """Bring longitude differences within ]-180, 180]."""
    return dlon - 360.0 * np.ceil((dlon - 180.0) / 360.0)


def _unwrap_ring(coords) -> np.ndarray:
    """Longitudes laid end-to-end: each difference is taken along the shortest path.

    :return: array (n, 2) whose longitudes may be outside [-180, 180].
    """
    coords = np.asarray(coords, dtype=float)[:, :2]
    lons = coords[0, 0] + np.concatenate(
        [[0.0], np.cumsum(_wrap_dlon(np.diff(coords[:, 0])))]
    )
    return np.column_stack([lons, coords[:, 1]])


def _polar_winding(coords) -> float:
    """Sum of longitude differences along a ring (0 or ±360)."""
    unwrapped = _unwrap_ring(coords)
    return float(unwrapped[-1, 0] - unwrapped[0, 0])


def _encircled_pole(ring: LinearRing) -> float | None:
    """Pole (+90 or -90) around which the ring goes, ``None`` otherwise.

    A ring that already has a vertex at the pole is a cap described in the
    lon/lat plane (e.g., ``box(-180, 70, 180, 90)``): it is not concerned.
    The pole chosen is that of the hemisphere of the ring's mean latitude; at
    the equator, the traversal direction decides (eastward: North Pole).
    """
    coords = np.asarray(ring.coords)[:, :2]
    if np.any(np.abs(coords[:, 1]) >= 90.0 - EPS):
        return None
    winding = _polar_winding(coords)
    if abs(abs(winding) - 360.0) > 1e-6:
        return None
    mean_lat = coords[:-1, 1].mean()
    if mean_lat != 0:
        return 90.0 if mean_lat > 0 else -90.0
    return 90.0 if winding > 0 else -90.0


def _fold_180(geom: BaseGeometry) -> BaseGeometry:
    """Fold back into [-180, 180] a geometry whose longitudes exceed it."""
    pieces = [translate(geom, 360.0 * k).intersection(_WORLD_180) for k in range(-2, 3)]
    return unary_union([p for piece in pieces for p in keep_dimension(piece, 2)])


def _polar_cap(poly: Polygon, pole: float) -> BaseGeometry:
    """Cap enclosed by the outer ring of ``poly`` and closed at the pole."""
    ring = _unwrap_ring(poly.exterior.coords)
    start, end = ring[0, 0], ring[-1, 0]
    cap = shapely.make_valid(Polygon([*map(tuple, ring), (end, pole), (start, pole)]))
    cap = _fold_180(cap)
    holes = [
        _fold_180(shapely.make_valid(Polygon(_unwrap_ring(h.coords))))
        for h in poly.interiors
    ]
    return cap.difference(unary_union(holes)) if holes else cap


def resolve_polar_rings(geom: BaseGeometry) -> BaseGeometry:
    """Replace polygons that go around a pole with their cap.

    The ring is detected by the sum of longitude differences between
    consecutive vertices, each taken along the shortest path (|difference| < 180°):
    ±360° instead of 0. The polygon is then reconstructed in the plane as the area
    between the ring and the pole, folded back into [-180, 180]. Holes are
    treated the same way.

    Other geometries are returned as is.

    :param geom: geometry with longitudes in [-180, 180].
    :return: equivalent geometry without polar ring.
    """
    if geom.geom_type == "GeometryCollection":
        return GeometryCollection([resolve_polar_rings(g) for g in geom.geoms])
    if geom.geom_type not in ("Polygon", "MultiPolygon") or geom.is_empty:
        return geom
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    poles = [_encircled_pole(p.exterior) for p in polys]
    if all(pole is None for pole in poles):
        return geom
    parts = [
        p if pole is None else _polar_cap(p, pole)
        for p, pole in zip(polys, poles, strict=True)
    ]
    merged = [q for part in parts for q in keep_dimension(part, 2)]
    return assemble(merged, 2, geom.geom_type == "MultiPolygon")
