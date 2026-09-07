"""Typed recovery operators + budget governor.

Why typed operators: converting "figure out what to do about this error" from an
open-ended generation problem into a closed-set classification problem is the
transformation that survives quantization best. Every operator here is either
deterministic code or a single tightly-constrained model call.

Why the budget governor: on a Pi 5, unbounded retry is not a quality problem, it
is a thermal and energy problem. The budget is a correctness property, and
`J_max` is the term that makes energy-per-recovered-task meaningful.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from ..faults.taxonomy import RecoveryOp


# --------------------------------------------------------------------------- #
# budget
# --------------------------------------------------------------------------- #

@dataclass
class RecoveryBudget:
    n_max: int = 3            # recovery actions per episode
    tokens_max: int = 4096    # extra tokens spent on recovery
    wall_max_s: float = 120.0
    joules_max: float | None = None   # None on machines without a power meter

    def exhausted(self, st: "BudgetState") -> bool:
        return (st.n >= self.n_max
                or st.tokens >= self.tokens_max
                or st.wall_s >= self.wall_max_s
                or (self.joules_max is not None and st.joules >= self.joules_max))


@dataclass
class BudgetState:
    n: int = 0
    tokens: int = 0
    wall_s: float = 0.0
    joules: float = 0.0

    def frac_used(self, b: RecoveryBudget) -> float:
        parts = [self.n / max(b.n_max, 1), self.tokens / max(b.tokens_max, 1),
                 self.wall_s / max(b.wall_max_s, 1e-6)]
        return max(parts)


# --------------------------------------------------------------------------- #
# operators
# --------------------------------------------------------------------------- #

class OperatorCtx(Protocol):
    """What an operator is allowed to touch. Keep this surface small."""
    tool: str
    args: dict
    history: list
    tools_available: list
    policy: object          # the compressed LLM; call it sparingly


@dataclass
class OperatorResult:
    action: str                 # "recall" | "call_other" | "subtask" | "replan" | "stop"
    tool: str | None = None
    args: dict | None = None
    subtasks: list = field(default_factory=list)
    note: str = ""
    tokens_spent: int = 0


# -- deterministic operators (no model call) -------------------------------- #

def op_retry(ctx: OperatorCtx, *, backoff_s: float = 0.0) -> OperatorResult:
    return OperatorResult("recall", ctx.tool, dict(ctx.args),
                          note=f"retry backoff={backoff_s}s")


# Capability index: tool -> (equivalent tool, arg builder, result adapter that
# reshapes the substitute's result into the original tool's outputSchema).
# Built OFFLINE from tool semantics so substitution stays deterministic;
# sparse on purpose -- honest substitutes are rare, and pretending otherwise
# would flatter the SUBSTITUTE operator.
SUBSTITUTES: dict[str, tuple] = {
    "sensor.read": (
        "sensor.history",
        lambda args: {"device_id": args.get("device_id", ""), "n": 1},
        lambda r: {"value": r["readings"][-1]["value"], "unit": r["unit"],
                   "ts": r["readings"][-1]["ts"]} if r.get("readings") else None,
    ),
    "kv.get": (
        "kv.scan",       # existence probe only; value is NOT recoverable this way
        lambda args: {"prefix": args.get("key", "")},
        lambda r: None,  # adapter refuses: scan cannot reconstruct the value
    ),
}


def op_substitute(ctx: OperatorCtx) -> OperatorResult:
    sub = SUBSTITUTES.get(ctx.tool)
    if sub is None or sub[2] is None:
        return op_retry(ctx)                  # no honest substitute -> retry
    alt_tool, arg_fn, _adapt = sub
    return OperatorResult("call_other", alt_tool, arg_fn(ctx.args),
                          note="substitute")


def op_abstain(ctx: OperatorCtx) -> OperatorResult:
    return OperatorResult("stop", note="budget exhausted; abstaining")


# -- constrained model operators (one call, tight schema) ------------------- #

def op_reparameterize(ctx: OperatorCtx) -> OperatorResult:
    """Re-emit the SAME tool with repaired arguments, given the error payload.

    v1 is fully deterministic: apply a machine-readable rename hint (P3 schema
    drift) when the error carries one, otherwise coerce obviously miscast arg
    values. The constrained-decoding model variant (self-reflective-API result:
    structured hints beat prose diagnoses) plugs in here later without touching
    callers."""
    from .policy import drift_hint            # local: avoid module cycle
    last = ctx.history[-1] if ctx.history else {}
    args = dict(ctx.args)
    hint = drift_hint(last.get("response", {}) if isinstance(last, dict) else {})
    if hint:
        old, new = hint
        if old in args:
            args[new] = args.pop(old)
    else:
        for k, v in args.items():
            if isinstance(v, str) and v.strip().lstrip("-").replace(".", "", 1).isdigit():
                args[k] = float(v) if "." in v else int(v)
    return OperatorResult("recall", ctx.tool, args, note="reparameterize")


def op_decompose(ctx: OperatorCtx) -> OperatorResult:
    """Split into narrower calls (pagination, filters) to dodge oversize/empty."""
    args = dict(ctx.args)
    n = args.get("n")
    if isinstance(n, int) and n > 1:
        args["n"] = max(1, n // 2)
        return OperatorResult("recall", ctx.tool, args, note="decompose:halve-n")
    return OperatorResult("recall", ctx.tool, args, note="decompose:reissue")


def op_replan(ctx: OperatorCtx) -> OperatorResult:
    """Re-plan the remaining trajectory. Most expensive; last resort before
    abstain. The loop surfaces the note to the policy as an observation note --
    NOT as sentinel logic in the prompt (invariant I5): the detection decision
    was made outside the model; only the recovery instruction crosses over."""
    return OperatorResult("replan",
                          note="previous result is suspect; re-plan the "
                               "remaining steps and re-establish state")


# Independent corroboration sources: tool -> (alt tool, args builder taking the
# ORIGINAL args + suspect result, adapter reshaping alt result to orig schema).
# Default (no entry) is a fresh re-sample of the same tool, which catches
# intermittent S* corruption; the table adds genuinely independent sources.
VERIFY_ALT: dict[str, tuple] = {
    "sensor.read": (
        "sensor.history",
        lambda args, res: {"device_id": args.get("device_id", ""), "n": 1},
        lambda r: {"value": r["readings"][-1]["value"], "unit": r["unit"],
                   "ts": r["readings"][-1]["ts"]} if r.get("readings") else None,
    ),
    "cal.get": (
        "cal.list",
        lambda args, res: {"date": str(res.get("start", ""))[:10]},
        None,                                  # loop reconciles list vs get
    ),
}


def op_verify(ctx: OperatorCtx) -> OperatorResult:
    """Corroborate a suspicious value with a second, independent tool.

    This is the operator that addresses the SILENT families (S1-S4) and is the
    one most likely to be lost under aggressive compression -- it requires the
    agent to act on a suspicion rather than on an error.
    """
    last = ctx.history[-1] if ctx.history else {}
    result = {}
    if isinstance(last, dict):
        resp = last.get("response", {})
        if isinstance(resp, dict):
            result = resp.get("result", {}) or {}
    alt = VERIFY_ALT.get(ctx.tool)
    if alt is None:
        return OperatorResult("recall", ctx.tool, dict(ctx.args), note="verify:resample")
    alt_tool, arg_fn, _adapt = alt
    return OperatorResult("call_other", alt_tool, arg_fn(ctx.args, result),
                          note="verify")


OPERATORS: dict[RecoveryOp, Callable[..., OperatorResult]] = {
    RecoveryOp.RETRY: op_retry,
    RecoveryOp.RETRY_BACKOFF: lambda ctx: op_retry(ctx, backoff_s=1.0),
    RecoveryOp.REPARAMETERIZE: op_reparameterize,
    RecoveryOp.SUBSTITUTE: op_substitute,
    RecoveryOp.DECOMPOSE: op_decompose,
    RecoveryOp.REPLAN: op_replan,
    RecoveryOp.VERIFY: op_verify,
    RecoveryOp.ABSTAIN: op_abstain,
}

# Ablation presets used in Table VIII.
OPERATOR_SETS = {
    "full": list(OPERATORS.keys()),
    "retry_only": [RecoveryOp.RETRY, RecoveryOp.RETRY_BACKOFF, RecoveryOp.ABSTAIN],
    "no_verify": [k for k in OPERATORS if k is not RecoveryOp.VERIFY],
    "replan_only": [RecoveryOp.REPLAN, RecoveryOp.ABSTAIN],   # full_replan baseline
}


class RecoveryController:
    """Selects and executes an operator under budget."""

    def __init__(self, budget: RecoveryBudget, operator_set: str = "full"):
        self.budget = budget
        self.allowed = OPERATOR_SETS[operator_set]
        self.state = BudgetState()

    def step(self, ctx: OperatorCtx, op: RecoveryOp) -> OperatorResult:
        if self.budget.exhausted(self.state):
            return op_abstain(ctx)
        if op not in self.allowed:
            op = RecoveryOp.RETRY if RecoveryOp.RETRY in self.allowed else RecoveryOp.ABSTAIN
        result = OPERATORS[op](ctx)
        self.state.n += 1
        self.state.tokens += result.tokens_spent
        return result

    def reset(self) -> None:
        self.state = BudgetState()
