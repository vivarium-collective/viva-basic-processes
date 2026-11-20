"""A sampled time series, read back at a given time.

``TimeSeriesStep`` holds one or more named series sampled at the same increasing ``times``. Given an input ``time``,
it writes each series' value at the latest sample at or before that time: a zero-order hold, which is how a coupling
that samples a signal and holds it for an interval sees it. A time within ``tolerance`` of a sample counts as that
sample, so a clock that reads 29.999999 at the 30 s instant still gets the 30 s value (bigraph-schema before 1.8.3
replaces an explicit 0 in a config with the default, so use a tiny positive tolerance for an exact match there).
Before the first sample is an error; after the last, the last value holds.

It drives a model with a signal computed elsewhere, exactly at its sampled instants: for example the concentration at
a cell's surface, recorded from a field simulation that the cell does not change.

Pure process-bigraph. Auto-registers into any workspace ``core`` via bigraph-schema package discovery; reference it as
``local:TimeSeriesStep`` or ``local:viva_basic_processes.time_series.TimeSeriesStep``.
"""

from __future__ import annotations

import bisect

from process_bigraph import Step


class TimeSeriesStep(Step):
    """Write each named series' value at the input ``time`` (the latest sample at or before it)."""

    config_schema = {
        "times": "node",  # strictly increasing sample times
        "values": "node",  # {name: [one value per sample time]}
        "tolerance": {"_type": "float", "_default": 1e-9},  # in the units of `times`
    }

    def initialize(self, config=None):
        times = [float(t) for t in self.config["times"]]
        if not times:
            raise ValueError("TimeSeriesStep needs at least one sample time")
        if any(later <= earlier for earlier, later in zip(times, times[1:])):
            raise ValueError("TimeSeriesStep's times must be strictly increasing")
        values = {str(name): [float(v) for v in series] for name, series in dict(self.config["values"]).items()}
        if not values:
            raise ValueError("TimeSeriesStep needs at least one named series in `values`")
        for name, series in values.items():
            if len(series) != len(times):
                raise ValueError(f"series {name!r} has {len(series)} values for {len(times)} times")
        tolerance = float(self.config.get("tolerance", 1e-9))
        if tolerance < 0:
            raise ValueError("TimeSeriesStep's tolerance must not be negative")
        self._times, self._values, self._tolerance = times, values, tolerance

    def inputs(self):
        return {"time": "float"}

    def outputs(self):
        return {name: "overwrite[float]" for name in self._values}

    def update(self, state):
        t = float(state["time"])
        i = bisect.bisect_right(self._times, t + self._tolerance) - 1
        if i < 0:
            raise ValueError(f"time {t} is before the first sample, {self._times[0]}")
        return {name: series[i] for name, series in self._values.items()}
