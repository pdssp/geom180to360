"""Display of lon/lat geometries on a 3D sphere (matplotlib).

Visual control tool: matplotlib is only imported when the functions are called
(optional dependency ``geom180to360[plot]``).
"""

from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry

from .geometry_utils import get_dimension
from .convert import convert_geometry
from .polar import resolve_polar_rings

__all__ = ["plot_conversion", "plot_sphere"]

_SPHERE_STEP = 2.0  # step (degrees) for sphere mesh and filling


def _lonlat_to_xyz(lon, lat, r: float = 1.0):
    lon, lat = np.broadcast_arrays(np.radians(lon), np.radians(lat))
    return (
        r * np.cos(lat) * np.cos(lon),
        r * np.cos(lat) * np.sin(lon),
        r * np.sin(lat),
    )


def _densify(coords, step: float = 1.0):
    """Interpole les segments (droits en lon/lat) avec un pas <= ``step``."""
    coords = np.asarray(coords)[:, :2]
    out = [coords[:1]]
    for a, b in zip(coords[:-1], coords[1:], strict=True):
        n = max(1, int(np.ceil(np.abs(b - a).max() / step)))
        t = np.linspace(0, 1, n + 1)[1:, None]
        out.append(a + (b - a) * t)
    return np.vstack(out)


def _view_center(azim: float, elev: float) -> tuple[float, float]:
    """Point (lon, lat) at the center of the view.

    An elevation beyond ±90° (view passing over a pole) aims at the point
    ``(azim + 180, ±180 - elev)``: we convert back to geographic coordinates
    so that N, S, E, W remain correct.
    """
    x, y, z = _view_vector(azim, elev)
    return float(np.degrees(np.arctan2(y, x))), float(np.degrees(np.arcsin(z)))


def _view_vector(azim: float, elev: float):
    return np.array(_lonlat_to_xyz(azim, elev))


def _hide_back(x, y, z, view):
    """Mask (NaN) points from the hidden hemisphere."""
    x, y, z = (np.array(v, dtype=float) for v in (x, y, z))
    back = x * view[0] + y * view[1] + z * view[2] < 0
    x[back] = y[back] = z[back] = np.nan
    return x, y, z


def _default_view(geom: BaseGeometry) -> tuple[float, float]:
    """Viewpoint centered on the geometry (average of unit vectors)."""
    coords = shapely.get_coordinates(shapely.segmentize(geom, 5.0))
    if len(coords) == 0:
        return 0.0, 20.0
    x, y, z = _lonlat_to_xyz(coords[:, 0], coords[:, 1])
    v = np.array([x.mean(), y.mean(), z.mean()])
    if np.linalg.norm(v) < 1e-6:
        return float(coords[:, 0].mean()), 20.0
    lon = np.degrees(np.arctan2(v[1], v[0]))
    lat = np.degrees(np.arcsin(v[2] / np.linalg.norm(v)))
    return float(lon), float(lat)


def _fill_pieces(geom: BaseGeometry):
    """Split surfaces along a fine grid to place them on the sphere.

    Each piece is small: the 3D polygon connecting its vertices stays
    attached to the sphere (a large flat face would pass through it).
    """
    polys = get_dimension(geom, 2)
    if not polys:
        return []
    minx, miny, maxx, maxy = geom.bounds
    xs = np.arange(np.floor(minx / _SPHERE_STEP) * _SPHERE_STEP, maxx, _SPHERE_STEP)
    ys = np.arange(np.floor(miny / _SPHERE_STEP) * _SPHERE_STEP, maxy, _SPHERE_STEP)
    gx, gy = np.meshgrid(xs, ys)
    cells = shapely.box(gx, gy, gx + _SPHERE_STEP, gy + _SPHERE_STEP).ravel()
    pieces = []
    for poly in polys:
        for piece in shapely.intersection(poly, cells):
            for p in get_dimension(piece, 2):
                if p.interiors:  # hole smaller than a grid cell
                    pieces.extend(
                        get_dimension(shapely.constrained_delaunay_triangles(p), 2)
                    )
                else:
                    pieces.append(p)
    return pieces


