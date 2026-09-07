"""Environment-specific semantic mutators for the SILENT fault families.

These cannot be generic: making a result "stale but plausible" requires knowing
what the field means. Each server registers mutators for S1-S4 here.

This file is the single highest-risk piece of the harness. If the silent faults
are trivially detectable (wrong type, absurd magnitude), RQ3 is invalid. Every
mutator must produce output that passes JSON-Schema validation and a
reasonableness check, and each should be spot-audited by hand (R3: 50 sampled
mutations per environment before the full run).

Contract:
    fn(result, *, params, server, tool, args, salt) -> mutated result dict
  - `result` is the nominal RESULT object (not the JSON-RPC envelope). Never
    mutate in place; return a new dict.
  - Output MUST validate against the tool's outputSchema (invariant I4) and
    must stay plausible in magnitude/format.
  - Determinism: any free choice is derived from `salt` via the injector PRF,
    never from `random` module state.

Applicability is per-OP and is consulted by the SCHEDULER (FaultScheduler
.decide), so an inapplicable silent family never "fires" as a no-op and never
pollutes the fault-present labels. The map below is therefore part of the
frozen fault-schedule function: changing it changes schedules (I1) -- do not
edit after data generation begins.
"""
from __future__ import annotations

from typing import Callable

MUTATORS: dict[tuple[str, str], Callable] = {}   # (env, family) -> fn

# (env, family) -> ops the mutation is meaningful for. Consulted by the
# scheduler through `applicable()` BEFORE a silent family may fire.
SILENT_OPS: dict[tuple[str, str], set[str]] = {
    ("fs", "S1"): {"read"},
    ("fs", "S2"): {"read"},
    ("fs", "S3"): {"list", "search"},
    ("fs", "S4"): {"stat"},
    ("kv", "S1"): {"get"},
    ("kv", "S2"): {"get", "getv"},
    ("kv", "S3"): {"scan"},
    ("kv", "S4"): {"get", "getv"},
    ("http", "S1"): {"fetch"},
    ("http", "S2"): {"fetch"},
    ("http", "S3"): {"fetch", "links"},
    ("http", "S4"): {"head"},
    ("cal", "S1"): {"get"},
    ("cal", "S2"): {"get", "list"},
    ("cal", "S3"): {"list", "free"},
    ("cal", "S4"): {"list"},
    ("sensor", "S1"): {"read"},
    ("sensor", "S2"): {"read", "history"},
    ("sensor", "S3"): {"history"},
    ("sensor", "S4"): {"read"},
    ("compute", "S1"): {"stats"},
    ("compute", "S2"): {"convert"},
    ("compute", "S3"): {"stats"},
    ("compute", "S4"): {"calc"},
}


def applicable(family: str, tool: str) -> bool:
    """Can this silent family meaningfully mutate this tool's result?
    Overt families are always applicable (they attack the envelope)."""
    if not family.startswith("S"):
        return True
    env, _, op = tool.partition(".")
    return op in SILENT_OPS.get((env, family), set())


def register(env: str, family: str):
    def deco(fn):
        MUTATORS[(env, family)] = fn
        return fn
    return deco


def _unit(*parts) -> float:
    from ..faults.injector import prf_unit    # lazy: avoids an import cycle
    return prf_unit("mut", *parts)


def _choice(seq, *parts):
    return seq[int(_unit(*parts) * len(seq)) % len(seq)]


def _op(tool: str) -> str:
    return tool.split(".", 1)[-1]


def _stale_k(params: dict, available: int) -> int:
    """How many steps back to go: taxonomy samples staleness_steps in (1,10);
    clip to the history actually available (server generators guarantee >=2)."""
    k = int(params.get("staleness_steps", 1))
    return max(1, min(k, available - 1))


def _decimalize(text: str, salt) -> str:
    """Reformat ONE integer >=100 in the text as a European-style decimal
    ('4821' -> '4.821'). Format-level corruption: same type, same field, wrong
    parse -- the classic locale bug."""
    import re
    nums = [m for m in re.finditer(r"\d{3,}", text)]
    if not nums:
        return text
    m = _choice(nums, salt, "decimalize")
    s = m.group()
    cut = len(s) - 3 if len(s) > 3 else 1
    return text[:m.start()] + s[:cut] + "." + s[cut:] + text[m.end():]


def _perturb(value: float, salt, lo=0.03, hi=0.12) -> float:
    """A plausible-magnitude wrong number: off by 3-12%, sign PRF-chosen."""
    frac = lo + (hi - lo) * _unit(salt, "frac")
    sign = 1.0 if _unit(salt, "sign") < 0.5 else -1.0
    out = value * (1.0 + sign * frac)
    return round(out, 2) if isinstance(value, float) else int(round(out)) or value


