"""A MathExpression Step: evaluate named symbolic expressions as one Step.

Configure a list of ``{"out": <name>, "expr": <string>}`` entries. The Step
parses each expression with SymPy, infers its input ports from the free symbols
(anything that isn't another output or a declared param), evaluates the
expressions in dependency-respecting topological order, and writes an overwrite
patch for every output. Expressions may reference other outputs; algebraic
cycles raise a ``ValueError`` with a dependency hint.

Pure process-bigraph + SymPy; no plotting or I/O. Auto-registers into any
workspace ``core`` via bigraph-schema package discovery.
"""
from __future__ import annotations

import sympy as sp

from process_bigraph import Step


class MathExpressionStep(Step):
    """Evaluate a set of user-configured mathematical expressions as a single Step.

    Configuration
    -------------
    expressions : list[dict]
        List of ``{"out": <str>, "expr": <str>}`` entries. Each ``out`` becomes
        an output port and state field.
    params : dict[str, float], optional
        Named constants available to expressions without becoming input ports.
    functions : str, optional
        SymPy ``lambdify`` backend module name (default ``"numpy"``).
    debug : bool, optional
        If True, prints inferred ports, dependency order, and compilation details.

    Notes
    -----
    Single-pass evaluation in dependency order; not a simultaneous-equation
    solver. Cyclic dependencies require a different approach (fixed-point
    iteration or root finding).
    """

    config_schema = {
        "expressions": "node",  # list[{"out": str, "expr": str}]
        "params": {"_type": "node", "_default": {}},
        "functions": {"_type": "string", "_default": "numpy"},
        "debug": {"_type": "boolean", "_default": False},
    }

    def initialize(self, config=None):
        cfg = self.config
        debug = bool(cfg.get("debug", False))

        expr_specs = cfg.get("expressions", None)
        if not isinstance(expr_specs, (list, tuple)) or len(expr_specs) == 0:
            raise ValueError("MathExpressionStep requires config['expressions'] as a non-empty list")

        self._params = dict(cfg.get("params", {}))
        backend = cfg.get("functions", "numpy")

        # Validate + parse
        out_names = []
        expr_map = {}  # out -> sympy expr
        raw_map = {}   # out -> expr string (for debugging)
        for spec in expr_specs:
            out = spec.get("out", None)
            expr_str = spec.get("expr", None)
            if not isinstance(out, str) or not out:
                raise ValueError("Each expression spec must have a non-empty string 'out'")
            if not isinstance(expr_str, str) or not expr_str:
                raise ValueError(f"Expression for '{out}' must be a non-empty string")
            if out in expr_map:
                raise ValueError(f"Duplicate output name: '{out}'")

            try:
                expr = sp.sympify(expr_str)
            except Exception as e:
                raise ValueError(f"Failed to parse expression for '{out}': {expr_str}\n{e}") from e

            out_names.append(out)
            expr_map[out] = expr
            raw_map[out] = expr_str

        self._out_names = out_names
        out_set = set(out_names)
        param_set = set(self._params.keys())

        # Build dependency graph among outputs
        # deps[out] = set of output-names that out depends on
        deps = {out: set() for out in out_names}
        external_inputs = set()

        for out, expr in expr_map.items():
            free = {str(s) for s in expr.free_symbols}

            # outputs referenced become dependencies
            deps[out] = {name for name in free if name in out_set and name != out}

            # anything else that isn't a param and isn't an output is an external input port
            external_inputs |= {name for name in free if name not in out_set and name not in param_set}

        # Topological sort (Kahn) to get execution order
        indeg = {o: 0 for o in out_names}
        for o in out_names:
            for d in deps[o]:
                indeg[o] += 1

        # Start with nodes that have no dependencies.
        # Use sorted() for deterministic order.
        queue = [o for o in sorted(out_names) if indeg[o] == 0]
        exec_order = []

        # adjacency: who depends on me
        rev = {o: set() for o in out_names}
        for o in out_names:
            for d in deps[o]:
                rev[d].add(o)

        while queue:
            n = queue.pop(0)
            exec_order.append(n)
            for m in sorted(rev[n]):
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)

        if len(exec_order) != len(out_names):
            # cycle exists
            remaining = [o for o in out_names if o not in exec_order]
            # give a helpful hint about the cycle region
            cycle_hint = {o: sorted(list(deps[o])) for o in remaining}
            raise ValueError(
                "Cyclic dependency between expressions. Cannot order outputs.\n"
                f"Remaining outputs: {remaining}\n"
                f"Dependencies among remaining: {cycle_hint}"
            )

        self._exec_order = exec_order
        self._in_names = sorted(external_inputs)

        # Compile each expression with *just the symbols it needs* (deterministic arg list)
        self._compiled = {}         # out -> callable
        self._needed_symbols = {}   # out -> list[str] (argument names)
        for out in out_names:
            expr = expr_map[out]
            needed = sorted({str(s) for s in expr.free_symbols})
            fn = sp.lambdify([sp.Symbol(n) for n in needed], expr, modules=backend)
            self._compiled[out] = fn
            self._needed_symbols[out] = needed

        if debug:
            print("\n[MathExpressionStep] initialize()")
            print("  outputs declared:", self._out_names)
            print("  params:", self._params)
            print("  inferred input ports:", self._in_names)
            print("  dependency order:", self._exec_order)
            for out in self._exec_order:
                print(f"   - {out} = {raw_map[out]}")
                print(f"     depends on outputs: {sorted(list(deps[out]))}")
                print(f"     needs symbols     : {self._needed_symbols[out]}")
            print("[MathExpressionStep] initialize complete\n")

        return cfg

    def inputs(self):
        return {name: "float" for name in self._in_names}

    def outputs(self):
        # all declared outputs are ports, regardless of execution order
        return {name: "overwrite[float]" for name in self._out_names}

    def update(self, state):
        # Values available for expression evaluation
        values = {}

        # External input ports come from state
        for name in self._in_names:
            values[name] = float(state[name])

        # Params are constants
        for k, v in self._params.items():
            values[k] = float(v)

        # Evaluate in dependency order
        out_patch = {}
        for out in self._exec_order:
            needed = self._needed_symbols[out]
            args = []
            for name in needed:
                if name not in values:
                    raise ValueError(
                        f"While computing '{out}', missing symbol '{name}'. "
                        f"(Likely an internal dependency not yet computed or missing input/param.)"
                    )
                args.append(values[name])

            y = self._compiled[out](*args)
            y = float(y)
            values[out] = y
            out_patch[out] = y

        return out_patch
