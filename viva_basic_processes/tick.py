"""A minimal Tick process — a continuous simulation-time accumulator.

``Tick`` reads a floating-point time store ``t`` and writes ``t + interval``
every update, turning the engine's per-update ``interval`` into an explicit,
wireable ``t(sim-time)`` signal that other processes/steps can consume (e.g. a
:class:`~viva_basic_processes.math_expression.MathExpressionStep` whose
expressions are functions of ``t``).

This differs from :class:`~viva_basic_processes.clock.Clock`:

* ``Clock`` emits a discrete integer *step count* (``tick``).
* ``Tick`` accumulates *continuous time* (a float ``t``) into a user store.

process-bigraph already maintains ``global_time`` as a reserved store in every
composite; wire an input to ``['global_time']`` to read absolute sim time
without any process. ``Tick`` is for the cases where you want that running total
in an ordinary (non-reserved) store you control and emit — writing to the
reserved ``global_time`` store directly would corrupt the engine's master clock.

Pure process-bigraph; no heavy dependencies. Auto-registers into any workspace
``core`` via bigraph-schema package discovery.
"""
from __future__ import annotations

from typing import Any, Optional

from process_bigraph import Process


class Tick(Process):
    """Accumulate continuous simulation time into a float ``t`` store.

    Reads ``t`` and writes ``t + interval`` each update, where ``interval`` is
    the process interval supplied by the engine. The starting value comes from
    whatever the ``t`` store is initialized to in the composite state.
    """

    config_schema: dict = {}

    def __init__(self, config: Optional[dict] = None, core: Any = None) -> None:
        super().__init__(config, core)

    def inputs(self):
        return {"t": "float"}

    def outputs(self):
        return {"t": "overwrite[float]"}

    def update(self, state, interval):
        return {"t": float(state["t"]) + float(interval)}


def register_tick(core: Any, name: str = "Tick") -> bool:
    """Register :class:`Tick` into ``core`` (via ``register_link``). No-op-safe;
    returns True when newly registered, False if already present or on error."""
    try:
        link_reg = getattr(core, "link_registry", {}) or {}
        if name in link_reg:
            return False
        core.register_link(name, Tick)
        return True
    except Exception:
        return False


def tick_node(*, interval: float = 1.0, t_path=("t",), address: str = "local:Tick") -> dict:
    """Build a process-bigraph node dict for a :class:`Tick`, ready to drop into
    a composite's ``state``. ``t_path`` is the store the tick reads and writes
    its accumulated time to (same store on both ports)."""
    return {
        "_type": "process",
        "address": address,
        "config": {},
        "interval": interval,
        "inputs": {"t": list(t_path)},
        "outputs": {"t": list(t_path)},
    }
