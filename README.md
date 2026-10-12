# geom180to360

[![image](https://img.shields.io/badge/Maintained%3F-yes-green.svg)]()

![image]()

Conversion tool of geometries from longitudes [-180, 180] to [0, 360]

## Purpose

In [-180, 180], the discontinuity is the antimeridian (±180°). In [0, 360],
it is on the Greenwich meridian (0°/360°). Simply adding 360 to negative
longitudes breaks any geometry crossing 0°: a polygon from -10° to 10°
would become a polygon from 350° to 10°, wrapping around the globe in the
opposite direction.

The program proceeds in four steps:

1. it splits the geometry at the 0° meridian;
2. it shifts the western part (lon < 0) by +360°;
3. it keeps the eastern part (lon ≥ 0) as is;
4. it merges the pieces. An object already split at the antimeridian, for
   example a `MULTIPOLYGON` on both sides of ±180°, becomes contiguous again.

### Rings around a pole

A polar footprint is often described by a ring that goes around the pole
without having a vertex at ±90°, for example
`POLYGON ((0 80, 90 75, 180 80, -90 85, 0 80))`. In the lon/lat plane, this
ring has no meaning: it forms a band with no thickness or that overlaps itself.
The program recognizes it and transforms it before conversion:

1. **Detection**: it sums the longitude differences between consecutive vertices,
   each taken along the shortest path. The sum is 0 for an ordinary ring and
   ±360° for a ring that goes around a pole.
2. **Pole selection**: it is the pole of the hemisphere of the ring's mean
   latitude, regardless of the traversal direction. If the mean latitude is zero,
   the traversal direction decides: eastward is the North Pole.
3. **Cap**: the area between the ring and the pole becomes a polygon closed at
   the pole. Any holes are preserved, even if they cross ±180°.

```bash
$ geom180to360 "POLYGON ((0 80, 90 75, 180 80, -90 85, 0 80))"
POLYGON ((0 80, 0 90, 360 90, 360 80, 270 85, 90 75, 0 80))
```

Conditions and limitations:
- two consecutive vertices must be less than 180° of longitude from each other,
  otherwise the segment direction is ambiguous;
- a polygon that already has a vertex at the pole, for example
  `box(-180, 70, 180, 90)`, is considered as a cap already described in the
  plane and is not modified;
- detection only applies to polygons, and not with `--no-split`.

In Python, the `resolve_polar_rings(geom)` function performs this step alone.

## Stable release

To install geom180to360, run this command in your
terminal:

``` console
$ pip install git+https://gitlab.cnes.fr/pdssp/common/geom180to360.git
```

This is the preferred method to install geom180to360,
as it will always install the most recent stable release.

If you don\'t have [pip](https://pip.pypa.io) installed, this [Python
installation
guide](http://docs.python-guide.org/en/latest/starting/installation/)
can guide you through the process.

## Installing UV

To manage the dependencies of geom180to360, we use
[UV](<https://docs.astral.sh/uv/>). If you don\'t have UV
installed, follow these steps:

1.  **Install UV**:

    > ``` shell
    > $ curl -LsSf https://astral.sh/uv/install.sh | sh
    > ```

2.  **Verify the installation**:

    > ``` console
    > $ uv --version
    > ```

Please note that this project has been tested with UV version 0.9.15.

## From sources

The sources for geom180to360 can be downloaded from
the [Gitlab repo]().

You can either clone the public repository:

``` console
$ git clone https://gitlab.cnes.fr/pdssp/common/geom180to360.git
```

Or download the
[tarball]():

``` console
$ curl -OJL https://gitlab.cnes.fr/pdssp/common/geom180to360/tarball/main
```

Once you have a copy of the source, you can install it with:

``` console
$ make  # install
```

## Development

``` console
$ git clone https://gitlab.cnes.fr/pdssp/common/geom180to360.git
$ cd geom180to360
$ make prepare-dev
$ source .venv/bin/activate
$ make install-dev
```

To get more information about the preconfigured tasks:

``` console
$ make help
```

## Project structure

```
pyproject.toml       metadata, dependencies, pytest configuration, etc.
uv.lock              frozen dependency versions (uv)
src/geom180to360/
    __init__.py      Public API
    __main__.py      Command Line Interface
    convert.py       conversion [-180, 180] → [0, 360] (WKT, shapely)
    polar.py         rings around a pole
    geojson.py       GeoJSON documents
    plot.py          sphere visualization (matplotlib)
tests/
    data/samples/    GeoJSON samples
    test_*.py        pytest tests
```

## Usage

### CLI 

#### Parameters 
| Option | Role |
|---|---|
| `WKT …` | One or more geometries passed as arguments |
| `-i, --input FILE` | Input file (WKT: one geometry per line) |
| `-o, --output FILE` | Output file (default: standard output) |
| `--no-split` | Do not split at 0° meridian (simple `lon + 360`) |
| `-p, --precision N` | Number of decimal places in output |
| `--geojson` | Input and output are in GeoJSON |
| `--plot` | Display input and output on a 3D sphere (matplotlib) |
| `--plot-output IMAGE` | Like `--plot`, but saves the figure (png, svg, pdf, etc.) |
| `--view LON LAT` | Figure viewpoint (default: centered on geometry) |
| `--version` | Package version |
| `-h, --help` | Help |

Without arguments or `--input`, the program reads standard input.

#### WKT Conversion

```bash
# One or more geometries as arguments
$ geom180to360 "POINT (-90 45)" "LINESTRING (-170 0, -160 10)"
POINT (270 45)
LINESTRING (190 0, 200 10)

# A geometry crossing Greenwich is split at 0°/360°
$ geom180to360 "POLYGON ((-10 0, 10 0, 10 10, -10 10, -10 0))"
MULTIPOLYGON (((350 0, 350 10, 360 10, 360 0, 350 0)), ((0 0, 0 10, 10 10, 10 0, 0 0)))

# An object split at the antimeridian is reunited
$ geom180to360 "MULTIPOLYGON (((170 0, 180 0, 180 10, 170 10, 170 0)), ((-180 0, -170 0, -170 10, -180 10, -180 0)))"
MULTIPOLYGON (((170 0, 170 10, 190 10, 190 0, 170 0)))
```

#### Files and standard input

In WKT, input contains one geometry per line. Empty lines and lines
starting with `#` are ignored.

```bash
geom180to360 -i shapes.wkt -o shapes_360.wkt
cat shapes.wkt | geom180to360 > shapes_360.wkt
```

```bash
$ printf '# commentaire\nPOINT (-90 45)\nPOINT (10 5)\n' | geom180to360
POINT (270 45)
POINT (10 5)
```

#### Precision

```bash
$ geom180to360 -p 3 "POINT (-170.123456789 1)"
POINT (189.877 1)
```

#### Without splitting (`--no-split`)

This option preserves vertex structure and order. It is only correct if the
geometry **does not cross** the 0° meridian.

```bash
$ geom180to360 --no-split "POLYGON ((-10 0, 10 0, 10 10, -10 10, -10 0))"
POLYGON ((350 0, 10 0, 10 10, 350 10, 350 0))      # wrong: covers 10° → 350°
```

#### GeoJSON

With `--geojson`, each argument is a complete GeoJSON document. With
`--input` or standard input, the entire content forms a document. A document
can be a geometry, a `Feature`, or a `FeatureCollection`. Properties and other
members are preserved, and any `bbox` is recalculated.

```bash
geom180to360 --geojson -i examples/shape.geojson -o shape_360.geojson
geom180to360 --geojson -p 6 < examples/shape.geojson
```

### Python usage 

To use geom180to360 in a project:

```python
from shapely import wkt
from geom180to360 import (
    convert_wkt,
    convert_geojson,
    convert_geometry,
    shift_longitudes,
    geojson_geometry,
    plot_sphere,
    plot_conversion,
)

convert_wkt("POINT (-90 45)")  # 'POINT (270 45)'
convert_wkt("POINT (-170.123456789 1)", precision=3)  # 'POINT (189.877 1)'
convert_geojson({"type": "Point", "coordinates": [-90, 45]})  # dict ou str

geom = convert_geometry(wkt.loads("POLYGON ((-10 0, 10 0, 10 10, -10 10, -10 0))"))

shift_longitudes(geom)  # lon + 360 sur les longitudes négatives, sans découpage

plot_conversion(wkt.loads("LINESTRING (-10 0, 10 5)"), output="fig.png")
plot_sphere(geom)  # une seule sphère
```

| Function | Role |
|---|---|
| `convert_wkt(wkt, split=True, precision=None)` | WKT [-180, 180] → WKT [0, 360] |
| `convert_geojson(obj, split=True, precision=None)` | GeoJSON (`dict` or `str`) → same type |
| `convert_geometry(geom, split=True)` | Shapely geometry → Shapely geometry |
| `shift_longitudes(geom)` | Simple `lon + 360` on negative longitudes, without splitting |
| `resolve_polar_rings(geom)` | Replace rings around a pole with their cap (in [-180, 180]) |
| `geojson_geometry(obj)` | Shapely geometry from a GeoJSON document (Feature, FeatureCollection, etc.) |
| `plot_sphere(geom, …)` | Draw a geometry on a 3D sphere |
| `plot_conversion(src, dst=None, output=None, view=None, split=True)` | Input/output figure |

### Errors

A longitude outside [-180, 180] in input causes an error. On the command line,
the program reports the error to standard error, moves to the next geometry,
and exits with code 1:

```bash
$ geom180to360 "POINT (200 0)"
Error geometry no. 1: Longitudes outside the interval [-180, 180]: [200.0, 200.0]
```

## Run tests

```bash
$ make tests
$ uv run pytest -m "not plot"          # without visualization tests
```
| File | Content |
|---|---|
| `test_convert.py` | WKT/shapely conversion: Greenwich, antimeridian, holes, precision, errors, area preservation |
| `test_polar.py` | polar ring detection, pole selection, caps, holes |
| `test_geojson.py` | Feature, FeatureCollection, bbox, preserved members |
| `test_cli.py` | command options, `python -m geom180to360` |
| `test_plot.py` | figures produced without error (ignored without matplotlib) |

## Author

👤 **Jean-Christophe MALAPERT**

## 🤝 Contributing

Contributions, issues and feature requests are welcome!  
Feel free to check [issues page](https://gitlab.cnes.fr/pdssp/common/geom180to360/issues).  
You can also take a look at the [contributing guide](https://gitlab.cnes.fr/pdssp/common/geom180to360/blob/main/CONTRIBUTING.rst)

## 📝 License

This project is [Apache V2.0](https://gitlab.cnes.fr/pdssp/common/geom180to360/blob/main/LICENSE) licensed.
