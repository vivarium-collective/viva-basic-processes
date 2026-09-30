"""A reusable Intervention process.

Investigations repeatedly need to apply a *specific perturbation* to a model —
clamp a quantity, knock a store to zero, externally supply something, scale a
pool — to build negative controls and test counterfactuals (the kind of
controls a skeptical reviewer asks for). Rather than hand-write a bespoke
process per perturbation, ``pbg-basic-processes`` ships one generic
``Intervention`` process that any workspace can wire into a composite.

Wire it into a composite by pointing its single ``target`` port at the store to
perturb; it reads the current value and emits the additive delta needed to
realise the perturbation, optionally only within a time window.

Modes (config ``mode``):

- ``set``      — drive the target to ``value`` every step (a clamp).
- ``knockout`` — drive the target to 0 (``set`` with value 0).
- ``scale``    — multiply the target by ``value`` (factor) each step.
- ``add``      — add ``value`` each step; with ``per_step: true`` it adds
                 ``value * interval`` (a rate) instead of a fixed bolus.
- ``decouple`` (alias ``remove``) — freeze the target at its value when the
                 intervention *first became active*, severing this process's net
                 contribution without nulling the pool (``delta = frozen - current``).
- ``invert``   — flip the coupling sign each step: ``delta = -2 * current`` drives
                 the store toward ``-current``.

``window: [t0, t1]`` (optional) restricts the intervention to ``t0 <= t < t1``.
By default ``t`` is the process's own elapsed time (accumulated across
``update`` calls). Set ``use_global_time: true`` and wire the ``global_time``
input to a :class:`viva_basic_processes.clock.Clock` to gate on *absolute*
simulation time instead. Omitted/empty window ⇒ always active.

Pure process-bigraph; no AI. Auto-registers into any workspace ``core`` via
bigraph-schema package discovery; or register explicitly with
:func:`register_intervention` and add a node with :func:`intervention_node`.
"""
from __future__ import annotations

from typing import Any, Optional

from process_bigraph import Process


class Intervention(Process):
    """Apply a specific perturbation to one target store (see module docstring)."""

    config_schema = {
        'mode': {'_type': 'string', '_default': 'set'},      # set|knockout|scale|add|decouple(remove)|invert
        'value': {'_type': 'float', '_default': 0.0},
        'window': {'_type': 'list', '_default': []},          # [t0, t1] or []
        'per_step': {'_type': 'boolean', '_default': False},  # add-mode: value*interval
        'use_global_time': {'_type': 'boolean', '_default': False},  # gate window on a wired Clock
    }

    def __init__(self, config: Optional[dict] = None, core: Any = None) -> None:
        super().__init__(config, core)
        # Elapsed process time, accumulated across update() calls so a `window`
        # can gate the intervention without a global-time wire.
        self._elapsed = 0.0
        # decouple/remove: the target value captured the first step the
        # intervention is active; None until then.
        self._frozen = None

    def inputs(self):
        ports = {'target': 'float'}
        if self.config.get('use_global_time'):
            ports['global_time'] = 'float'
        return ports

    def outputs(self):
        return {'target': 'float'}

    def update(self, state, interval):
        if self.config.get('use_global_time'):
            # Gate on absolute simulation time from a wired Clock.
            t = float(state.get('global_time', 0.0) or 0.0)
        else:
            t = self._elapsed
        self._elapsed += interval

        window = self.config.get('window') or []
        if isinstance(window, (list, tuple)) and len(window) == 2:
            t0, t1 = window
            if not (t0 <= t < t1):
                return {}

        current = state.get('target', 0.0) or 0.0
        mode = (self.config.get('mode') or 'set').lower()
        value = self.config.get('value', 0.0)

        if mode == 'set':
            delta = value - current
        elif mode == 'knockout':
            delta = -current
        elif mode == 'scale':
            delta = current * (value - 1.0)
        elif mode == 'add':
            delta = value * interval if self.config.get('per_step') else value
        elif mode in ('decouple', 'remove'):
            # Freeze at the value the target held when first active.
            if self._frozen is None:
                self._frozen = current
            delta = self._frozen - current
        elif mode == 'invert':
            delta = -2.0 * current
        else:
            delta = 0.0

        return {'target': delta}


def register_intervention(core: Any, name: str = 'Intervention') -> bool:
    """Register :class:`Intervention` into ``core`` (via ``register_link``) so a
    composite can reference ``local:Intervention``. No-op-safe; returns True when
    newly registered, False if already present or on error."""
    try:
        link_reg = getattr(core, 'link_registry', {}) or {}
        if name in link_reg:
            return False
        core.register_link(name, Intervention)
        return True
    except Exception:
        return False


def intervention_node(target_path, *, mode: str = 'set', value: float = 0.0,
                      window=None, per_step: bool = False, interval: float = 1.0,
                      use_global_time: bool = False, global_time_path=('global_time',),
                      address: str = 'local:Intervention') -> dict:
    """Build a process-bigraph node dict for an Intervention, ready to drop into
    a composite's ``state``.

    ``target_path`` is the path (list of keys) to the store to perturb; it is
    wired to both the input and output ``target`` port so the process reads the
    current value and writes the corrective delta.

    Set ``use_global_time=True`` to gate the ``window`` on absolute simulation
    time; ``global_time_path`` is then wired to a :class:`Clock`'s
    ``global_time`` store.

    Example::

        state['clamp_nutrient'] = intervention_node(
            ['nutrient'], mode='set', value=0.0)          # externally hold nutrient at 0
    """
    if isinstance(target_path, str):
        target_path = [target_path]
    config = {'mode': mode, 'value': float(value), 'per_step': bool(per_step)}
    if window:
        config['window'] = list(window)
    inputs = {'target': list(target_path)}
    outputs = {'target': list(target_path)}
    if use_global_time:
        config['use_global_time'] = True
        inputs['global_time'] = list(global_time_path)
    return {
        '_type': 'process',
        'address': address,
        'config': config,
        'interval': interval,
        'inputs': inputs,
        'outputs': outputs,
    }