def _plot_compass(ax, azim: float, elev: float) -> None:
    """Write N, S, E, W at the disk edge, according to local directions
    at the center of the view (E: increasing longitudes)."""
    lon, lat = np.radians(azim), np.radians(elev)
    north = np.array(
        [-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)]
    )
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    for label, d in (("N", north), ("S", -north), ("E", east), ("W", -east)):
        x, y, z = 1.12 * d
        ax.text(
            x,
            y,
            z,
            label,
            color="0.25",
            fontsize=11,
            fontweight="bold",
            ha="center",
            va="center",
        )
    # Visible poles.
    view = _view_vector(azim, elev)
    for label, z in (("NP", 1.0), ("SP", -1.0)):
        if z * view[2] > 0:
            ax.scatter([0], [0], [1.01 * z], color="0.25", s=12, depthshade=False)
            ax.text(
                0,
                0,
                1.06 * z,
                label,
                color="0.25",
                fontsize=8,
                ha="center",
                va="bottom" if z > 0 else "top",
            )


def plot_sphere(
    geom: BaseGeometry,
    ax=None,
    view: tuple[float, float] | None = None,
    cut_meridian: float | None = None,
    color: str = "tab:orange",
    title: str | None = None,
):
    """Draw a lon/lat geometry (in degrees) on a 3D sphere.

    Longitudes are interpreted as is (convention [-180, 180] or [0, 360]):
    filling is calculated in the lon/lat plane, as shapely does. A poorly
    converted geometry will therefore appear incorrect.

    :param geom: geometry to draw.
    :param ax: 3D matplotlib axes (created if ``None``).
    :param view: viewpoint ``(lon, lat)``; defaults to centered on ``geom``.
    :param cut_meridian: discontinuity meridian to highlight.
    :param color: color of surfaces, lines, and points.
    :param title: axes title.
    :return: the matplotlib axes.

    In an interactive window, the sphere is redrawn when the mouse is released
    after rotating it: hidden face and cardinal points then follow the new view.
    """
    import matplotlib
    import matplotlib.pyplot as plt

    # "Globe" rotation: dragging horizontally rotates around the poles axis,
    # vertically changes the latitude. The "arcball" style (default since
    # matplotlib 3.10) causes the globe to flip upside down.
    if "axes3d.mouserotationstyle" in matplotlib.rcParams:
        matplotlib.rcParams["axes3d.mouserotationstyle"] = "azel"

    if ax is None:
        ax = plt.figure(figsize=(6, 6)).add_subplot(projection="3d")
    azim, elev = view if view is not None else _default_view(geom)

    def draw(azim: float, elev: float, roll: float = 0.0) -> None:
        _draw_sphere(ax, geom, azim, elev, roll, cut_meridian, color, title)

    draw(azim, elev)
    _follow_rotation(ax, draw)
    return ax


def _follow_rotation(ax, draw) -> None:
    """Redraw the axes for the new view after mouse rotation.

    Elements are positioned in 3D for a given view (hidden face masked,
    N/S/E/W at disk edge): without redraw, a 180° rotation would show E
    on the left and the back face.
    """
    drawn = {"view": (ax.azim, ax.elev, ax.roll)}

    def on_release(event) -> None:
        view = (ax.azim, ax.elev, ax.roll)
        if np.allclose(view, drawn["view"]):
            return
        drawn["view"] = view
        ax.cla()
        draw(*view)
        ax.figure.canvas.draw_idle()

    ax.figure.canvas.mpl_connect("button_release_event", on_release)


