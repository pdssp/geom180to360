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
logger.remove()

class SmartFormatter(argparse.HelpFormatter):
    """Smart formatter for argparse - The lines are split for long text"""

    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(  # pylint: disable=protected-access
            self, text, width
        )


class SigintHandler:  # pylint: disable=too-few-public-methods
    """Handles the signal"""

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


def parse_cli() -> argparse.Namespace:
    """Parse command line inputs.

    Returns
    -------
    argparse.Namespace
        Command line options
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

    return parser.parse_args()


def run():
    """Main function that instanciates the library."""
    handler = SigintHandler()
    signal.signal(signal.SIGINT, handler.signal_handler)
    try:
        options_cli = parse_cli()
        logger.add(sys.stderr, level=options_cli.level)
        sys.exit(0)
    except Exception as error:  # pylint: disable=broad-except
        logger.exception(error)
        sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    run()
