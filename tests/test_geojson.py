"""Conversion of GeoJSON documents."""

from __future__ import annotations

import json

from shapely.geometry import shape

from _helpers import load_wkt
from geom180to360 import convert_geojson, geojson_geometry


def test_geometry():
    src = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[170, -10], [180, -10], [180, 10], [170, 10], [170, -10]]],
            [[[-180, -10], [-170, -10], [-170, 10], [-180, 10], [-180, -10]]],
            [[[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]]],
        ],
    }
    out = convert_geojson(src)
    assert out["type"] == "MultiPolygon"
    assert shape(out).equals(
        load_wkt(
            "MULTIPOLYGON (((170 -10, 190 -10, 190 10, 170 10, 170 -10)),"
            " ((350 -10, 360 -10, 360 10, 350 10, 350 -10)),"
            " ((0 -10, 10 -10, 10 10, 0 10, 0 -10)))"
        )
    )


def test_feature_collection_string_keeps_members():
    src = json.dumps(
        {
            "type": "FeatureCollection",
            "bbox": [-90, 45, -90, 45],
            "features": [
                {
                    "type": "Feature",
                    "id": 1,
                    "properties": {"name": "a"},
                    "geometry": {"type": "Point", "coordinates": [-90.123456, 45]},
                },
                {"type": "Feature", "properties": {}, "geometry": None},
            ],
        }
    )
    out = json.loads(convert_geojson(src, precision=2))
    feat = out["features"][0]
    assert feat["geometry"] == {"type": "Point", "coordinates": [269.88, 45.0]}
    assert feat["properties"] == {"name": "a"}
    assert feat["id"] == 1
    assert out["features"][1]["geometry"] is None
    assert out["bbox"] == [269.88, 45.0, 269.88, 45.0]


def test_input_is_not_modified():
    src = {"type": "Point", "coordinates": [-90, 45]}
    convert_geojson(src)
    assert src == {"type": "Point", "coordinates": [-90, 45]}


def test_geojson_geometry():
    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Point", "coordinates": [1, 2]},
            },
            {"type": "Feature", "properties": {}, "geometry": None},
        ],
    }
    geom = geojson_geometry(doc)
    assert geom.geom_type == "GeometryCollection"
    assert geom.bounds == (1, 2, 1, 2)
