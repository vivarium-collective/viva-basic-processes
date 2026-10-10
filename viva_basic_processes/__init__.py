"""viva-basic-processes: reusable, composite-agnostic process-bigraph processes.

These processes auto-register into any workspace ``core`` via bigraph-schema
package discovery (``allocate_core`` walks every installed ``bigraph-schema``
dependent and registers its ``Process`` / ``Step`` subclasses) — no entry
points or ``register_*`` boilerplate required. Add ``viva-basic-processes`` as a
dependency and ``Clock`` / ``Intervention`` / ``MathExpressionStep`` appear in
the registry, the same way ``viva-emitters`` surfaces its emitters.

(Was ``pbg-basic-processes`` before the pbg -> viva rename; a ``pbg_basic_processes``
import shim still ships for back-compat.)
"""

from viva_basic_processes.clock import Clock, register_clock, clock_node
from viva_basic_processes.tick import Tick, register_tick, tick_node
from viva_basic_processes.intervention import (
    Intervention,
    register_intervention,
    intervention_node,
)

try:
    from viva_basic_processes.math_expression import MathExpressionStep
except ImportError:  # pragma: no cover - sympy is a base dep, but stay defensive
    pass

# Plotting helpers (plot_timeseries / plot_single_eval) live in
# viva_basic_processes.plotting and require the optional ``[plotting]`` extra
# (matplotlib). Import them here for convenience, but stay importable without
# matplotlib installed — the helpers raise a clear error only when called.
from viva_basic_processes.plotting import plot_timeseries, plot_single_eval

__all__ = [
    "Clock",
    "register_clock",
    "clock_node",
    "Tick",
    "register_tick",
    "tick_node",
    "Intervention",
    "register_intervention",
    "intervention_node",
    "MathExpressionStep",
    "plot_timeseries",
    "plot_single_eval",
]
