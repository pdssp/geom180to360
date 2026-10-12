"""Fixtures communes aux tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def plot_backend():
    """Backend matplotlib sans affichage ; ignore le test sans matplotlib."""
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    yield
    import matplotlib.pyplot as plt

    plt.close("all")
