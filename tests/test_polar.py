"""Rings around a pole."""

from __future__ import annotations

import pytest

from _helpers import load_wkt
from geom180to360 import convert_wkt, resolve_polar_rings
from geom180to360.polar import _encircled_pole, _polar_winding


@pytest.mark.parametrize(
    ("coords", "winding"),
    [
        ([(0, 80), (90, 80), (180, 80), (-90, 80), (0, 80)], 360),
        ([(0, 80), (-90, 80), (180, 80), (90, 80), (0, 80)], -360),
        ([(-10, 0), (10, 0), (10, 5), (-10, 5), (-10, 0)], 0),
        # Crosses the antimeridian without going around the pole.
        ([(170, 0), (-170, 0), (-170, 10), (170, 10), (170, 0)], 0),
    ],
)
def test_polar_winding(coords, winding):
    assert _polar_winding(coords) == pytest.approx(winding)


@pytest.mark.parametrize(
    ("src", "pole"),
    [
        ("POLYGON ((0 80, 90 75, 180 80, -90 85, 0 80))", 90),
        # Traversed westward: the pole is chosen by mean latitude.
        ("POLYGON ((0 80, -90 80, 180 80, 90 80, 0 80))", 90),
        ("POLYGON ((-10 -70, -100 -65, 170 -70, 80 -75, -10 -70))", -90),
        # Equator: traversal direction decides.
        ("POLYGON ((0 5, 90 -5, 180 5, -90 -5, 0 5))", 90),
        ("POLYGON ((0 5, -90 -5, 180 5, 90 -5, 0 5))", -90),
        # Already a cap in the plane (vertex at pole): not concerned.
        ("POLYGON ((-180 70, 0 70, 180 70, 180 90, -180 90, -180 70))", None),
        ("POLYGON ((-10 0, 10 0, 10 5, -10 5, -10 0))", None),
    ],
)
def test_encircled_pole(src, pole):
    assert _encircled_pole(load_wkt(src).exterior) == pole


def test_polar_ring_becomes_cap():
    out = load_wkt(convert_wkt("POLYGON ((0 80, 90 80, 180 80, -90 80, 0 80))"))
    assert out.geom_type == "Polygon"
    assert out.bounds == (0, 80, 360, 90)
    assert out.area == pytest.approx(360 * 10)


def test_south_polar_ring_becomes_cap():
    out = load_wkt(convert_wkt("POLYGON ((0 -70, -90 -70, 180 -70, 90 -70, 0 -70))"))
    assert out.bounds == (0, -90, 360, -70)
    assert out.area == pytest.approx(360 * 20)


def test_polar_ring_hole_crossing_antimeridian_is_kept():
    out = load_wkt(
        convert_wkt(
            "POLYGON ((0 80, 90 80, 180 80, -90 80, 0 80),"
            " (170 82, -170 82, -170 85, 170 85, 170 82))"
        )
    )
    assert out.area == pytest.approx(360 * 10 - 20 * 3)
    assert not out.contains(load_wkt("POINT (180 83)"))
    assert out.contains(load_wkt("POINT (100 83)"))


def test_resolve_polar_rings_in_multipolygon():
    src = load_wkt(
        "MULTIPOLYGON (((0 80, 90 80, 180 80, -90 80, 0 80)),"
        " ((-10 -5, 10 -5, 10 5, -10 5, -10 -5)))"
    )
    out = resolve_polar_rings(src)
    assert out.geom_type == "MultiPolygon"
    assert out.area == pytest.approx(360 * 10 + 20 * 10)


@pytest.mark.parametrize(
    "src",
    [
        "POLYGON ((-180 70, 0 70, 180 70, 180 90, -180 90, -180 70))",
        "POLYGON ((170 0, -170 0, -170 10, 170 10, 170 0))",
        "POLYGON ((-10 -10, 10 -10, 10 10, -10 10, -10 -10))",
        "LINESTRING (0 80, 90 80, 180 80, -90 80, 0 80)",
        "POINT (0 0)",
        "POLYGON EMPTY",
    ],
)
def test_resolve_polar_rings_leaves_other_geometries(src):
    geom = load_wkt(src)
    assert resolve_polar_rings(geom).equals(geom)


def test_no_split_ignores_polar_rings():
    src = "POLYGON ((0 80, 90 80, 180 80, -90 80, 0 80))"
    assert (
        convert_wkt(src, split=False) == "POLYGON ((0 80, 90 80, 180 80, 270 80, 0 80))"
    )
