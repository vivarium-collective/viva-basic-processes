# pbg-basic-processes

Reusable, composite-agnostic [process-bigraph](https://github.com/vivarium-collective/process-bigraph) processes — the small, generic building blocks that show up in almost every workspace.

| Process | What it does |
|---|---|
| `Clock` | Emits an integer `tick` step counter each step — the one temporal quantity the engine does *not* expose as a store. (Absolute simulation time, `global_time`, is already maintained by the engine in every composite; wire any input to `['global_time']` to read it.) |
| `Tick` | Accumulates continuous simulation time into a float `t` store (`t -> t + interval` each update) — a wireable time signal for processes/steps that are functions of `t` (e.g. a time-driven `MathExpressionStep`). |
| `Intervention` | Applies a specific perturbation to one target store — `set` / `knockout` / `scale` / `add` / `decouple` / `invert`, optionally within a time window. The building block for negative controls and counterfactuals. |
| `MathExpressionStep` | Evaluates a list of named symbolic (SymPy) expressions as one Step, inferring input ports from free symbols and resolving inter-expression dependencies in topological order. |

## Auto-registration

Like [`pbg-emitters`](https://github.com/vivarium-collective/pbg-emitters), these processes **auto-register** into any workspace `core`. `allocate_core()` walks every installed distribution that depends on `bigraph-schema` and registers its `Process`/`Step` subclasses — no entry points, no `register_*` boilerplate:

```python
from bigraph_schema import allocate_core

core = allocate_core()
assert 'Clock' in core.link_registry          # just by being installed
assert 'Intervention' in core.link_registry
assert 'MathExpressionStep' in core.link_registry
```

Add `pbg-basic-processes` as a dependency of your workspace (it is a base dependency of `pbg-superpowers`, so every pbg workspace gets it) and reference the processes by `local:Clock`, `local:Tick`, `local:Intervention`, `local:MathExpressionStep`.

## Plotting helpers (optional)

`viva_basic_processes.plotting` provides two notebook/tutorial convenience helpers — `plot_timeseries` (line plots of emitted records over a time column) and `plot_single_eval` (a bar chart of one step's inputs/outputs). They require matplotlib, which is an **optional** extra so the core processes stay lightweight:

```bash
pip install "viva-basic-processes[plotting]"
```

```python
from viva_basic_processes import plot_timeseries, plot_single_eval
```

## Install

```bash
pip install pbg-basic-processes            # from PyPI (when published)
pip install -e .                           # from a checkout
```

## Usage

Node-builder helpers make wiring into a composite easy:

```python
from pbg_basic_processes import clock_node, intervention_node

state = {
    'tick': 0,
    'nutrient': 5.0,
    'clock': clock_node(interval=1.0),          # writes a step counter to ['tick']
    # hold nutrient at 0 only between t=10 and t=20 of absolute sim time.
    # use_global_time wires the window to the engine's reserved global_time store.
    'starve': intervention_node(['nutrient'], mode='set', value=0.0,
                                window=[10, 20], use_global_time=True),
}
```

## Develop

```bash
pip install -e '.[dev]'
pytest -q
```

MIT-licensed. Part of the [vivarium-collective](https://github.com/vivarium-collective) process-bigraph ecosystem.
