"""Geometric utils."""

from __future__ import annotations

import shapely
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge, unary_union

#: Tolerance for coordinate comparisons (degrees).
EPS = 1e-12


def translate(geom: BaseGeometry, dx: float) -> BaseGeometry:
    """Shift all longitudes by ``dx`` degrees."""

    def _transform(coords):
        coords = coords.copy()
        coords[:, 0] += dx
        return coords

    return shapely.transform(geom, _transform, include_z=geom.has_z)


def keep_dimension(geom: BaseGeometry, dim: int) -> list[BaseGeometry]:
    """Extract simple components of dimension ``dim`` from a geometry."""
    if geom.is_empty:
        return []
    if hasattr(geom, "geoms"):
        parts: list[BaseGeometry] = []
        for g in geom.geoms:
            parts.extend(keep_dimension(g, dim))
        return parts
    return [geom] if shapely.get_dimensions(geom) == dim else []


def drop_collinear(geom: BaseGeometry) -> BaseGeometry:
    """Remove collinear vertices left by old cuts.

    Example: the vertex at 180° of a polygon rejoined on both sides of the
    antimeridian. Zero tolerance does not modify the geometry.
    """
    return shapely.simplify(geom, 0)


def assemble(parts: list[BaseGeometry], dim: int, multi: bool) -> BaseGeometry:
    """Reconstruct a homogeneous geometry from simple components."""
    if dim == 2:
        merged = drop_collinear(unary_union(parts)) if parts else Polygon()
        polys = keep_dimension(merged, 2)
        if len(polys) == 1 and not multi:
            return polys[0]
        return MultiPolygon(polys)
    if dim == 1:
        merged = (
            drop_collinear(linemerge(unary_union(parts))) if parts else LineString()
        )
        lines = keep_dimension(merged, 1)
        if len(lines) == 1 and not multi:
            return lines[0]
        return MultiLineString(lines)
    raise ValueError(f"Unsupported dimension: {dim}")
