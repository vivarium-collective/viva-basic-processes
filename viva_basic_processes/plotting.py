"""Small matplotlib plotting helpers for process-bigraph records.

These are convenience utilities for notebooks and tutorials — ``plot_timeseries``
(line plots of emitted records over a time column) and ``plot_single_eval`` (a
bar chart of a single step's inputs/outputs, optionally vs. expected values).

matplotlib is an *optional* dependency: it is imported lazily inside each
function so that ``import viva_basic_processes`` (and the auto-registration of
the processes) never requires it. Install the extra to use these helpers::

    pip install "viva-basic-processes[plotting]"
"""
from __future__ import annotations

import numpy as np


def _require_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: WPS433 (lazy import by design)
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "matplotlib is required for viva_basic_processes.plotting. "
            "Install it with: pip install 'viva-basic-processes[plotting]'"
        ) from exc
    return plt


def plot_single_eval(state, *, inputs=("a", "b", "c"), outputs=("z",), expected=None, title=None):
    """Plot a single evaluation (e.g. of a MathExpressionStep): inputs and
    outputs as bars.

    Parameters
    ----------
    state : dict-like
        Typically ``sim.state`` (or a nested dict) containing the variables.
    inputs, outputs : tuple[str]
        Names to plot from the state.
    expected : dict[str, float] | None
        Optional expected values to overlay for outputs, e.g. ``{"z": ...}``.
    title : str | None
        Plot title.

    Returns
    -------
    matplotlib.figure.Figure
        The figure for the inputs/outputs bar chart.
    """
    plt = _require_matplotlib()

    names = list(inputs) + list(outputs)
    values = [float(state[n]) for n in names]

    fig = plt.figure()
    plt.bar(names, values)
    plt.ylabel("value")
    plt.title(title or "Single evaluation: inputs -> outputs")
    plt.show()

    if expected:
        # Small companion plot: output vs expected
        out_names = list(outputs)
        out_vals = [float(state[n]) for n in out_names]
        exp_vals = [float(expected[n]) for n in out_names]

        x = np.arange(len(out_names))
        width = 0.35

        plt.figure()
        plt.bar(x - width / 2, out_vals, width, label="computed")
        plt.bar(x + width / 2, exp_vals, width, label="expected")
        plt.xticks(x, out_names)
        plt.ylabel("value")
        plt.title("Outputs: computed vs expected")
        plt.legend()
        plt.show()

    return fig


def plot_timeseries(records, series, *, x="t", title=None, xlabel=None, ylabel=None,
                    marker=".", linewidth=None, legend=True):
    """Plot one or more series from a list of emitted ``records`` over a time column.

    Parameters
    ----------
    records : list[dict]
        Emitted records (e.g. ``emitter.query()``), each a dict keyed by variable.
    series : Iterable[str] | dict[str, str]
        Keys to plot. A dict maps key -> legend label.
    x : str
        The record key to use for the x-axis (default ``"t"``).

    Returns
    -------
    matplotlib.figure.Figure
        The figure.
    """
    plt = _require_matplotlib()

    if not records:
        raise ValueError("No records to plot")

    ts = np.array([r[x] for r in records], dtype=float)

    if isinstance(series, dict):
        keys = list(series.keys())
        labels = series
    else:
        keys = list(series)
        labels = {k: k for k in keys}

    fig = plt.figure()
    for k in keys:
        ys = np.array([r[k] for r in records], dtype=float)
        plt.plot(ts, ys, marker=marker, linewidth=linewidth, label=labels[k])

    plt.xlabel(xlabel or x)
    if ylabel is not None:
        plt.ylabel(ylabel)
    if title is not None:
        plt.title(title)
    if legend and len(keys) > 1:
        plt.legend()
    plt.show()

    return fig
