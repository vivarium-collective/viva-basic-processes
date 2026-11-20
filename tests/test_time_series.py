"""TimeSeriesStep: a sampled series read back with a zero-order hold, alone and driving a composite."""

import pytest
from bigraph_schema import allocate_core
from process_bigraph import Composite

from viva_basic_processes.time_series import TimeSeriesStep

TIMES = [0.0, 30.0, 60.0, 90.0]
SERIES = {"c": [0.0, 2.5, 1.5, 0.5], "occ": [0.0, 0.25, 0.15, 0.05]}


def _step(**config):
    return TimeSeriesStep({"times": TIMES, "values": SERIES, **config}, core=allocate_core())


def test_it_auto_registers_via_discovery():
    assert "TimeSeriesStep" in (getattr(allocate_core(), "link_registry", {}) or {})


@pytest.mark.parametrize(("t", "index"), [
    (0.0, 0), (29.9, 0), (30.0, 1), (45.0, 1), (60.0, 2), (89.0, 2), (90.0, 3), (500.0, 3),
    (29.9999999999, 1),  # within the tolerance of the 30 s sample
])
def test_each_series_holds_its_latest_sample_at_or_before_the_time(t, index):
    assert _step().update({"time": t}) == {name: values[index] for name, values in SERIES.items()}


def test_a_time_before_the_first_sample_is_an_error():
    with pytest.raises(ValueError, match="before the first sample"):
        _step().update({"time": -1.0})


def test_with_a_tighter_tolerance_a_time_just_short_of_a_sample_holds_the_one_before():
    # not 0.0: bigraph-schema before 1.8.3 replaces an explicit 0 in a config with the default
    assert _step(tolerance=1e-15).update({"time": 29.9999999999})["c"] == 0.0


@pytest.mark.parametrize(("times", "values", "message"), [
    ([], {"c": []}, "at least one sample time"),
    ([0.0, 30.0, 30.0], {"c": [1.0, 2.0, 3.0]}, "strictly increasing"),
    ([0.0, 30.0], {}, "at least one named series"),
    ([0.0, 30.0], {"c": [1.0]}, "has 1 values for 2 times"),
])
def test_a_malformed_series_is_refused(times, values, message):
    with pytest.raises(ValueError, match=message):
        TimeSeriesStep({"times": times, "values": values}, core=allocate_core())


def test_in_a_composite_it_replays_the_series_at_each_instant():
    """Driven by the engine's own time every 30 s, the stores hold each sample in turn and keep the last after it."""
    core = allocate_core()
    state = {
        "signal": {"c": -1.0, "occ": -1.0},
        "replay": {
            "_type": "step",
            "address": "local:TimeSeriesStep",
            "config": {"times": TIMES, "values": SERIES},
            "inputs": {"time": ["global_time"]},
            "outputs": {"c": ["signal", "c"], "occ": ["signal", "occ"]},
        },
        "emitter": {
            "_type": "step",
            "address": "local:RAMEmitter",
            "config": {"emit": {"signal": "map[float]", "global_time": "float"}},
            "inputs": {"signal": ["signal"], "global_time": ["global_time"]},
        },
        "clock": {
            "_type": "process",
            "address": "local:Tick",
            "interval": 30.0,
            "inputs": {"t": ["t"]},
            "outputs": {"t": ["t"]},
        },
        "t": 0.0,
    }
    sim = Composite({"state": state}, core=core)
    sim.run(150.0)
    rows = sim.state["emitter"]["instance"].history
    seen = {row["global_time"]: row["signal"] for row in rows}
    for t, index in ((0.0, 0), (30.0, 1), (60.0, 2), (90.0, 3), (150.0, 3)):
        assert seen[t] == {name: values[index] for name, values in SERIES.items()}, t