# --------------------------------------------------------------------------- #
# fs
# --------------------------------------------------------------------------- #

@register("fs", "S1")
def fs_stale(result, *, params, server, tool, args, salt):
    f = server.files.get(args.get("path", ""))
    if not f or len(f["versions"]) < 2:
        return dict(result)
    k = _stale_k(params, len(f["versions"]))
    return {**result, "content": f["versions"][-1 - k],
            "version": len(f["versions"]) - k}


@register("fs", "S2")
def fs_type(result, *, params, server, tool, args, salt):
    return {**result, "content": _decimalize(result["content"], salt)}


@register("fs", "S3")
def fs_empty(result, *, params, server, tool, args, salt):
    if _op(tool) == "list":
        return {**result, "entries": [], "count": 0}
    return {**result, "matches": [], "total": 0}


@register("fs", "S4")
def fs_contradict(result, *, params, server, tool, args, salt):
    out = dict(result)
    out["size"] = max(1, _perturb(result["size"], salt))
    if result.get("version", 0) > 1:
        out["version"] = result["version"] - 1
    return out


# --------------------------------------------------------------------------- #
# kv
# --------------------------------------------------------------------------- #

@register("kv", "S1")
def kv_stale(result, *, params, server, tool, args, salt):
    e = server.store.get(args.get("key", ""))
    if not e or len(e["versions"]) < 2:
        return dict(result)
    k = _stale_k(params, len(e["versions"]))
    return {"value": e["versions"][-1 - k], "version": len(e["versions"]) - k}


@register("kv", "S2")
def kv_type(result, *, params, server, tool, args, salt):
    v = result["value"]
    if isinstance(v, bool):
        return dict(result)
    if isinstance(v, int):
        s = f"{v:,}" if v >= 1000 else str(v)        # '1,234' misparses as 1
        return {**result, "value": s}
    if isinstance(v, dict) and isinstance(v.get("quota"), int):
        q = v["quota"]
        return {**result, "value": {**v, "quota": f"{q:,}" if q >= 1000 else str(q)}}
    return dict(result)


@register("kv", "S3")
def kv_empty(result, *, params, server, tool, args, salt):
    return {**result, "keys": [], "count": 0}


@register("kv", "S4")
def kv_contradict(result, *, params, server, tool, args, salt):
    v = result["value"]
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return {**result, "value": _perturb(v, salt)}
    if isinstance(v, dict) and isinstance(v.get("quota"), (int, float)):
        return {**result, "value": {**v, "quota": _perturb(v["quota"], salt)}}
    return dict(result)


# --------------------------------------------------------------------------- #
# http
# --------------------------------------------------------------------------- #

@register("http", "S1")
def http_stale(result, *, params, server, tool, args, salt):
    p = server.pages.get(args.get("url", ""))
    if not p or len(p["snapshots"]) < 2:
        return dict(result)
    k = _stale_k(params, len(p["snapshots"]))
    return {**result, "body": p["snapshots"][-1 - k]}


@register("http", "S2")
def http_type(result, *, params, server, tool, args, salt):
    body = result["body"]
    if isinstance(body, dict):
        out = dict(body)
        for key in ("count", "score"):
            v = out.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[key] = f"{v:,}" if v >= 1000 else str(v)
        return {**result, "body": out}
    if isinstance(body, str):
        return {**result, "body": _decimalize(body, salt)}
    return dict(result)


@register("http", "S3")
def http_empty(result, *, params, server, tool, args, salt):
    if _op(tool) == "links":
        return {**result, "links": [], "count": 0}
    body = result["body"]
    empty = {} if isinstance(body, dict) else ([] if isinstance(body, list) else "")
    return {**result, "body": empty}


@register("http", "S4")
def http_contradict(result, *, params, server, tool, args, salt):
    return {**result, "content_length": max(1, _perturb(result["content_length"], salt))}


# --------------------------------------------------------------------------- #
# cal
# --------------------------------------------------------------------------- #

def _shift_time(iso: str, hours: int) -> str:
    """Shift 'YYYY-MM-DDTHH:MM' by whole hours, clamped to the same day
    (a cross-midnight shift would be an implausible listing)."""
    h = int(iso[11:13]) + hours
    h = max(0, min(23, h))
    return f"{iso[:11]}{h:02d}{iso[13:]}"


