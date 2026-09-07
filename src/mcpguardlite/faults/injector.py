"""Seeded, replayable fault scheduling.

The single most important property in this file: fault decisions must be a pure
function of (seed, episode_id, turn, tool_name, family). That is what makes the
compression grid a *paired* experiment -- Q4_K_M and FP16 encounter the same
faults at the same turns, so RCG measures the model and not the dice.

Never use `random` module-level state here. Never use wall-clock time.
"""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass, asdict
from typing import Any

from .taxonomy import TAXONOMY, FaultFamily, Persistence, RecoveryOp
from ..envs.mutators import MUTATORS, applicable

# Persistence scope: a latched P3/P4 keeps firing for the ORIGINAL tool only
# (a drifted schema does not vanish other tools); T1/R2 are server-wide.
FAMILY_SCOPE = {"P3": "tool", "P4": "tool"}


# --------------------------------------------------------------------------- #
# deterministic PRF
# --------------------------------------------------------------------------- #

def _prf_u64(*parts: Any) -> int:
    """Pseudo-random function -> 64-bit int. Stable across machines/Python runs."""
    payload = "\x1f".join(str(p) for p in parts).encode()
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return struct.unpack("<Q", digest)[0]


def prf_unit(*parts: Any) -> float:
    """Deterministic uniform in [0, 1)."""
    return _prf_u64(*parts) / 2.0 ** 64


def prf_range(lo: float, hi: float, *parts: Any) -> float:
    return lo + (hi - lo) * prf_unit(*parts)


def prf_choice(seq, *parts: Any):
    return seq[_prf_u64(*parts) % len(seq)]


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

@dataclass
class FaultConfig:
    """One point in the fault-process design space."""
    families: list[str]              # e.g. ["T2", "P1", "S1"]
    rate: float = 0.15               # per-tool-call probability of firing
    persistence_override: str | None = None
    seed: int = 0
    max_faults_per_episode: int = 3

    @classmethod
    def from_yaml(cls, path: str) -> "FaultConfig":
        import yaml
        with open(path) as fh:
            return cls(**yaml.safe_load(fh))

    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True).encode()
        ).hexdigest()[:12]


@dataclass
class FaultEvent:
    """A fault decision. Logged verbatim into the trace."""
    episode_id: str
    turn: int
    tool: str
    family: str
    fired: bool
    persistent_from: int | None
    params: dict
    oracle_op: RecoveryOp

    def to_json(self) -> dict:
        d = asdict(self)
        d["oracle_op"] = self.oracle_op.value
        return d


# --------------------------------------------------------------------------- #
# scheduler
# --------------------------------------------------------------------------- #

class FaultScheduler:
    """Decides whether a fault fires on a given (episode, turn, tool).

    Stateful only for persistence bookkeeping, and that state is itself
    reconstructible from the seed -- so a replay from the trace is exact.
    """

    def __init__(self, cfg: FaultConfig):
        self.cfg = cfg
        # (episode, family) -> (first turn, tool it latched on)
        self._latched: dict[tuple[str, str], tuple[int, str]] = {}
        self._counts: dict[str, int] = {}

    def _persistence(self, fam: FaultFamily) -> Persistence:
        return Persistence(self.cfg.persistence_override
                           or fam.default_persistence.value)

    # ---------------------------------------------------------------- public
    def decide(self, episode_id: str, turn: int, tool: str) -> FaultEvent | None:
        # A latched persistent fault keeps firing past the per-episode cap:
        # it is ONE fault that lasts, not a new fault per call.
        for family in self.cfg.families:
            fam = TAXONOMY[family]
            latch_key = (episode_id, family)
            if (self._persistence(fam) is Persistence.PERSISTENT
                    and latch_key in self._latched):
                turn0, tool0 = self._latched[latch_key]
                if FAMILY_SCOPE.get(family) == "tool" and tool != tool0:
                    continue
                if not applicable(family, tool):
                    continue
                return self._emit(episode_id, turn, tool, fam,
                                  persistent_from=turn0)

        if self._counts.get(episode_id, 0) >= self.cfg.max_faults_per_episode:
            return None

        for family in self.cfg.families:
            fam = TAXONOMY[family]
            # Silent families fire only where an env mutator can act; the
            # applicability map is pure data over the tool name, so the
            # schedule stays a pure function of (seed, episode, turn, tool).
            if not applicable(family, tool):
                continue
            u = prf_unit(self.cfg.seed, episode_id, turn, tool, family)
            if u < self.cfg.rate:
                if self._persistence(fam) is Persistence.PERSISTENT:
                    self._latched[(episode_id, family)] = (turn, tool)
                self._counts[episode_id] = self._counts.get(episode_id, 0) + 1
                return self._emit(episode_id, turn, tool, fam, persistent_from=None)
        return None

    def reset_episode(self, episode_id: str) -> None:
        self._latched = {k: v for k, v in self._latched.items() if k[0] != episode_id}
        self._counts.pop(episode_id, None)

    # --------------------------------------------------------------- private
    def _emit(self, episode_id, turn, tool, fam: FaultFamily,
              persistent_from: int | None) -> FaultEvent:
        params = {}
        for key, spec in fam.params.items():
            if isinstance(spec, tuple):
                params[key] = prf_range(spec[0], spec[1],
                                        self.cfg.seed, episode_id, turn, key)
            elif isinstance(spec, list):
                params[key] = prf_choice(spec, self.cfg.seed, episode_id, turn, key)
        return FaultEvent(
            episode_id=episode_id, turn=turn, tool=tool, family=fam.code,
            fired=True, persistent_from=persistent_from, params=params,
            oracle_op=fam.oracle_op,
        )


