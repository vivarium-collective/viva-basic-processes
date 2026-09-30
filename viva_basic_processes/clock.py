"""A minimal Clock process — an integer step counter.

process-bigraph's engine already maintains ``global_time`` (absolute simulation
time, a float) as a reserved store in *every* composite: wire any process input
to ``['global_time']`` to read it — no Clock required (see
:class:`viva_basic_processes.intervention.Intervention`'s ``use_global_time``).

What the engine does **not** track as a wireable store is a discrete *step
count*. That is ``Clock``'s job: it takes no inputs and emits ``tick`` (int),
incremented every update, so processes can schedule on "every N steps" or count
elapsed updates. Writing to the reserved ``global_time`` store is deliberately
avoided — doing so corrupts the engine's master clock.

Pure process-bigraph; no heavy dependencies. Auto-registers into any workspace
``core`` via bigraph-schema package discovery.
"""
from __future__ import annotations

from typing import Any, Optional

from process_bigraph import Process


class Clock(Process):
    """Emit an integer ``tick`` step counter each update.

    (For absolute simulation time, read the engine-maintained ``global_time``
    store directly — see the module docstring.)
    """

    config_schema = {
        'start_tick': {'_type': 'integer', '_default': 0},
    }

    def __init__(self, config: Optional[dict] = None, core: Any = None) -> None:
        super().__init__(config, core)
        self._tick = int(self.config.get('start_tick', 0))

    def inputs(self):
        return {}

    def outputs(self):
        return {'tick': 'overwrite[integer]'}

    def update(self, state, interval):
        self._tick += 1
        return {'tick': self._tick}


def register_clock(core: Any, name: str = 'Clock') -> bool:
    """Register :class:`Clock` into ``core`` (via ``register_link``). No-op-safe;
    returns True when newly registered, False if already present or on error."""
    try:
        link_reg = getattr(core, 'link_registry', {}) or {}
        if name in link_reg:
            return False
        core.register_link(name, Clock)
        return True
    except Exception:
        return False


def clock_node(*, start_tick: int = 0, interval: float = 1.0,
               tick_path=('tick',), address: str = 'local:Clock') -> dict:
    """Build a process-bigraph node dict for a :class:`Clock`, ready to drop into
    a composite's ``state``. ``tick_path`` is the store the clock writes its
    ``tick`` output to."""
    return {
        '_type': 'process',
        'address': address,
        'config': {'start_tick': int(start_tick)},
        'interval': interval,
        'inputs': {},
        'outputs': {'tick': list(tick_path)},
    }
