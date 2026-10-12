# -*- coding: utf-8 -*-
# geom180to360 - Conversion tool of geometries from longitudes [-180, 180] to [0, 360]
# Copyright (C) 2026 - CNES (Jean-Christophe MALAPERT for PDSSP)
# This file is part of geom180to360 <https://gitlab.cnes.fr/pdssp/common/geom180to360>
# SPDX-License-Identifier: Apache-2.0
"""Main program."""
import sys
import argparse
import signal
from loguru import logger
from geom180to360 import __author__
from geom180to360 import __copyright__
from geom180to360 import __description__
from geom180to360 import __version__
from .config import configure_logging

import json
import sys
from collections.abc import Iterable, Iterator
from typing import TextIO

from shapely import wkt as shapely_wkt
from shapely.geometry import GeometryCollection
from shapely.geometry.base import BaseGeometry

from . import __version__
from .convert import convert_wkt
from .geojson import convert_geojson, geojson_geometry

logger.remove()

_Plotted = list[tuple[BaseGeometry, BaseGeometry]]

class SmartFormatter(argparse.HelpFormatter):
    """Smart formatter for argparse - lines are split for long text"""

    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(  # pylint: disable=protected-access
            self, text, width
        )


class SigintHandler:  # pylint: disable=too-few-public-methods
    """Handles SIGINT signals"""

    def __init__(self):
        self.SIGINT = False  # pylint: disable=invalid-name

    def signal_handler(self, sig: int, frame):
        """Trap the signal

        Args:
            sig (int): the signal number
            frame: the current stack frame
        """
        # pylint: disable=unused-argument
        logger.error("You pressed Ctrl+C")
        self.SIGINT = True
        sys.exit(2)


def str2bool(string_to_test: str) -> bool:
    """Checks if a given string is a boolean

    Args:
        string_to_test (str): string to test

    Returns:
        bool: True when the string is a boolean otherwise False
    """
    return string_to_test.lower() in ("yes", "true", "True", "t", "1")


def build_parser() -> argparse.ArgumentParser:
    """Parse parser for Command Line Interface (CLI).

    Returns
    -------
    argparse.ArgumentParser
        The argument parser instance.
    """
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=SmartFormatter,
        epilog=__author__ + " - " + __copyright__,
    )
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )

    parser.add_argument(
        "--level",
        choices=[
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "TRACE",
        ],
        default="INFO",
        help="set Level log (default: %(default)s)",
    )
    parser.add_argument(
        "wkt",
        nargs="*",
        help="WKT geometry(ies). If absent, reads --input or standard input "
        "(one geometry per line).",
    )
    parser.add_argument("-i", "--input", help="Input file (one WKT per line).")
    parser.add_argument("-o", "--output", help="Output file (default: stdout).")
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Do not split at 0° meridian (simple lon+360 shift).",
    )
    parser.add_argument(
        "-p",
        "--precision",
        type=int,
        default=None,
        help="Number of decimal places in output (default: full precision).",
    )
    parser.add_argument(
        "--geojson",
        action="store_true",
        help="Input/output GeoJSON: each argument, or the entire content "
        "of --input / standard input, is a GeoJSON document.",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Display input and output on the sphere in a window. "
        "Requires matplotlib.",
    )
    parser.add_argument(
        "--plot-output",
        metavar="IMAGE",
        help="Like --plot, but saves the figure to IMAGE "
        "(png, svg, pdf, etc.) instead of displaying it.",
    )
    parser.add_argument(
        "--view",
        nargs=2,
        type=float,
        metavar=("LON", "LAT"),
        help="Viewpoint for --plot (default: centered on geometries).",
    )
    return parser

def _iter_wkt(lines: Iterable[str]) -> Iterator[str]:
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def _open_output(path: str | None) -> TextIO:
    return open(path, "w", encoding="utf-8") if path else sys.stdout


def _plot(args: argparse.Namespace, plotted: _Plotted) -> int:
    """Plot geometries; returns 1 (with a message) if impossible."""
    if not args.plot or not plotted:
        return 0
    try:
        from .plot import plot_conversion

        plot_conversion(
            GeometryCollection([src for src, _ in plotted]),
            GeometryCollection([dst for _, dst in plotted]),
            output=args.plot_output,
            view=tuple(args.view) if args.view else None,
        )
    except ImportError as exc:
        print(
            f"Visualization impossible ({exc}): install matplotlib, "
            "for example with uv sync or the [plot] option.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:  # noqa: BLE001 - graphics backend (Tk, Qt, etc.)
        if args.plot_output:
            raise
        print(
            "Cannot open a visualization window "
            f"({type(exc).__name__}: {str(exc).strip().splitlines()[0]}).\n"
            "Save the figure to a file with --plot-output IMAGE.png, "
            "or check Python's Tcl/Tk installation.",
            file=sys.stderr,
        )
        return 1
    return 0


def _run_wkt(args: argparse.Namespace) -> int:
    if args.wkt:
        source: Iterable[str] = args.wkt
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            source = f.readlines()
    else:
        source = sys.stdin

    out = _open_output(args.output)
    status = 0
    plotted: _Plotted = []
    try:
        for n, wkt in enumerate(_iter_wkt(source), start=1):
            try:
                result = convert_wkt(
                    wkt, split=not args.no_split, precision=args.precision
                )
                geom = shapely_wkt.loads(result)
                line = result
                out.write(line + "\n")
                if args.plot:
                    plotted.append((shapely_wkt.loads(wkt), geom))
            except Exception as exc:  # noqa: BLE001 - continue on error
                print(f"Error geometry no. {n}: {exc}", file=sys.stderr)
                status = 1
    finally:
        if out is not sys.stdout:
            out.close()
    return max(status, _plot(args, plotted))


def _run_geojson(args: argparse.Namespace) -> int:
    if args.wkt:
        docs = args.wkt
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            docs = [f.read()]
    else:
        docs = [sys.stdin.read()]

    out = _open_output(args.output)
    status = 0
    plotted: _Plotted = []
    try:
        for n, doc in enumerate(docs, start=1):
            try:
                result = convert_geojson(
                    json.loads(doc), split=not args.no_split, precision=args.precision
                )
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
                if args.plot:
                    plotted.append(
                        (geojson_geometry(json.loads(doc)), geojson_geometry(result))
                    )
            except Exception as exc:  # noqa: BLE001 - continue on error
                print(f"Error GeoJSON document no. {n}: {exc}", file=sys.stderr)
                status = 1
    finally:
        if out is not sys.stdout:
            out.close()
    return max(status, _plot(args, plotted))

def run(argv: list[str] | None = None):
    """Entry point for the ``geom180to360`` command.

    :param argv: arguments (default: ``sys.argv[1:]``).
    :return: exit code (0 if all went well, 1 otherwise).
    """
    handler = SigintHandler()
    signal.signal(signal.SIGINT, handler.signal_handler)
    try:
        args = build_parser().parse_args(argv)
        configure_logging()
        logger.add(sys.stderr, level=args.level)
        args.plot = args.plot or args.plot_output is not None
        status = _run_geojson(args) if args.geojson else _run_wkt(args)
        sys.exit(status)
    except Exception as error:  # pylint: disable=broad-except
        logger.exception(error)
        sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    run()
