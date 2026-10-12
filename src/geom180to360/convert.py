"""Conversion of geometries from longitudes [-180, 180] to [0, 360].

In [-180, 180] the discontinuity is the antimeridian (±180°); in [0, 360]
it is on the Greenwich meridian (0°/360°). Simply shifting negative
longitudes by ``lon + 360`` breaks any geometry crossing Greenwich: a polygon
from -10° to 10° would become a polygon from 350° to 10° that would
cover the entire globe in the opposite direction.

This module handles this correctly:

* rings around a pole become caps (see :func:`geom180to360.polar.resolve_polar_rings`);
* the geometry is split at the 0° meridian;
* the western part (lon < 0) is shifted by +360°;
* the eastern part (lon >= 0) is preserved;
* the pieces are merged. An object previously split at the antimeridian
  (e.g., MULTIPOLYGON on both sides of ±180°) becomes contiguous again
  in [0, 360].

>>> convert_wkt("POINT (-90 45)")
'POINT (270 45)'
>>> convert_wkt("POLYGON ((-10 0, 10 0, 10 10, -10 10, -10 0))")
'MULTIPOLYGON (((350 0, 350 10, 360 10, 360 0, 350 0)), ((0 0, 0 10, 10 10, 10 0, 0 0)))'
"""

from __future__ import annotations

import shapely
from shapely import wkt as shapely_wkt
from shapely.geometry import GeometryCollection, MultiPoint, Point, box
from shapely.geometry.base import BaseGeometry

from ._geometry import EPS, assemble, keep_dimension, translate
from .polar import resolve_polar_rings

__all__ = ["convert_geometry", "convert_wkt", "shift_longitudes"]


def _check_longitudes(geom: BaseGeometry) -> None:
    """Check that all longitudes are within [-180, 180]."""
    if geom.is_empty:
        return
    minx, _, maxx, _ = geom.bounds
    if minx < -180 - EPS or maxx > 180 + EPS:
        raise ValueError(
            f"Longitudes outside the interval [-180, 180]: [{minx}, {maxx}]"
        )


def shift_longitudes(geom: BaseGeometry) -> BaseGeometry:
    """Shift each negative longitude by +360 without splitting the geometry.

    Preserves the structure (and vertex order), but is only correct if the
    geometry does not cross the Greenwich meridian.
    """

    def _transform(coords):
        coords = coords.copy()
        coords[:, 0] += 360.0 * (coords[:, 0] < 0)
        return coords

    return shapely.transform(geom, _transform, include_z=geom.has_z)


def convert_geometry(geom: BaseGeometry, split: bool = True) -> BaseGeometry:
    """Convert a shapely geometry from [-180, 180] to [0, 360].

    :param geom: geometry with longitudes in [-180, 180].
    :param split: if ``True`` (default), splits at the 0° meridian so that
        geometries crossing Greenwich remain correct, and transforms rings
        around a pole into caps. If ``False``, only applies the ``lon + 360``
        shift to negative longitudes (structure preserved).
    :return: the geometry with longitudes in [0, 360].
    :raises ValueError: if a longitude is outside [-180, 180].
    """
    _check_longitudes(geom)

    if geom.is_empty:
        return geom

    if geom.geom_type == "GeometryCollection":
        return GeometryCollection(
            [convert_geometry(g, split=split) for g in geom.geoms]
        )

    # Points have no extent: simple shift is enough.
    if not split or isinstance(geom, (Point, MultiPoint)):
        return shift_longitudes(geom)

    geom = resolve_polar_rings(geom)

    minx, miny, maxx, maxy = geom.bounds
    # Nothing crosses 0°: simple shift, structure is preserved.
    if minx >= 0:
        return geom
    if maxx <= 0:
        # Everything to the west: vertices at 0° also move to 360°.
        return translate(geom, 360.0)

    dim = shapely.get_dimensions(geom)
    multi = geom.geom_type.startswith("Multi")

    # Bandes englobantes avec une marge en latitude.
    west_box = box(-181, miny - 1, 0, maxy + 1)
    east_box = box(0, miny - 1, 181, maxy + 1)

    west = translate(geom.intersection(west_box), 360.0)
    east = geom.intersection(east_box)

    parts = keep_dimension(west, dim) + keep_dimension(east, dim)
    # normalize(): deterministic output (canonical vertex order).
    return assemble(parts, dim, multi).normalize()


def convert_wkt(wkt: str, split: bool = True, precision: int | None = None) -> str:
    """Convert a WKT string from [-180, 180] to [0, 360].

    :param wkt: geometry in WKT format.
    :param split: see :func:`convert_geometry`.
    :param precision: number of decimal places in output (``None`` = maximum
        precision, unnecessary zeros removed).
    :return: the converted geometry in WKT format.
    """
    result = convert_geometry(shapely_wkt.loads(wkt), split=split)
    rounding = -1 if precision is None else precision
    return shapely.to_wkt(result, rounding_precision=rounding, trim=True)
