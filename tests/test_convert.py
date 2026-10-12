"""Conversion [-180, 180] → [0, 360] (WKT and shapely geometries)."""

from __future__ import annotations

import pytest

from _helpers import load_wkt, same_geometry
from geom180to360 import convert_geometry, convert_wkt, shift_longitudes


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("POINT (-90 45)", "POINT (270 45)"),
        ("POINT (0 0)", "POINT (0 0)"),
        ("POINT (-180 0)", "POINT (180 0)"),
        ("POINT (180 0)", "POINT (180 0)"),
        ("POINT Z (-1 2 3)", "POINT Z (359 2 3)"),
        ("MULTIPOINT ((-10 0), (10 0))", "MULTIPOINT ((350 0), (10 0))"),
        ("LINESTRING (-170 0, -160 10)", "LINESTRING (190 0, 200 10)"),
        (
            "POLYGON ((10 0, 20 0, 20 10, 10 10, 10 0))",
            "POLYGON ((10 0, 20 0, 20 10, 10 10, 10 0))",
        ),
        (
            "POLYGON ((-20 0, -10 0, -10 10, -20 10, -20 0))",
            "POLYGON ((340 0, 350 0, 350 10, 340 10, 340 0))",
        ),
    ],
)
def test_simple_shift(src, expected):
    assert same_geometry(convert_wkt(src), expected)


def test_polygon_crossing_greenwich_is_split():
    out = convert_wkt("POLYGON ((-10 0, 10 0, 10 10, -10 10, -10 0))")
    assert same_geometry(
        out,
        "MULTIPOLYGON (((0 0, 10 0, 10 10, 0 10, 0 0)),"
        " ((350 0, 360 0, 360 10, 350 10, 350 0)))",
    )
    assert load_wkt(out).area == pytest.approx(200)


def test_polygon_touching_greenwich_from_west_goes_to_360():
    out = convert_wkt("POLYGON ((-10 0, 0 0, 0 10, -10 10, -10 0))")
    assert same_geometry(out, "POLYGON ((350 0, 360 0, 360 10, 350 10, 350 0))")


def test_polygon_with_hole_crossing_greenwich():
    src = (
        "POLYGON ((-10 -10, 10 -10, 10 10, -10 10, -10 -10),"
        " (-5 -5, 5 -5, 5 5, -5 5, -5 -5))"
    )
    out = load_wkt(convert_wkt(src))
    assert out.geom_type == "MultiPolygon"
    assert out.area == pytest.approx(load_wkt(src).area)
    assert out.bounds == (0, -10, 360, 10)


def test_antimeridian_split_polygon_is_merged():
    src = (
        "MULTIPOLYGON (((170 0, 180 0, 180 10, 170 10, 170 0)),"
        " ((-180 0, -170 0, -170 10, -180 10, -180 0)))"
    )
    assert same_geometry(
        convert_wkt(src), "MULTIPOLYGON (((170 0, 190 0, 190 10, 170 10, 170 0)))"
    )


def test_merged_polygon_has_no_leftover_vertex_at_180():
    src = (
        "MULTIPOLYGON (((170 -10, 180 -10, 180 10, 170 10, 170 -10)),"
        " ((-180 -10, -170 -10, -170 10, -180 10, -180 -10)),"
        " ((-10 -10, 10 -10, 10 10, -10 10, -10 -10)))"
    )
    out = load_wkt(convert_wkt(src))
    merged = next(p for p in out.geoms if p.bounds[0] == 170)
    assert len(merged.exterior.coords) == 5
    assert out.area == pytest.approx(load_wkt(src).area)


def test_linestring_crossing_greenwich():
    out = load_wkt(convert_wkt("LINESTRING (-10 0, 10 0)"))
    assert out.geom_type == "MultiLineString"
    assert out.length == pytest.approx(20)
    assert same_geometry(out, "MULTILINESTRING ((0 0, 10 0), (350 0, 360 0))")


def test_geometry_collection():
    out = convert_wkt("GEOMETRYCOLLECTION (POINT (-90 0), LINESTRING (-170 0, -160 0))")
    assert same_geometry(
        out, "GEOMETRYCOLLECTION (POINT (270 0), LINESTRING (190 0, 200 0))"
    )


def test_no_split_keeps_structure():
    out = convert_wkt("POLYGON ((-10 0, 10 0, 10 10, -10 10, -10 0))", split=False)
    assert out == "POLYGON ((350 0, 10 0, 10 10, 350 10, 350 0))"


def test_shift_longitudes_keeps_vertex_order():
    out = shift_longitudes(load_wkt("LINESTRING (-10 0, 10 0, -20 5)"))
    assert list(out.coords) == [(350, 0), (10, 0), (340, 5)]


def test_precision():
    assert convert_wkt("POINT (-170.123456789 1)", precision=3) == "POINT (189.877 1)"


@pytest.mark.parametrize(
    "src", ["POLYGON EMPTY", "POINT EMPTY", "GEOMETRYCOLLECTION EMPTY"]
)
def test_empty(src):
    assert convert_wkt(src) == src


@pytest.mark.parametrize("src", ["POINT (200 0)", "POINT (-180.5 0)"])
def test_out_of_range(src):
    with pytest.raises(ValueError, match=r"\[-180, 180\]"):
        convert_wkt(src)


@pytest.mark.parametrize(
    "src",
    [
        "POLYGON ((-150 -20, 150 -20, 150 20, -150 20, -150 -20))",
        "MULTIPOLYGON (((-10 0, 10 0, 10 5, -10 5, -10 0)), ((100 0, 110 0, 110 5, 100 5, 100 0)))",
        "POLYGON ((-180 -90, 180 -90, 180 90, -180 90, -180 -90))",
    ],
)
def test_area_is_preserved(src):
    geom = load_wkt(src)
    out = convert_geometry(geom)
    assert out.area == pytest.approx(geom.area)
    minx, _, maxx, _ = out.bounds
    assert 0 <= minx <= maxx <= 360
