"""Conversion of GeoJSON documents (geometry, Feature, FeatureCollection)."""

from __future__ import annotations

import json
from typing import Any

import shapely
from shapely.geometry import GeometryCollection, mapping, shape
from shapely.geometry.base import BaseGeometry

from .convert import convert_geometry

__all__ = ["convert_geojson", "geojson_geometry"]


def _round_coords(geom: BaseGeometry, precision: int) -> BaseGeometry:
    return shapely.transform(geom, lambda c: c.round(precision), include_z=geom.has_z)


def _convert_geometry_obj(
    obj: dict[str, Any] | None, split: bool, precision: int | None
) -> dict[str, Any] | None:
    if obj is None:  # Feature without geometry
        return None
    result = convert_geometry(shape(obj), split=split)
    if precision is not None:
        result = _round_coords(result, precision)
    return json.loads(json.dumps(mapping(result)))  # tuples -> listes


def _convert_obj(
    obj: dict[str, Any], split: bool, precision: int | None
) -> dict[str, Any]:
    kind = obj.get("type")
    if kind == "FeatureCollection":
        out = dict(obj)
        out["features"] = [_convert_obj(f, split, precision) for f in obj["features"]]
    elif kind == "Feature":
        out = dict(obj)
        out["geometry"] = _convert_geometry_obj(obj.get("geometry"), split, precision)
    else:
        out = _convert_geometry_obj(obj, split, precision)
    if "bbox" in obj:
        out["bbox"] = _bbox(out)
    return out


def _bbox(obj: dict[str, Any]) -> list[float] | None:
    """Recalculate the bbox (the old one is in [-180, 180])."""
    geom = geojson_geometry(obj)
    return None if geom.is_empty else list(geom.bounds)


def geojson_geometry(obj: dict[str, Any]) -> BaseGeometry:
    """Combine geometries from a GeoJSON object into a single geometry.

    :param obj: geometry, ``Feature``, or ``FeatureCollection``.
    :return: the geometry (``GeometryCollection`` for a collection).
    """
    kind = obj.get("type")
    if kind == "FeatureCollection":
        return GeometryCollection([geojson_geometry(f) for f in obj["features"]])
    if kind == "Feature":
        geom = obj.get("geometry")
        return GeometryCollection() if geom is None else shape(geom)
    return shape(obj)


def convert_geojson(
    geojson: str | dict[str, Any],
    split: bool = True,
    precision: int | None = None,
) -> str | dict[str, Any]:
    """Convert a GeoJSON object from [-180, 180] to [0, 360].

    Accepts a geometry, a ``Feature``, or a ``FeatureCollection``. Properties
    and other members are preserved; any ``bbox`` is recalculated.

    :param geojson: GeoJSON object (``dict``) or its JSON serialization.
    :param split: see :func:`geom180to360.convert_geometry`.
    :param precision: number of decimal places for coordinates (``None`` = no
        rounding).
    :return: same form as input (``dict`` or JSON string).
    """
    if isinstance(geojson, str):
        return json.dumps(_convert_obj(json.loads(geojson), split, precision))
    return _convert_obj(geojson, split, precision)
