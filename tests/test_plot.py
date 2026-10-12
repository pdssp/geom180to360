"""Visualization on sphere (smoke test: the figure is produced without error)."""

from __future__ import annotations

import numpy as np
import pytest

from _helpers import SAMPLES_DIR, load_sample, load_wkt
from geom180to360 import geojson_geometry
from geom180to360.__main__ import run

pytestmark = [pytest.mark.plot, pytest.mark.usefixtures("plot_backend")]


def test_plot_conversion(tmp_path):
    from geom180to360 import plot_conversion

    out = tmp_path / "sphere.png"
    src = load_wkt(
        "GEOMETRYCOLLECTION ("
        "POLYGON ((-10 0, 10 0, 10 10, -10 10, -10 0), (-2 2, 2 2, 2 5, -2 5, -2 2)),"
        " LINESTRING (-170 40, 170 40), POINT (-90 0))"
    )
    plot_conversion(src, output=str(out))
    assert out.stat().st_size > 0



def test_plot_polar_sample(tmp_path):
    from geom180to360 import plot_conversion

    doc = load_sample(SAMPLES_DIR / "32_anneau_nord_trou_antimeridien.geojson")
    out = tmp_path / "polar.png"
    plot_conversion(geojson_geometry(doc), output=str(out))
    assert out.stat().st_size > 0


def test_cli_plot_output(tmp_path, capsys):
    out = tmp_path / "sphere.png"
    args = [
        "--plot-output",
        str(out),
        "--view",
        "0",
        "30",
        "POINT (-90 45)",
    ]
    with pytest.raises(SystemExit) as excinfo:
        run(args)
    assert excinfo.value.code == 0
    assert capsys.readouterr().out == "POINT (270 45)\n"
    assert out.stat().st_size > 0


def test_cli_plot_window_error_is_reported(monkeypatch, capsys):
    """No window possible (Tcl/Tk absent, etc.): clear message, code 1."""

    def broken(*args, **kwargs):
        raise RuntimeError("Can't find a usable init.tcl\nmore details")

    monkeypatch.setattr("geom180to360.plot.plot_conversion", broken)
    with pytest.raises(SystemExit) as excinfo:
        run(["--plot", "POINT (-90 45)"])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == "POINT (270 45)\n"
    assert "--plot-output" in captured.err
    assert "init.tcl" in captured.err


@pytest.mark.parametrize("start", [180, 0])
def test_compass_follows_mouse_rotation(start):
    """After a 180° mouse rotation, E stays on the east side."""
    import matplotlib.pyplot as plt
    from matplotlib.backend_bases import MouseEvent
    from mpl_toolkits.mplot3d import proj3d

    from geom180to360 import plot_sphere
    from geom180to360.plot import _lonlat_to_xyz

    geom = geojson_geometry(load_sample(SAMPLES_DIR / "06_antimeridien_coupe.geojson"))
    ax = plot_sphere(geom, view=(start, 0))
    fig = ax.figure
    fig.canvas.draw()

    new = (start + 180) % 360
    ax.view_init(elev=0, azim=new)  # what the mouse rotation does
    fig.canvas.callbacks.process(
        "button_release_event", MouseEvent("button_release_event", fig.canvas, 0, 0)
    )
    fig.canvas.draw()

    def screen_x(xyz):
        return proj3d.proj_transform(*xyz, ax.get_proj())[0]

    labels = {t.get_text(): t for t in ax.texts}
    east_label = screen_x(labels["E"].get_position_3d())
    west_label = screen_x(labels["W"].get_position_3d())
    assert east_label > 0 > west_label
    # The meridian new + 60° is correctly on the E side.
    assert screen_x(_lonlat_to_xyz(new + 60, 0)) > 0
    plt.close(fig)


@pytest.mark.parametrize(
    ("azim", "elev", "roll"),
    [(180, 0, 0), (0, 0, 0), (180, 120, 0), (0, -150, 0), (180, 10, 180), (30, 20, 60)],
)
def test_compass_matches_geography_for_any_view(azim, elev, roll):
    """E/N on true east/north sides, even upside-down or beyond a pole."""
    import matplotlib.pyplot as plt
    from matplotlib.backend_bases import MouseEvent
    from mpl_toolkits.mplot3d import proj3d

    from geom180to360 import plot_sphere
    from geom180to360.plot import _lonlat_to_xyz, _view_center

    ax = plot_sphere(load_wkt("POINT (0 0)"), view=(0, 0))
    fig = ax.figure
    ax.view_init(elev=elev, azim=azim, roll=roll)
    fig.canvas.callbacks.process(
        "button_release_event", MouseEvent("button_release_event", fig.canvas, 0, 0)
    )
    fig.canvas.draw()

    def screen(xyz):
        return np.array(proj3d.proj_transform(*xyz, ax.get_proj())[:2])

    lon, lat = _view_center(azim, elev)
    center = screen(_lonlat_to_xyz(lon, lat))
    east = screen(_lonlat_to_xyz(lon + 20, lat)) - center
    north = screen(_lonlat_to_xyz(lon, lat + 20 if lat < 70 else 89)) - center
    labels = {t.get_text(): screen(t.get_position_3d()) - center for t in ax.texts}
    assert np.dot(east, labels["E"]) > 0
    assert np.dot(north, labels["N"]) > 0
    assert (ax.azim, ax.elev, ax.roll) == pytest.approx((azim, elev, roll))
    plt.close(fig)


def test_globe_rotation_style():
    import matplotlib

    from geom180to360 import plot_sphere

    if "axes3d.mouserotationstyle" not in matplotlib.rcParams:
        pytest.skip("matplotlib < 3.10")
    plot_sphere(load_wkt("POINT (0 0)"))
    assert matplotlib.rcParams["axes3d.mouserotationstyle"] == "azel"
