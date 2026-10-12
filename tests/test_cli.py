"""Command-line interface."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from geom180to360 import __version__
from geom180to360.__main__ import run


def test_wkt_arguments(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run(["POINT (-90 45)", "LINESTRING (-170 0, -160 10)"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out == "POINT (270 45)\nLINESTRING (190 0, 200 10)\n"


def test_input_file_skips_comments_and_blank_lines(tmp_path, capsys):
    src = tmp_path / "in.wkt"
    src.write_text("# commentaire\nPOINT (-90 45)\n\nPOINT (10 5)\n", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        run(["-i", str(src)])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out == "POINT (270 45)\nPOINT (10 5)\n"


def test_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("POINT (-1 0)\n"))
    with pytest.raises(SystemExit) as excinfo:
        run([])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out == "POINT (359 0)\n"


def test_output_file(tmp_path):
    out = tmp_path / "out.wkt"
    with pytest.raises(SystemExit) as excinfo:
        run(["-o", str(out), "POINT (-90 45)"])
    assert excinfo.value.code == 0
    assert out.read_text(encoding="utf-8") == "POINT (270 45)\n"


def test_precision_and_no_split(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run(["-p", "1", "--no-split", "LINESTRING (-10.04 0, 10 0)"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out == "LINESTRING (350 0, 10 0)\n"


def test_geojson(tmp_path, capsys):
    src = tmp_path / "in.geojson"
    src.write_text('{"type": "Point", "coordinates": [-90, 45]}', encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        run(["--geojson", "-i", str(src)])
    assert excinfo.value.code == 0
    assert json.loads(capsys.readouterr().out) == {
        "type": "Point",
        "coordinates": [270.0, 45.0],
    }

def test_error_continues_and_returns_1(capsys):
    with pytest.raises(SystemExit) as excinfo:
        run(["POINT (200 0)", "POINT (-90 0)"])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == "POINT (270 0)\n"
    assert "no. 1" in captured.err


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_python_m():
    result = subprocess.run(
        [sys.executable, "-m", "geom180to360", "POINT (-90 45)"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "POINT (270 45)\n"