def _draw_sphere(
    ax,
    geom: BaseGeometry,
    azim: float,
    elev: float,
    roll: float,
    cut_meridian: float | None,
    color: str,
    title: str | None,
) -> None:
    """Draw the sphere and geometry for view ``(azim, elev, roll)``."""
    from matplotlib.colors import to_rgba
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    v = _view_vector(azim, elev)
    ax.computed_zorder = False  # explicit draw order: sphere, then above

    # Sphere lit from top left of the view.
    lon = np.arange(-180, 180 + _SPHERE_STEP, _SPHERE_STEP)
    lat = np.arange(-90, 90 + _SPHERE_STEP, _SPHERE_STEP)
    glon, glat = np.meshgrid(lon, lat)
    x, y, z = _lonlat_to_xyz(glon, glat)
    center_lon, center_lat = _view_center(azim, elev)
    light = _view_vector(center_lon - 40, center_lat + 40)
    shade = np.clip(x * light[0] + y * light[1] + z * light[2], 0, 1)
    base = np.array(to_rgba("#dce6f0"))
    colors = base * (0.55 + 0.45 * shade[..., None])
    colors[..., 3] = 1
    ax.plot_surface(
        x, y, z, facecolors=colors, shade=False, linewidth=0, antialiased=False
    )

    # Graticule every 30°.
    for m in range(-180, 180, 30):
        gx, gy, gz = _hide_back(*_lonlat_to_xyz(m, np.linspace(-90, 90, 91), 1.002), v)
        ax.plot(gx, gy, gz, color="0.6", lw=0.4)
    for p in range(-60, 90, 30):
        gx, gy, gz = _hide_back(
            *_lonlat_to_xyz(np.linspace(-180, 180, 181), p, 1.002), v
        )
        ax.plot(gx, gy, gz, color="0.6", lw=0.4)
    if cut_meridian is not None:
        gx, gy, gz = _hide_back(
            *_lonlat_to_xyz(cut_meridian, np.linspace(-90, 90, 181), 1.003), v
        )
        ax.plot(gx, gy, gz, color="crimson", lw=1.2, ls="--")

    # Surfaces.
    faces = []
    for piece in _fill_pieces(geom):
        c = _densify(piece.exterior.coords, _SPHERE_STEP / 2)
        fx, fy, fz = _lonlat_to_xyz(c[:, 0], c[:, 1], 1.004)
        if np.mean(fx * v[0] + fy * v[1] + fz * v[2]) > 0:
            faces.append(np.column_stack([fx, fy, fz]))
    if faces:
        ax.add_collection3d(
            Poly3DCollection(faces, facecolor=to_rgba(color, 0.55), edgecolor="none")
        )

    # Contours et lignes.
    rings = []
    for poly in get_dimension(geom, 2):
        rings.extend([poly.exterior, *poly.interiors])
    rings.extend(get_dimension(geom, 1))
    for ring in rings:
        c = _densify(ring.coords)
        ax.plot(
            *_hide_back(*_lonlat_to_xyz(c[:, 0], c[:, 1], 1.005), v),
            color=color,
            lw=1.5,
        )

    # Points.
    pts = [g for g in get_dimension(geom, 0)]
    if pts:
        c = np.array([(p.x, p.y) for p in pts])
        px, py, pz = _hide_back(*_lonlat_to_xyz(c[:, 0], c[:, 1], 1.006), v)
        ax.scatter(px, py, pz, color=color, s=20, depthshade=False)

    _plot_compass(ax, center_lon, center_lat)
    ax.view_init(elev=elev, azim=azim, roll=roll)
    ax.set_box_aspect((1, 1, 1))
    lim = 0.75
    ax.set(xlim=(-lim, lim), ylim=(-lim, lim), zlim=(-lim, lim))
    ax.set_axis_off()
    if title:
        ax.set_title(title)


def plot_conversion(
    src: BaseGeometry,
    dst: BaseGeometry | None = None,
    output: str | None = None,
    view: tuple[float, float] | None = None,
    split: bool = True,
):
    """Display a geometry [-180, 180] and its conversion [0, 360] on the sphere.

    Two columns (input, output) and two rows (view and its opposite in
    longitude) to see the entire globe.

    :param src: input geometry (longitudes in [-180, 180]).
    :param dst: converted geometry (calculated if ``None``).
    :param output: image file (png, svg, pdf, etc.); ``None`` = window.
    :param view: viewpoint ``(lon, lat)``; defaults to centered on ``dst``.
    :param split: see :func:`convert_geometry` (if ``dst`` is calculated).
    :return: the matplotlib figure.
    """
    import matplotlib

    if output:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if dst is None:
        dst = convert_geometry(src, split=split)
    if view is None:
        view = _default_view(dst)
    # A polar ring has no meaning in the plane: we show its cap.
    if split:
        src = resolve_polar_rings(src)
    lon, lat = view
    views = [(lon, lat), ((lon + 180) % 360, lat)]
    fig = plt.figure(figsize=(10, 10))
    for row, (vlon, vlat) in enumerate(views):
        label = f"view lon {round(vlon)}°, lat {round(vlat)}°"
        plot_sphere(
            src,
            fig.add_subplot(2, 2, 2 * row + 1, projection="3d"),
            view=(vlon, vlat),
            cut_meridian=180,
            color="tab:blue",
            title=f"Input [-180, 180] — cut ±180°\n{label}",
        )
        plot_sphere(
            dst,
            fig.add_subplot(2, 2, 2 * row + 2, projection="3d"),
            view=(vlon, vlat),
            cut_meridian=0,
            color="tab:orange",
            title=f"Output [0, 360] — cut 0°\n{label}"
        )
    fig.tight_layout()
    if output:
        fig.savefig(output, dpi=120)
        plt.close(fig)
    else:
        plt.show()
    return fig