# --------------------------------------------------------------------------- #
# payload transforms
# --------------------------------------------------------------------------- #

# families whose transform needs a nominal "result" object to corrupt
RESULT_FAMILIES = frozenset({"S1", "S2", "S3", "S4", "P5", "R1"})


def drift_rename(server, tool: str) -> tuple[str, str] | None:
    """Deterministic P3 rename for a tool: first required input param -> *_v2."""
    for t in getattr(server, "TOOLS", []):
        if t["name"] == tool:
            req = t["inputSchema"].get("required") or []
            if req:
                return req[0], req[0] + "_v2"
    return None


def apply_fault(response: dict, event: FaultEvent, *, ctx: dict | None = None) -> dict:
    """Transform a nominal JSON-RPC response according to the fault family.

    Transforms are *total*: every branch returns something the client can
    actually receive (malformed bytes ride in a `__raw_bytes__` sentinel so the
    transport layer can emit them faithfully) or raises a transport-level
    exception the proxy converts to a `__transport_error__` envelope.

    `ctx` (from the proxy): {"args", "tool", "env", "server"}. The S* branches
    dispatch to envs/mutators.py and mutate only the "result" member, keeping
    the envelope intact -- silence lives inside a well-formed response (I4).
    """
    fam = event.family
    ctx = ctx or {}

    if fam == "T1":
        raise ConnectionRefusedError(f"guardlite: {event.tool} unreachable")
    if fam == "T2":
        raise TimeoutError(f"guardlite: {event.tool} timed out")
    if fam == "T3":
        raise ConnectionResetError("guardlite: reset mid-stream")
    if fam == "T4":
        raw = json.dumps(response)
        cut = int(len(raw) * event.params.get("truncate_frac", 0.5))
        return {"__raw_bytes__": raw[:cut]}          # deliberately unparseable
    if fam == "P1":
        return {"jsonrpc": "2.0", "id": response.get("id"),
                "error": {"code": int(event.params.get("code", -32603)),
                          "message": "guardlite injected error"}}
    if fam == "P2":
        return {"__raw_bytes__": json.dumps(response)[:-1] + "\x00}"}
    if fam == "P3":
        rename = drift_rename(ctx.get("server"), event.tool)
        old, new = rename if rename else ("param", "param_v2")
        return {"jsonrpc": "2.0", "id": response.get("id"),
                "error": {"code": -32602,
                          "message": f"Invalid params: unknown parameter '{old}'"
                                     f" (schema revision expects '{new}')"}}
    if fam == "P4":
        return {"jsonrpc": "2.0", "id": response.get("id"),
                "error": {"code": -32601, "message": "Method not found"}}
    if fam == "P5":
        result = dict(response.get("result", {}))
        server = ctx.get("server")
        schema = server.output_schema(event.tool) if server else None
        required = sorted((schema or {}).get("required") or list(result) or ["x"])
        victim = prf_choice(required, event.episode_id, event.turn, "P5")
        result.pop(victim, None)
        return {**response, "result": result}
    if fam in ("S1", "S2", "S3", "S4"):
        env = ctx.get("env") or event.tool.split(".", 1)[0]
        mut = MUTATORS[(env, fam)]
        salt = (event.episode_id, event.turn, event.tool)
        mutated = mut(dict(response.get("result", {})),
                      params=event.params, server=ctx.get("server"),
                      tool=event.tool, args=ctx.get("args", {}), salt=salt)
        return {**response, "result": mutated}
    if fam == "R1":
        result = dict(response.get("result", {}))
        x = int(event.params.get("inflate_x", 10))
        blob = json.dumps(result, sort_keys=True)
        result["__debug_dump__"] = blob * max(1, x)   # overt oversize, valid JSON
        return {**response, "result": result}
    if fam == "R2":
        return response          # latency inflation is applied by the proxy
    if fam == "R3":
        return {"jsonrpc": "2.0", "id": response.get("id"),
                "error": {"code": -32001,
                          "message": "session evicted: server state reset, "
                                     "re-establish context"}}

    return response
