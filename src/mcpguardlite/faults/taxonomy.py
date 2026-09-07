"""MCP-FaultBench fault taxonomy.

Adapts the classical crash / omission / timing / value fault classification
(Avizienis et al., 2004) to the MCP JSON-RPC layer, plus an edge-resource class.

Every family declares:
  - detectability: whether the fault is visible from the protocol layer alone
  - persistence:   default temporal behaviour
  - oracle_op:     the ground-truth recovery operator (supervision + oracle baseline)

This module is pure data. The injector decides *when* a fault fires; the
transforms in `injector.py` decide *what* it does to the payload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FaultClass(str, Enum):
    TRANSPORT = "T"
    PROTOCOL = "P"
    SEMANTIC = "S"
    RESOURCE = "R"


class Detectability(str, Enum):
    OVERT = "overt"    # visible in the JSON-RPC envelope / schema check
    SILENT = "silent"  # well-formed but wrong -> requires model or verifier


class Persistence(str, Enum):
    TRANSIENT = "transient"        # fires once, next call is clean
    INTERMITTENT = "intermittent"  # fires with probability p on each call
    PERSISTENT = "persistent"      # fires on every call for the rest of episode


class RecoveryOp(str, Enum):
    RETRY = "retry"
    RETRY_BACKOFF = "retry_backoff"
    REPARAMETERIZE = "reparameterize"
    SUBSTITUTE = "substitute"
    DECOMPOSE = "decompose"
    REPLAN = "replan"
    VERIFY = "verify"
    ESCALATE = "escalate"
    ABSTAIN = "abstain"
    NOOP = "noop"


@dataclass(frozen=True)
class FaultFamily:
    code: str
    fclass: FaultClass
    name: str
    detectability: Detectability
    oracle_op: RecoveryOp
    default_persistence: Persistence
    description: str
    # knobs the injector may sample, e.g. {"delay_ms": (500, 30000)}
    params: dict = field(default_factory=dict)


TAXONOMY: dict[str, FaultFamily] = {
    # ---------------------------------------------------------- T. Transport
    "T1": FaultFamily(
        "T1", FaultClass.TRANSPORT, "server_unreachable",
        Detectability.OVERT, RecoveryOp.SUBSTITUTE, Persistence.PERSISTENT,
        "Connection refused / DNS failure for the whole episode.",
    ),
    "T2": FaultFamily(
        "T2", FaultClass.TRANSPORT, "timeout",
        Detectability.OVERT, RecoveryOp.RETRY_BACKOFF, Persistence.INTERMITTENT,
        "Response delayed beyond the client deadline.",
        {"delay_ms": (500, 30000)},
    ),
    "T3": FaultFamily(
        "T3", FaultClass.TRANSPORT, "connection_reset",
        Detectability.OVERT, RecoveryOp.RETRY, Persistence.TRANSIENT,
        "Transport drops mid-response.",
    ),
    "T4": FaultFamily(
        "T4", FaultClass.TRANSPORT, "partial_stream",
        Detectability.OVERT, RecoveryOp.RETRY, Persistence.TRANSIENT,
        "Streamed result truncated at a byte boundary; JSON does not close.",
        {"truncate_frac": (0.2, 0.9)},
    ),
    # ----------------------------------------------------------- P. Protocol
    "P1": FaultFamily(
        "P1", FaultClass.PROTOCOL, "jsonrpc_error",
        Detectability.OVERT, RecoveryOp.REPARAMETERIZE, Persistence.INTERMITTENT,
        "Server returns a JSON-RPC error object (invalid params, internal error).",
        {"code": [-32602, -32603, -32000]},
    ),
    "P2": FaultFamily(
        "P2", FaultClass.PROTOCOL, "malformed_json",
        Detectability.OVERT, RecoveryOp.RETRY, Persistence.TRANSIENT,
        "Payload is not parseable JSON (encoding corruption).",
    ),
    "P3": FaultFamily(
        "P3", FaultClass.PROTOCOL, "schema_drift",
        Detectability.OVERT, RecoveryOp.REPARAMETERIZE, Persistence.PERSISTENT,
        "Advertised tool schema changed: a parameter was renamed or removed.",
    ),
    "P4": FaultFamily(
        "P4", FaultClass.PROTOCOL, "tool_vanished",
        Detectability.OVERT, RecoveryOp.SUBSTITUTE, Persistence.PERSISTENT,
        "Tool present in tools/list is gone by the time it is called.",
    ),
    "P5": FaultFamily(
        "P5", FaultClass.PROTOCOL, "missing_required_field",
        Detectability.OVERT, RecoveryOp.REPARAMETERIZE, Persistence.INTERMITTENT,
        "Result object omits a field the declared output schema requires.",
    ),
    # ----------------------------------------------------------- S. Semantic
    "S1": FaultFamily(
        "S1", FaultClass.SEMANTIC, "stale_value",
        Detectability.SILENT, RecoveryOp.VERIFY, Persistence.INTERMITTENT,
        "Well-formed result carrying an out-of-date value.",
        {"staleness_steps": (1, 10)},
    ),
    "S2": FaultFamily(
        "S2", FaultClass.SEMANTIC, "unit_or_type_mismatch",
        Detectability.SILENT, RecoveryOp.VERIFY, Persistence.INTERMITTENT,
        "Value correct in magnitude but wrong unit/type (C vs F, str vs int).",
    ),
    "S3": FaultFamily(
        "S3", FaultClass.SEMANTIC, "empty_as_success",
        Detectability.SILENT, RecoveryOp.DECOMPOSE, Persistence.INTERMITTENT,
        "Empty result set returned with a success status.",
    ),
    "S4": FaultFamily(
        "S4", FaultClass.SEMANTIC, "cross_tool_contradiction",
        Detectability.SILENT, RecoveryOp.VERIFY, Persistence.INTERMITTENT,
        "Two tools return mutually inconsistent facts about the same entity.",
    ),
    # ----------------------------------------------------------- R. Resource
    "R1": FaultFamily(
        "R1", FaultClass.RESOURCE, "oversized_result",
        Detectability.OVERT, RecoveryOp.DECOMPOSE, Persistence.INTERMITTENT,
        "Result exceeds the remaining context budget.",
        {"inflate_x": (5, 100)},
    ),
    "R2": FaultFamily(
        "R2", FaultClass.RESOURCE, "thermal_degradation",
        Detectability.OVERT, RecoveryOp.RETRY_BACKOFF, Persistence.PERSISTENT,
        "Sustained latency inflation emulating thermal throttling.",
        {"slowdown_x": (1.5, 6.0)},
    ),
    "R3": FaultFamily(
        "R3", FaultClass.RESOURCE, "memory_eviction",
        Detectability.OVERT, RecoveryOp.REPLAN, Persistence.TRANSIENT,
        "Server-side session/cache evicted; prior context invalid.",
    ),
}

SILENT_FAMILIES = [c for c, f in TAXONOMY.items()
                   if f.detectability is Detectability.SILENT]
OVERT_FAMILIES = [c for c, f in TAXONOMY.items()
                  if f.detectability is Detectability.OVERT]


def by_class(fclass: FaultClass) -> list[FaultFamily]:
    return [f for f in TAXONOMY.values() if f.fclass is fclass]
