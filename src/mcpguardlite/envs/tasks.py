"""Task suite + programmatic verifier.

Design goal (HANDOFF §6 R5): >=70% of tasks are judged programmatically. Here it
is 100%: every task carries a gold plan replayable on a clean server, and the
verifier compares (a) the final `state_digest()` against the digest produced by
the gold replay and (b) the agent's answer against the gold answer derived by a
tiny deterministic extraction VM. No LLM judge anywhere in the loop.

The same extraction spec is applied by the ScriptedPolicy to its OBSERVED
responses -- so a silent fault corrupts the scripted agent's answer exactly the
way it would corrupt a model's, and SFR is measurable end-to-end without a GPU.

Tiers (trace schema field `tier`):
    single      one tool call answers the task
    sequential  2-3 independent calls whose results combine
    dependent   a later call's args come from an earlier call's result
    verify      the task explicitly requires cross-checking two sources
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .servers import ToolError, extract_number, extract_path, make_server


# --------------------------------------------------------------------------- #
# task record
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Task:
    task_id: str
    env: str
    tier: str                      # single | sequential | dependent | verify
    instruction: str
    gold_plan: tuple = ()          # ((tool, args_template), ...)
    answer_spec: tuple = ()        # extraction VM program (see derive_answer)
    mutates_state: bool = False    # if True, verify by digest comparison


# --------------------------------------------------------------------------- #
# arg templates: {"$from": turn_idx, "$field": "content", "$extract": "path"}
# --------------------------------------------------------------------------- #

def resolve_args(template: dict, responses: list[dict]) -> dict:
    """Fill argument placeholders from earlier responses. Deterministic; raises
    ToolError when the referenced field is unusable (so a faulted upstream
    response surfaces as a failed call, not a crash)."""
    out = {}
    for k, v in template.items():
        if isinstance(v, dict) and "$from" in v:
            try:
                src = responses[v["$from"]]
                val = _dig(src, v.get("$field", ""))
            except (IndexError, KeyError, TypeError) as e:
                raise ToolError(-32602, f"unresolvable arg {k}: {e}") from e
            ex = v.get("$extract")
            if ex == "path":
                val = extract_path(val)
            elif ex == "number":
                val = extract_number(val)
            elif ex == "date":
                val = str(val)[:10]
            if val is None:
                raise ToolError(-32602, f"arg {k}: extraction '{ex}' found nothing")
            if "$suffix" in v:
                val = str(val) + v["$suffix"]
            out[k] = val
        else:
            out[k] = v
    return out


def _dig(obj, path: str):
    if not path:
        return obj
    cur = obj
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


# --------------------------------------------------------------------------- #
# answer derivation VM
# --------------------------------------------------------------------------- #

def derive_answer(responses: list[dict], spec: tuple):
    """Stack machine over the per-turn RESULT objects.

    ops:
      ("get", t, "a.b.0")      push responses[t] field
      ("num",)                 pop str -> first number in it
      ("count",)               pop list -> its length
      ("agg", "max|min|sum|mean")  pop list of numbers -> aggregate
      ("pair", n)              pop n values -> push them as one list
      ("round", nd)            round top of stack
      ("const", v)             push a literal
    Returns the single remaining value, or None when any step is unusable
    (that is the scripted agent 'trusting' a corrupted observation upstream).
    """
    stack: list = []
    try:
        for op in spec:
            kind = op[0]
            if kind == "get":
                stack.append(_dig(responses[op[1]], op[2]))
            elif kind == "num":
                stack.append(extract_number(stack.pop()))
            elif kind == "count":
                stack.append(len(stack.pop()))
            elif kind == "agg":
                vals = [float(v) for v in stack.pop()]
                stack.append({"max": max, "min": min, "sum": sum,
                              "mean": lambda x: sum(x) / len(x)}[op[1]](vals))
            elif kind == "pair":
                n = op[1]
                vals, stack = stack[-n:], stack[:-n]
                stack.append(vals)
            elif kind == "round":
                stack.append(round(float(stack.pop()), op[1]))
            elif kind == "const":
                stack.append(op[1])
        return stack[-1] if stack else None
    except Exception:
        return None


def answers_match(got, gold) -> bool:
    if got is None or gold is None:
        return got is gold
    if isinstance(gold, (int, float)) and not isinstance(gold, bool):
        num = extract_number(got) if isinstance(got, str) else got
        try:
            return math.isclose(float(num), float(gold), rel_tol=1e-4, abs_tol=1e-6)
        except (TypeError, ValueError):
            return False
    if isinstance(gold, list):
        return isinstance(got, list) and sorted(map(str, got)) == sorted(map(str, gold))
    return str(got).strip().casefold() == str(gold).strip().casefold()


# --------------------------------------------------------------------------- #
# gold replay + verification
# --------------------------------------------------------------------------- #

@dataclass
class Gold:
    digest: str
    answer: object
    responses: list = field(default_factory=list)


def replay_gold(task: Task, seed: int) -> Gold:
    """Run the gold plan on a CLEAN server; return target digest + gold answer."""
    server = make_server(task.env, seed)
    responses: list[dict] = []
    for tool, template in task.gold_plan:
        args = resolve_args(template, responses)
        responses.append(server.call_tool(tool, args))
    answer = derive_answer(responses, task.answer_spec) if task.answer_spec else "done"
    return Gold(digest=server.state_digest(), answer=answer, responses=responses)


def verify_episode(task: Task, seed: int, final_digest: str, answer) -> bool:
    gold = replay_gold(task, seed)
    if task.mutates_state and final_digest != gold.digest:
        return False
    if task.answer_spec:
        return answers_match(answer, gold.answer)
    return True


# --------------------------------------------------------------------------- #
# task generators (deterministic; parameterized only by env + index)
# --------------------------------------------------------------------------- #
# Entities referenced in templates are chosen by INDEX into the sorted entity
# list of a seed-0 server, so task text is stable while remaining valid for any
# episode seed (all seeds generate the same entity IDS, different content).

def _fs_entities():
    s = make_server("fs", 0)
    return sorted(p for p in s.files if p != "/notes/pointer_0.txt")


def _kv_entities():
    s = make_server("kv", 0)
    return sorted(s.store)


def _cal_days():
    return [f"2026-09-{d:02d}" for d in range(8, 12)]


def _cal_ids():
    s = make_server("cal", 0)
    return sorted(s.events)


def build_tasks(env: str, n: int) -> list[Task]:
    """The first `n` tasks for an env. Templates cycle through tiers so any
    prefix of the suite is tier-balanced."""
    makers = {"fs": _fs_task, "kv": _kv_task, "http": _http_task,
              "cal": _cal_task, "sensor": _sensor_task, "compute": _compute_task}
    return [makers[env](i) for i in range(n)]


def _fs_task(i: int) -> Task:
    files = _fs_entities()
    f = files[i % len(files)]
    g = files[(i + 3) % len(files)]
    tid = f"fs-{i:03d}"
    variant = i % 4
    if variant == 0:
        return Task(tid, "fs", "single",
                    f"Read the file {f} and report the number mentioned in it. "
                    "Answer with the number only.",
                    (("fs.read", {"path": f}),),
                    (("get", 0, "content"), ("num",)))
    if variant == 1:
        return Task(tid, "fs", "sequential",
                    f"Find the sizes of {f} and {g} and report the larger size. "
                    "Answer with the number only.",
                    (("fs.stat", {"path": f}), ("fs.stat", {"path": g})),
                    (("get", 0, "size"), ("get", 1, "size"), ("pair", 2), ("agg", "max")))
    if variant == 2:
        return Task(tid, "fs", "dependent",
                    "Read /notes/pointer_0.txt, open the file it points to, and "
                    "report the number mentioned there. Answer with the number only.",
                    (("fs.read", {"path": "/notes/pointer_0.txt"}),
                     ("fs.read", {"path": {"$from": 0, "$field": "content",
                                           "$extract": "path"}})),
                    (("get", 1, "content"), ("num",)))
    return Task(tid, "fs", "verify",
                f"Read {f}, then confirm via fs.stat that the version you saw is "
                "current, and report that version. Answer with the number only.",
                (("fs.read", {"path": f}), ("fs.stat", {"path": f})),
                (("get", 1, "version"),))


def _kv_task(i: int) -> Task:
    keys = _kv_entities()
    k = keys[i % len(keys)]
    k2 = keys[(i + 5) % len(keys)]
    ns = k.split(":")[0]
    tid = f"kv-{i:03d}"
    variant = i % 4
    if variant == 0:
        return Task(tid, "kv", "single",
                    f"Get the current value stored at key '{k}' and report the "
                    "number in it. Answer with the number only.",
                    (("kv.get", {"key": k}),),
                    (("get", 0, "value"), ("num",)))
    if variant == 1:
        return Task(tid, "kv", "sequential",
                    f"Count the keys under the '{ns}:' prefix, then store that "
                    f"count at key 'report:{ns}_count'. Then answer with the count.",
                    (("kv.scan", {"prefix": ns + ":"}),
                     ("kv.set", {"key": f"report:{ns}_count",
                                 "value": {"$from": 0, "$field": "count"}})),
                    (("get", 0, "count"),), mutates_state=True)
    if variant == 2:
        return Task(tid, "kv", "dependent",
                    f"Read the current version number of key '{k}', then fetch "
                    "version 1 of the same key and report the number in THAT value. "
                    "Answer with the number only.",
                    (("kv.get", {"key": k}),
                     ("kv.getv", {"key": k, "version": 1})),
                    (("get", 1, "value"), ("num",)))
    return Task(tid, "kv", "verify",
                f"Get the value at '{k2}' and cross-check it by fetching its "
                "latest version explicitly with kv.getv; report the version "
                "number both agree on. Answer with the number only.",
                (("kv.get", {"key": k2}),
                 ("kv.getv", {"key": k2, "version": {"$from": 0, "$field": "version"}})),
                (("get", 1, "version"),))


def _http_task(i: int) -> Task:
    tid = f"http-{i:03d}"
    item = i % 4
    variant = i % 4
    if variant == 0:
        return Task(tid, "http", "single",
                    f"Fetch api.local/items/{item} and report its 'count' field. "
                    "Answer with the number only.",
                    (("http.fetch", {"url": f"api.local/items/{item}"}),),
                    (("get", 0, "body.count"),))
    if variant == 1:
        a, b = i % 4, (i + 1) % 4
        return Task(tid, "http", "sequential",
                    f"Fetch api.local/items/{a} and api.local/items/{b} and report "
                    "the sum of their 'count' fields. Answer with the number only.",
                    (("http.fetch", {"url": f"api.local/items/{a}"}),
                     ("http.fetch", {"url": f"api.local/items/{b}"})),
                    (("get", 0, "body.count"), ("get", 1, "body.count"),
                     ("pair", 2), ("agg", "sum")))
    if variant == 2:
        return Task(tid, "http", "dependent",
                    "Fetch index.local/ to list recorded pages, then fetch the "
                    "first news.local article listed and report the visitor "
                    "number in it. Answer with the number only.",
                    (("http.links", {"url": "index.local/"}),
                     ("http.fetch", {"url": f"news.local/article-{i % 3}"})),
                    (("get", 1, "body"), ("num",)))
    return Task(tid, "http", "verify",
                f"Fetch news.local/article-{i % 3}, cross-check its length with "
                "http.head, and report the content_length. Answer with the "
                "number only.",
                (("http.fetch", {"url": f"news.local/article-{i % 3}"}),
                 ("http.head", {"url": f"news.local/article-{i % 3}"})),
                (("get", 1, "content_length"),))


def _cal_task(i: int) -> Task:
    days = _cal_days()
    ids = _cal_ids()
    d = days[i % len(days)]
    eid = ids[i % len(ids)]
    tid = f"cal-{i:03d}"
    variant = i % 4
    if variant == 0:
        return Task(tid, "cal", "single",
                    f"How many events are scheduled on {d}? Answer with the "
                    "number only.",
                    (("cal.list", {"date": d}),),
                    (("get", 0, "count"),))
    if variant == 1:
        return Task(tid, "cal", "sequential",
                    f"Count the free 60-minute slots on {d}, then book the "
                    f"earliest free slot for a 'triage' meeting (50 minutes). "
                    "Answer with the number of free slots you found.",
                    (("cal.free", {"date": d}),
                     ("cal.create", {"title": "triage", "date": d,
                                     "start": {"$from": 0, "$field": "slots.0"},
                                     "end": {"$from": 0, "$field": "slots.0"}})),
                    (("get", 0, "count"),), mutates_state=True)
    if variant == 2:
        return Task(tid, "cal", "dependent",
                    f"List the events on {d}, then look up the first event's "
                    "details and report its location. Answer with the location "
                    "string only (e.g. room-3).",
                    (("cal.list", {"date": d}),
                     ("cal.get", {"event_id": {"$from": 0, "$field": "events.0.id"}})),
                    (("get", 1, "location"),))
    return Task(tid, "cal", "verify",
                f"Get event {eid} and cross-check via the day listing that its "
                "start time matches; report the start time (YYYY-MM-DDTHH:MM).",
                (("cal.get", {"event_id": eid}),
                 ("cal.list", {"date": {"$from": 0, "$field": "start",
                                        "$extract": "date"}})),
                (("get", 0, "start"),))


def _sensor_task(i: int) -> Task:
    dev = f"dev-{i % 6}"
    tid = f"sensor-{i:03d}"
    variant = i % 4
    if variant == 0:
        return Task(tid, "sensor", "single",
                    f"Read the latest value of {dev} and report it. Answer with "
                    "the number only.",
                    (("sensor.read", {"device_id": dev}),),
                    (("get", 0, "value"),))
    if variant == 1:
        a, b = f"dev-{i % 6}", f"dev-{(i + 2) % 6}"
        return Task(tid, "sensor", "sequential",
                    f"Read the latest values of {a} and {b} and report the larger "
                    "one. Answer with the number only.",
                    (("sensor.read", {"device_id": a}),
                     ("sensor.read", {"device_id": b})),
                    (("get", 0, "value"), ("get", 1, "value"),
                     ("pair", 2), ("agg", "max")))
    if variant == 2:
        return Task(tid, "sensor", "dependent",
                    f"Read the latest value of {dev}, then set that device's "
                    "alarm threshold to exactly that value. Answer with the "
                    "number you set.",
                    (("sensor.read", {"device_id": dev}),
                     ("sensor.alarm", {"device_id": dev,
                                       "threshold": {"$from": 0, "$field": "value"}})),
                    (("get", 1, "threshold"),), mutates_state=True)
    return Task(tid, "sensor", "verify",
                f"Read the latest value of {dev} and cross-check it against the "
                "most recent entry of its history; report the mean of the last 4 "
                "readings rounded to 2 decimals. Answer with the number only.",
                (("sensor.read", {"device_id": dev}),
                 ("sensor.history", {"device_id": dev, "n": 4})),
                (("get", 1, "readings.0.value"), ("get", 1, "readings.1.value"),
                 ("get", 1, "readings.2.value"), ("get", 1, "readings.3.value"),
                 ("pair", 4), ("agg", "mean"), ("round", 2)))


def _compute_task(i: int) -> Task:
    tid = f"compute-{i:03d}"
    variant = i % 4
    a, b = 17 + 3 * i, 40 + 7 * i
    if variant == 0:
        return Task(tid, "compute", "single",
                    f"Compute {a} * {b} + {a}. Answer with the number only.",
                    (("compute.calc", {"expression": f"{a} * {b} + {a}"}),),
                    (("get", 0, "value"),))
    if variant == 1:
        c = round(10 + 1.5 * i, 1)
        return Task(tid, "compute", "sequential",
                    f"Convert {c} C to F, then convert {c} C to K, and report the "
                    "sum of the two converted values rounded to 2 decimals. "
                    "Answer with the number only.",
                    (("compute.convert", {"value": c, "from_unit": "C", "to_unit": "F"}),
                     ("compute.convert", {"value": c, "from_unit": "C", "to_unit": "K"})),
                    (("get", 0, "value"), ("get", 1, "value"),
                     ("pair", 2), ("agg", "sum"), ("round", 2)))
    if variant == 2:
        km = 3 + i % 20
        return Task(tid, "compute", "dependent",
                    f"Convert {km} km to m, then divide that result by 8 using "
                    "compute.calc. Answer with the number only.",
                    (("compute.convert", {"value": km, "from_unit": "km", "to_unit": "m"}),
                     ("compute.calc", {"expression": {"$from": 0, "$field": "value",
                                                     "$suffix": " / 8"}})),
                    (("get", 1, "value"),))
    vals = [round(5 + 0.5 * ((i + j) % 9), 1) for j in range(5)]
    return Task(tid, "compute", "verify",
                f"Compute the mean of {vals} with compute.stats, cross-check by "
                "computing the sum and dividing yourself, and report the mean "
                "rounded to 3 decimals. Answer with the number only.",
                (("compute.stats", {"values": vals, "op": "mean"}),
                 ("compute.stats", {"values": vals, "op": "sum"})),
                (("get", 0, "value"), ("round", 3)))
