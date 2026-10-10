"""Tests for the Tick process and the plotting helpers.

These are the pieces process-bigraph Tutorial 3 ("Declarative Math with
MathExpressionStep") depends on: a continuous-time ``Tick`` wired into a
``MathExpressionStep``, plus ``plot_timeseries`` / ``plot_single_eval``.
"""
import pytest

from bigraph_schema import allocate_core
from process_bigraph import Composite

from viva_basic_processes import (
    Tick,
    MathExpressionStep,
    plot_timeseries,
    plot_single_eval,
    tick_node,
)


def test_tick_auto_registers_via_discovery():
    core = allocate_core()
    link_reg = getattr(core, "link_registry", {}) or {}
    assert "Tick" in link_reg, "Tick was not auto-discovered into the core registry"


def test_tick_accumulates_time():
    """A Tick wired to a MathExpressionStep: t advances, z = a*b tracks state."""
    core = allocate_core()
    dt = 0.5
    state = {
        "t": 0.0,
        "a": 2.0,
        "b": 3.0,
        "z": 0.0,
        "tick": tick_node(interval=dt, t_path=("t",)),
        "math": {
            "_type": "step",
            "address": "local:MathExpressionStep",
            "config": {
                "expressions": [{"out": "z", "expr": "a*b + t"}],
                "debug": False,
            },
            "inputs": {"a": ["a"], "b": ["b"], "t": ["t"]},
            "outputs": {"z": ["z"]},
        },
    }
    comp = Composite({"state": state}, core=core)
    comp.run(4 * dt)  # four ticks

    end = comp.state
    assert end["t"] == pytest.approx(4 * dt)
    # z = a*b + t = 6 + 2.0
    assert end["z"] == pytest.approx(2.0 * 3.0 + 4 * dt)


def test_plot_timeseries_returns_figure():
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")  # headless
    records = [{"t": 0.0, "z": 1.0}, {"t": 1.0, "z": 2.0}, {"t": 2.0, "z": 3.0}]
    fig = plot_timeseries(records, ["z"], title="z(t)", legend=False)
    assert fig is not None
    matplotlib.pyplot.close("all")


def test_plot_single_eval_returns_figure():
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")  # headless
    state = {"a": 2.0, "b": 3.0, "c": 0.5, "z": 6.5}
    fig = plot_single_eval(state, inputs=("a", "b", "c"), outputs=("z",),
                           expected={"z": 6.5}, title="single eval")
    assert fig is not None
    matplotlib.pyplot.close("all")