@register("cal", "S1")
def cal_stale(result, *, params, server, tool, args, salt):
    e = server.events.get(args.get("event_id", ""))
    if not e or not e.get("history"):
        return dict(result)
    old = e["history"][0]
    dur_h = int(e["end"][11:13]) - int(e["start"][11:13])
    old_end = _shift_time(old, dur_h)[:14] + e["end"][14:]   # keep minutes of real end
    return {**result, "start": old, "end": old_end}


@register("cal", "S2")
def cal_tz(result, *, params, server, tool, args, salt):
    shift = _choice([-5, -6, 4, 5], salt, "tz")     # classic tz-offset misrender
    if _op(tool) == "get":
        return {**result, "start": _shift_time(result["start"], shift),
                "end": _shift_time(result["end"], shift)}
    evs = [{**ev, "start": _shift_time(ev["start"], shift),
            "end": _shift_time(ev["end"], shift)} for ev in result["events"]]
    return {**result, "events": evs}


@register("cal", "S3")
def cal_empty(result, *, params, server, tool, args, salt):
    if _op(tool) == "free":
        return {**result, "slots": [], "count": 0}
    return {**result, "events": [], "count": 0}


@register("cal", "S4")
def cal_contradict(result, *, params, server, tool, args, salt):
    if not result["events"]:
        return dict(result)
    evs = [dict(ev) for ev in result["events"]]
    i = int(_unit(salt, "which") * len(evs)) % len(evs)
    evs[i]["start"] = _shift_time(evs[i]["start"], _choice([-1, 1], salt, "dir"))
    return {**result, "events": evs}


# --------------------------------------------------------------------------- #
# sensor
# --------------------------------------------------------------------------- #

_UNIT_CONFUSION = {
    # kind -> plausible wrong-unit rendering of a correct value (label unchanged)
    "temp": lambda v: round(v * 9 / 5 + 32, 2),       # C reported as F
    "humidity": lambda v: round(v / 100, 4),          # percent as fraction
    "pressure": lambda v: round(v / 10, 2),           # hPa as kPa
    "light": lambda v: round(v / 1000, 4),            # lux as klux
}


@register("sensor", "S1")
def sensor_stale(result, *, params, server, tool, args, salt):
    dev = args.get("device_id", "")
    if dev not in server.devices:
        return dict(result)
    k = _stale_k(params, server._N_READINGS)
    return {**result, "value": server._reading(dev, server._N_READINGS - 1 - k)}


@register("sensor", "S2")
def sensor_unit(result, *, params, server, tool, args, salt):
    dev = server.devices.get(args.get("device_id", ""))
    if dev is None:
        return dict(result)
    conv = _UNIT_CONFUSION[dev["kind"]]
    if _op(tool) == "read":
        return {**result, "value": conv(result["value"])}
    return {**result,
            "readings": [{**r, "value": conv(r["value"])} for r in result["readings"]]}


@register("sensor", "S3")
def sensor_empty(result, *, params, server, tool, args, salt):
    return {**result, "readings": [], "count": 0}


@register("sensor", "S4")
def sensor_contradict(result, *, params, server, tool, args, salt):
    dev = server.devices.get(args.get("device_id", ""))
    sig = dev["sig"] if dev else 1.0
    off = sig * (0.4 + 0.5 * _unit(salt, "off"))
    sign = 1.0 if _unit(salt, "sgn") < 0.5 else -1.0
    return {**result, "value": round(result["value"] + sign * off, 2)}


# --------------------------------------------------------------------------- #
# compute
# --------------------------------------------------------------------------- #

@register("compute", "S1")
def compute_stale(result, *, params, server, tool, args, salt):
    vals = [float(v) for v in args.get("values", [])]
    if len(vals) < 2:
        return dict(result)
    sub = vals[:-1]                                   # aggregate over a stale subset
    op = args.get("op", "mean")
    agg = {"mean": sum(sub) / len(sub), "max": max(sub),
           "min": min(sub), "sum": sum(sub)}.get(op, result["value"])
    return {"value": round(agg, 6), "n": len(sub)}


@register("compute", "S2")
def compute_noconvert(result, *, params, server, tool, args, salt):
    # conversion silently not applied: input value echoed under the target label
    return {**result, "value": round(float(args.get("value", result["value"])), 6)}


@register("compute", "S3")
def compute_empty(result, *, params, server, tool, args, salt):
    return {"value": 0.0, "n": 0}


@register("compute", "S4")
def compute_offby(result, *, params, server, tool, args, salt):
    return {**result, "value": round(_perturb(float(result["value"]), salt,
                                              lo=0.01, hi=0.05), 6)}
