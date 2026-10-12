# -*- coding: utf-8 -*-
# geom180to360 - Conversion tool of geometries from longitudes [-180, 180] to [0, 360]
# Copyright (C) 2026 - CNES (Jean-Christophe MALAPERT for PDSSP)
# This file is part of geom180to360 <https://gitlab.cnes.fr/pdssp/common/geom180to360>
# SPDX-License-Identifier: Apache-2.0
"""Conversion tool of geometries from longitudes [-180, 180] to [0, 360]"""
from ._version import __author__
from ._version import __author_email__
from ._version import __copyright__
from ._version import __description__
from ._version import __license__
from ._version import __name_soft__
from ._version import __title__
from ._version import __url__
from ._version import __version__

from .convert import convert_geometry, convert_wkt, shift_longitudes  # noqa: E402
from .geojson import convert_geojson, geojson_geometry  # noqa: E402
from .plot import plot_conversion, plot_sphere  # noqa: E402
from .polar import resolve_polar_rings  # noqa: E402

__all__ = [
    "__version__",
    "convert_geojson",
    "convert_geometry",
    "convert_wkt",
    "geojson_geometry",
    "plot_conversion",
    "plot_sphere",
    "resolve_polar_rings",
    "shift_longitudes",
]