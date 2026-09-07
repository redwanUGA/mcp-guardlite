"""Six locally hostable MCP servers.

Constraint that drives every design choice here: the WHOLE benchmark must run
offline on a Raspberry Pi. No live network, no API keys, no nondeterminism.
That is what lets us run the identical suite on cluster and on device and
compare the numbers honestly.

Each server exposes: tools/list, tools/call, and a `reset(seed)` used by the
harness to restore deterministic state between episodes.

Design invariants:
  - `reset(seed)` rebuilds the ENTIRE state from `random.Random(seed)` -- no
    module-level randomness, no wall-clock time (I1 territory).
  - `state_digest()` hashes only MUTABLE state, so read-only tool calls never
    change the digest. A retry-heavy episode and a clean episode that end in the
    same state must produce the same digest, or the programmatic verifier
    (HANDOFF §3.1) punishes recovery itself.
  - Every tool declares an `outputSchema`; the sentinel validates against it and
    the S* mutators must stay INSIDE it (invariant I4).
  - Value-bearing fields that the S2 mutators retype (kv values, http bodies)
    are deliberately loosely typed; structural fields (version, count, status)
    are strictly typed so protocol faults stay overt.
"""
from __future__ import annotations

import ast
import hashlib
import json
import random
import re
from typing import Any, Protocol


class ToolError(Exception):
    """A legitimate tool-level error (bad args, missing entity). NOT a fault:
    the proxy wraps this into a JSON-RPC error envelope with no FaultEvent."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class MCPServer(Protocol):
    name: str
    def list_tools(self) -> list[dict]: ...
    def call_tool(self, name: str, args: dict) -> dict: ...
    def reset(self, seed: int) -> None: ...
    def state_digest(self) -> str: ...   # for the programmatic verifier


# --------------------------------------------------------------------------- #
# schema helpers
# --------------------------------------------------------------------------- #

_S = {"type": "string"}
_I = {"type": "integer"}
_N = {"type": "number"}
_B = {"type": "boolean"}
_ANY: dict = {}                                    # any JSON value (S2 target)


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required,
            "additionalProperties": True}


def _arr(items: dict) -> dict:
    return {"type": "array", "items": items}


def _digest(state: Any) -> str:
    return hashlib.sha256(
        json.dumps(state, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")).encode()
    ).hexdigest()


class _Base:
    """Shared plumbing: tool dispatch by short op name, digest over `_mutable()`."""

    name = "base"

    def __init__(self, seed: int = 0):
        self.reset(seed)

    # -- protocol ----------------------------------------------------------
    def list_tools(self) -> list[dict]:
        return [dict(t) for t in self.TOOLS]

    def call_tool(self, name: str, args: dict) -> dict:
        op = name.split(".", 1)[1] if name.startswith(self.name + ".") else name
        fn = getattr(self, f"op_{op}", None)
        if fn is None:
            raise ToolError(-32601, f"Method not found: {name}")
        try:
            return fn(**(args or {}))
        except TypeError as e:
            raise ToolError(-32602, f"Invalid params for {name}: {e}") from e

    def state_digest(self) -> str:
        return _digest(self._mutable())

    def _mutable(self) -> Any:
        return {}

    def output_schema(self, tool: str) -> dict | None:
        op = tool.split(".", 1)[-1]
        for t in self.TOOLS:
            if t["name"].split(".", 1)[-1] == op:
                return t.get("outputSchema")
        return None


# --------------------------------------------------------------------------- #
# fs -- read/write/list/search over a synthetic tree
# --------------------------------------------------------------------------- #

_WORDS = ("system report status update backlog config deploy metric latency "
          "budget release sensor archive summary draft review pipeline node "
          "cluster shard").split()


def _sentences(rng: random.Random, n: int) -> str:
    out = []
    for _ in range(n):
        k = rng.randint(4, 8)
        out.append(" ".join(rng.choice(_WORDS) for _ in range(k)) + ".")
    return " ".join(out)


class FilesystemServer(_Base):
    """Synthetic file tree. Files keep a version history (enables S1 stale)."""

    name = "fs"

    TOOLS = [
        {"name": "fs.list", "description": "List directory entries.",
         "inputSchema": _obj({"path": _S}, ["path"]),
         "outputSchema": _obj({"entries": _arr(_obj({"name": _S, "type": _S}, ["name", "type"])),
                               "count": _I}, ["entries", "count"])},
        {"name": "fs.read", "description": "Read a file's current content.",
         "inputSchema": _obj({"path": _S}, ["path"]),
         "outputSchema": _obj({"content": _S, "version": _I, "mtime": _I},
                              ["content", "version", "mtime"])},
        {"name": "fs.write", "description": "Write (create/replace) a file.",
         "inputSchema": _obj({"path": _S, "content": _S}, ["path", "content"]),
         "outputSchema": _obj({"ok": _B, "version": _I}, ["ok", "version"])},
        {"name": "fs.stat", "description": "File metadata without content.",
         "inputSchema": _obj({"path": _S}, ["path"]),
         "outputSchema": _obj({"exists": _B, "size": _I, "version": _I, "mtime": _I},
                              ["exists", "size", "version", "mtime"])},
        {"name": "fs.search", "description": "Count keyword occurrences per file.",
         "inputSchema": _obj({"query": _S}, ["query"]),
         "outputSchema": _obj({"matches": _arr(_obj({"path": _S, "count": _I},
                                                    ["path", "count"])),
                               "total": _I}, ["matches", "total"])},
    ]

    def reset(self, seed: int) -> None:
        # STRUCTURE (names, counts) is seed-INDEPENDENT so task templates can
        # reference entities by name at any episode seed; only VALUES vary.
        srng = random.Random("fs-structure")
        vrng = random.Random(("fs", seed).__repr__())
        self.files: dict[str, dict] = {}
        dirs = ["/docs", "/src", "/data", "/notes"]
        idx = 0
        for d in dirs:
            for i in range(4):
                path = f"{d}/{srng.choice(_WORDS)}_{i}.txt"
                nver = srng.randint(2, 3)        # >=2 so S1 always has history
                versions = []
                for v in range(nver):
                    body = _sentences(vrng, vrng.randint(2, 4))
                    # a stable numeric fact per version -- tasks key on this
                    body += f" The {srng.choice(('build', 'ticket', 'batch'))} number is {vrng.randint(100, 9899) + v}."
                    versions.append(body)
                self.files[path] = {"versions": versions,
                                    "mtime": 1_757_000_000 + idx * 3600}
                idx += 1
        # a pointer file for dependent-tier tasks; the stale version points at a
        # DIFFERENT file, so fs.S1 on the pointer misdirects the whole plan
        paths = sorted(self.files)
        target, old_target = srng.sample(paths, 2)
        self.files["/notes/pointer_0.txt"] = {
            "versions": [f"See the file at {old_target} for the latest figures.",
                         f"See the file at {target} for the latest figures."],
            "mtime": 1_757_100_000}

    def _mutable(self):
        return self.files

    # -- ops ---------------------------------------------------------------
    def op_list(self, path: str) -> dict:
        prefix = path.rstrip("/") + "/"
        names = sorted({p[len(prefix):].split("/")[0]
                        for p in self.files if p.startswith(prefix)})
        entries = [{"name": n, "type": "file" if "." in n else "dir"} for n in names]
        return {"entries": entries, "count": len(entries)}

    def op_read(self, path: str) -> dict:
        f = self.files.get(path)
        if f is None:
            raise ToolError(-32004, f"no such file: {path}")
        return {"content": f["versions"][-1], "version": len(f["versions"]),
                "mtime": f["mtime"]}

    def op_write(self, path: str, content: str) -> dict:
        f = self.files.setdefault(path, {"versions": [], "mtime": 1_757_200_000})
        f["versions"].append(str(content))
        f["mtime"] += 60
        return {"ok": True, "version": len(f["versions"])}

    def op_stat(self, path: str) -> dict:
        f = self.files.get(path)
        if f is None:
            return {"exists": False, "size": 0, "version": 0, "mtime": 0}
        return {"exists": True, "size": len(f["versions"][-1]),
                "version": len(f["versions"]), "mtime": f["mtime"]}

    def op_search(self, query: str) -> dict:
        q = query.lower()
        matches = []
        for p in sorted(self.files):
            c = self.files[p]["versions"][-1].lower().count(q)
            if c:
                matches.append({"path": p, "count": c})
        return {"matches": matches, "total": sum(m["count"] for m in matches)}


# --------------------------------------------------------------------------- #
# kv -- get/set/scan/delete with versioning (enables S1 stale)
# --------------------------------------------------------------------------- #

class KVServer(_Base):
    name = "kv"

    TOOLS = [
        {"name": "kv.get", "description": "Get the current value of a key.",
         "inputSchema": _obj({"key": _S}, ["key"]),
         "outputSchema": _obj({"value": _ANY, "version": _I}, ["value", "version"])},
        {"name": "kv.getv", "description": "Get a specific version of a key.",
         "inputSchema": _obj({"key": _S, "version": _I}, ["key", "version"]),
         "outputSchema": _obj({"value": _ANY, "version": _I}, ["value", "version"])},
        {"name": "kv.set", "description": "Set a key (appends a new version).",
         "inputSchema": _obj({"key": _S, "value": _ANY}, ["key", "value"]),
         "outputSchema": _obj({"ok": _B, "version": _I}, ["ok", "version"])},
        {"name": "kv.scan", "description": "List keys with a given prefix.",
         "inputSchema": _obj({"prefix": _S}, ["prefix"]),
         "outputSchema": _obj({"keys": _arr(_S), "count": _I}, ["keys", "count"])},
        {"name": "kv.delete", "description": "Delete a key.",
         "inputSchema": _obj({"key": _S}, ["key"]),
         "outputSchema": _obj({"ok": _B}, ["ok"])},
    ]

    def reset(self, seed: int) -> None:
        srng = random.Random("kv-structure")     # names/counts: seed-independent
        vrng = random.Random(("kv", seed).__repr__())
        self.store: dict[str, dict] = {}
        for ns, n in (("config", 4), ("user", 4), ("inv", 4), ("cache", 3)):
            for i in range(n):
                key = f"{ns}:{srng.choice(_WORDS)}_{i}"
                nver = srng.randint(2, 4)        # >=2 so S1 always has history
                base = vrng.randint(100, 5000)
                versions: list[Any] = [base + v * vrng.randint(1, 9)
                                       for v in range(nver)]
                if ns == "user":
                    versions = [{"name": f"user_{i}", "quota": v} for v in versions]
                self.store[key] = {"versions": versions}

    def _mutable(self):
        return self.store

    def op_get(self, key: str) -> dict:
        e = self.store.get(key)
        if e is None:
            raise ToolError(-32004, f"no such key: {key}")
        return {"value": e["versions"][-1], "version": len(e["versions"])}

    def op_getv(self, key: str, version: int) -> dict:
        e = self.store.get(key)
        if e is None or not (1 <= version <= len(e["versions"])):
            raise ToolError(-32004, f"no such key/version: {key}@{version}")
        return {"value": e["versions"][version - 1], "version": version}

    def op_set(self, key: str, value: Any) -> dict:
        e = self.store.setdefault(key, {"versions": []})
        e["versions"].append(value)
        return {"ok": True, "version": len(e["versions"])}

    def op_scan(self, prefix: str) -> dict:
        keys = sorted(k for k in self.store if k.startswith(prefix))
        return {"keys": keys, "count": len(keys)}

    def op_delete(self, key: str) -> dict:
        if key not in self.store:
            raise ToolError(-32004, f"no such key: {key}")
        del self.store[key]
        return {"ok": True}


# --------------------------------------------------------------------------- #
# http -- fetch over a RECORDED corpus, never the live web
# --------------------------------------------------------------------------- #

class HTTPFetchServer(_Base):
    """Recorded corpus keyed by URL; each URL stores >=1 snapshot (S1 target).
    Read-only: the digest is constant, so http tasks verify by answer."""

    name = "http"

    TOOLS = [
        {"name": "http.fetch", "description": "GET a recorded URL.",
         "inputSchema": _obj({"url": _S}, ["url"]),
         "outputSchema": _obj({"status": _I, "body": _ANY}, ["status", "body"])},
        {"name": "http.head", "description": "HEAD a recorded URL.",
         "inputSchema": _obj({"url": _S}, ["url"]),
         "outputSchema": _obj({"status": _I, "content_length": _I},
                              ["status", "content_length"])},
        {"name": "http.links", "description": "List links found at a URL.",
         "inputSchema": _obj({"url": _S}, ["url"]),
         "outputSchema": _obj({"links": _arr(_S), "count": _I}, ["links", "count"])},
    ]

    def reset(self, seed: int) -> None:
        srng = random.Random("http-structure")   # page set: seed-independent
        vrng = random.Random(("http", seed).__repr__())
        self.pages: dict[str, dict] = {}
        for i in range(4):
            snaps = []
            for s in range(srng.randint(2, 3)):   # >=2 so S1 always has history
                snaps.append({"id": i, "name": f"unit_{i}",
                              "count": vrng.randint(5, 4000) + s,
                              "score": round(vrng.uniform(1, 9) + 0.1 * s, 2)})
            self.pages[f"api.local/items/{i}"] = {"snapshots": snaps}
        for i in range(3):
            snaps = [_sentences(vrng, 3) +
                     f" Visitors today: {vrng.randint(50, 4000) + 10 * s}."
                     for s in range(2)]
            self.pages[f"news.local/article-{i}"] = {"snapshots": snaps}
        all_pages = sorted(self.pages)
        self.pages["index.local/"] = {"snapshots": [all_pages[:-1], all_pages]}

    def _mutable(self):
        return {}                                    # corpus is immutable

    def _page(self, url: str) -> dict:
        p = self.pages.get(url)
        if p is None:
            raise ToolError(-32004, f"404 not recorded: {url}")
        return p

    def op_fetch(self, url: str) -> dict:
        return {"status": 200, "body": self._page(url)["snapshots"][-1]}

    def op_head(self, url: str) -> dict:
        body = self._page(url)["snapshots"][-1]
        return {"status": 200,
                "content_length": len(json.dumps(body) if not isinstance(body, str) else body)}

    def op_links(self, url: str) -> dict:
        self._page(url)
        links = sorted(self.pages) if url.startswith("index") else []
        return {"links": links, "count": len(links)}


# --------------------------------------------------------------------------- #
# cal -- events, conflicts, timezone handling (enables S2)
# --------------------------------------------------------------------------- #

class CalendarServer(_Base):
    name = "cal"
    _TZS = ["America/New_York", "America/Chicago", "UTC"]

    TOOLS = [
        {"name": "cal.list", "description": "List events on a date (YYYY-MM-DD).",
         "inputSchema": _obj({"date": _S}, ["date"]),
         "outputSchema": _obj({"events": _arr(_obj({"id": _S, "title": _S,
                                                    "start": _S, "end": _S},
                                                   ["id", "title", "start", "end"])),
                               "count": _I}, ["events", "count"])},
        {"name": "cal.get", "description": "Get one event by id.",
         "inputSchema": _obj({"event_id": _S}, ["event_id"]),
         "outputSchema": _obj({"id": _S, "title": _S, "start": _S, "end": _S,
                               "tz": _S, "location": _S},
                              ["id", "title", "start", "end", "tz", "location"])},
        {"name": "cal.create", "description": "Create an event on a date.",
         "inputSchema": _obj({"title": _S, "date": _S, "start": _S, "end": _S},
                             ["title", "date", "start", "end"]),
         "outputSchema": _obj({"ok": _B, "event_id": _S}, ["ok", "event_id"])},
        {"name": "cal.free", "description": "Free 60-min slots on a date (9-17h).",
         "inputSchema": _obj({"date": _S}, ["date"]),
         "outputSchema": _obj({"slots": _arr(_S), "count": _I}, ["slots", "count"])},
        {"name": "cal.delete", "description": "Delete an event.",
         "inputSchema": _obj({"event_id": _S}, ["event_id"]),
         "outputSchema": _obj({"ok": _B}, ["ok"])},
    ]

    def reset(self, seed: int) -> None:
        srng = random.Random("cal-structure")    # ids/counts: seed-independent
        vrng = random.Random(("cal", seed).__repr__())
        self.events: dict[str, dict] = {}
        self._next = 100
        for day in range(8, 12):                      # 2026-09-08 .. 09-11
            for _ in range(srng.randint(2, 3)):
                h = vrng.choice([9, 10, 11, 13, 14, 15, 16])
                eid = f"ev{self._next}"
                self._next += 1
                start = f"2026-09-{day:02d}T{h:02d}:00"
                self.events[eid] = {
                    "title": f"{srng.choice(_WORDS)} sync",
                    "start": start,
                    "end": f"2026-09-{day:02d}T{h:02d}:50",
                    "tz": vrng.choice(self._TZS),
                    "location": f"room-{vrng.randint(1, 9)}",
                    # prior schedule (S1 stale target)
                    "history": [f"2026-09-{day:02d}T{max(h - vrng.randint(1, 3), 8):02d}:00"],
                }

    def _mutable(self):
        return self.events

    def op_list(self, date: str) -> dict:
        evs = [{"id": k, "title": v["title"], "start": v["start"], "end": v["end"]}
               for k, v in sorted(self.events.items())
               if v["start"].startswith(date)]
        return {"events": evs, "count": len(evs)}

    def op_get(self, event_id: str) -> dict:
        e = self.events.get(event_id)
        if e is None:
            raise ToolError(-32004, f"no such event: {event_id}")
        return {"id": event_id, "title": e["title"], "start": e["start"],
                "end": e["end"], "tz": e["tz"], "location": e["location"]}

    def op_create(self, title: str, date: str, start: str, end: str) -> dict:
        eid = f"ev{self._next}"
        self._next += 1
        self.events[eid] = {"title": title, "start": f"{date}T{start}",
                            "end": f"{date}T{end}", "tz": "UTC",
                            "location": "room-0", "history": []}
        return {"ok": True, "event_id": eid}

    def op_free(self, date: str) -> dict:
        busy = {int(v["start"][11:13]) for v in self.events.values()
                if v["start"].startswith(date)}
        slots = [f"{h:02d}:00" for h in range(9, 17) if h not in busy]
        return {"slots": slots, "count": len(slots)}

    def op_delete(self, event_id: str) -> dict:
        if event_id not in self.events:
            raise ToolError(-32004, f"no such event: {event_id}")
        del self.events[event_id]
        return {"ok": True}


# --------------------------------------------------------------------------- #
# sensor -- IoT telemetry, units in C/F/K (enables S2, S4)
# --------------------------------------------------------------------------- #

class SensorServer(_Base):
    """Readings are a pure function of (seed, device, k): retries and history
    reads NEVER advance state, so the digest stays honest under recovery."""

    name = "sensor"
    _N_READINGS = 24

    TOOLS = [
        {"name": "sensor.list", "description": "List registered devices.",
         "inputSchema": _obj({}, []),
         "outputSchema": _obj({"devices": _arr(_obj({"id": _S, "kind": _S,
                                                     "unit": _S, "location": _S},
                                                    ["id", "kind", "unit", "location"])),
                               "count": _I}, ["devices", "count"])},
        {"name": "sensor.read", "description": "Latest reading of a device.",
         "inputSchema": _obj({"device_id": _S}, ["device_id"]),
         "outputSchema": _obj({"value": _N, "unit": _S, "ts": _I},
                              ["value", "unit", "ts"])},
        {"name": "sensor.history", "description": "Last n readings (oldest first).",
         "inputSchema": _obj({"device_id": _S, "n": _I}, ["device_id", "n"]),
         "outputSchema": _obj({"readings": _arr(_obj({"value": _N, "ts": _I},
                                                     ["value", "ts"])),
                               "unit": _S, "count": _I},
                              ["readings", "unit", "count"])},
        {"name": "sensor.alarm", "description": "Set a device's alarm threshold.",
         "inputSchema": _obj({"device_id": _S, "threshold": _N},
                             ["device_id", "threshold"]),
         "outputSchema": _obj({"ok": _B, "threshold": _N}, ["ok", "threshold"])},
    ]

    _KINDS = [("temp", "C", 18.0, 6.0), ("humidity", "%", 45.0, 15.0),
              ("pressure", "hPa", 1013.0, 8.0), ("light", "lux", 300.0, 150.0)]

    def reset(self, seed: int) -> None:
        self._seed = seed
        rng = random.Random(("sensor", seed).__repr__())
        self.devices: dict[str, dict] = {}
        for i in range(6):
            kind, unit, mu, sig = self._KINDS[i % len(self._KINDS)]
            self.devices[f"dev-{i}"] = {
                "kind": kind, "unit": unit, "mu": mu, "sig": sig,
                "location": f"zone-{i % 3}", "alarm": None,
            }

    def _mutable(self):
        return {d: v["alarm"] for d, v in self.devices.items()}

    def _reading(self, device_id: str, k: int) -> float:
        d = self.devices[device_id]
        r = random.Random(("read", self._seed, device_id, k).__repr__())
        return round(d["mu"] + d["sig"] * (r.random() * 2 - 1), 2)

    def op_list(self) -> dict:
        devs = [{"id": k, "kind": v["kind"], "unit": v["unit"],
                 "location": v["location"]} for k, v in sorted(self.devices.items())]
        return {"devices": devs, "count": len(devs)}

    def op_read(self, device_id: str) -> dict:
        if device_id not in self.devices:
            raise ToolError(-32004, f"no such device: {device_id}")
        k = self._N_READINGS - 1
        return {"value": self._reading(device_id, k),
                "unit": self.devices[device_id]["unit"],
                "ts": 1_757_030_000 + k * 300}

    def op_history(self, device_id: str, n: int) -> dict:
        if device_id not in self.devices:
            raise ToolError(-32004, f"no such device: {device_id}")
        n = max(1, min(int(n), self._N_READINGS))
        ks = range(self._N_READINGS - n, self._N_READINGS)
        return {"readings": [{"value": self._reading(device_id, k),
                              "ts": 1_757_030_000 + k * 300} for k in ks],
                "unit": self.devices[device_id]["unit"], "count": n}

    def op_alarm(self, device_id: str, threshold: float) -> dict:
        if device_id not in self.devices:
            raise ToolError(-32004, f"no such device: {device_id}")
        self.devices[device_id]["alarm"] = float(threshold)
        return {"ok": True, "threshold": float(threshold)}


# --------------------------------------------------------------------------- #
# compute -- unit conversion + arithmetic; the cross-check tool
# --------------------------------------------------------------------------- #

_LINEAR_UNITS = {("m", "km"): 1e-3, ("km", "m"): 1e3,
                 ("m", "mi"): 1 / 1609.344, ("mi", "m"): 1609.344,
                 ("kg", "lb"): 2.204623, ("lb", "kg"): 1 / 2.204623,
                 ("s", "ms"): 1e3, ("ms", "s"): 1e-3}


def convert_unit(value: float, src: str, dst: str) -> float:
    s, d = src.strip(), dst.strip()
    temps = {"C", "F", "K"}
    if s == d:
        return float(value)
    if s in temps and d in temps:
        c = {"C": value, "F": (value - 32) * 5 / 9, "K": value - 273.15}[s]
        return {"C": c, "F": c * 9 / 5 + 32, "K": c + 273.15}[d]
    if (s, d) in _LINEAR_UNITS:
        return value * _LINEAR_UNITS[(s, d)]
    raise ToolError(-32602, f"unsupported conversion {s} -> {d}")


class ComputeServer(_Base):
    """Pure functions; the digest is constant by construction."""

    name = "compute"

    TOOLS = [
        {"name": "compute.convert", "description": "Convert between units (C/F/K, m/km/mi, kg/lb, s/ms).",
         "inputSchema": _obj({"value": _N, "from_unit": _S, "to_unit": _S},
                             ["value", "from_unit", "to_unit"]),
         "outputSchema": _obj({"value": _N, "unit": _S}, ["value", "unit"])},
        {"name": "compute.calc", "description": "Evaluate an arithmetic expression.",
         "inputSchema": _obj({"expression": _S}, ["expression"]),
         "outputSchema": _obj({"value": _N}, ["value"])},
        {"name": "compute.stats", "description": "Aggregate a list of numbers.",
         "inputSchema": _obj({"values": _arr(_N),
                              "op": {"type": "string",
                                     "enum": ["mean", "max", "min", "sum"]}},
                             ["values", "op"]),
         "outputSchema": _obj({"value": _N, "n": _I}, ["value", "n"])},
        {"name": "compute.compare", "description": "Compare two numbers with tolerance.",
         "inputSchema": _obj({"a": _N, "b": _N, "rel_tol": _N}, ["a", "b"]),
         "outputSchema": _obj({"equal": _B, "diff": _N}, ["equal", "diff"])},
    ]

    _ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
                ast.USub, ast.UAdd, ast.FloorDiv)

    def reset(self, seed: int) -> None:
        pass

    def op_convert(self, value: float, from_unit: str, to_unit: str) -> dict:
        return {"value": round(convert_unit(float(value), from_unit, to_unit), 6),
                "unit": to_unit}

    def op_calc(self, expression: str) -> dict:
        try:
            tree = ast.parse(str(expression), mode="eval")
        except SyntaxError as e:
            raise ToolError(-32602, f"bad expression: {e}") from e
        for node in ast.walk(tree):
            if not isinstance(node, self._ALLOWED):
                raise ToolError(-32602, f"disallowed syntax: {type(node).__name__}")
        return {"value": round(float(eval(compile(tree, "<calc>", "eval"))), 6)}  # noqa: S307

    def op_stats(self, values: list, op: str) -> dict:
        vals = [float(v) for v in values]
        if not vals:
            return {"value": 0.0, "n": 0}
        agg = {"mean": sum(vals) / len(vals), "max": max(vals),
               "min": min(vals), "sum": sum(vals)}.get(op)
        if agg is None:
            raise ToolError(-32602, f"unknown op: {op}")
        return {"value": round(agg, 6), "n": len(vals)}

    def op_compare(self, a: float, b: float, rel_tol: float = 1e-6) -> dict:
        a, b = float(a), float(b)
        diff = abs(a - b)
        ok = diff <= rel_tol * max(abs(a), abs(b), 1e-12)
        return {"equal": bool(ok), "diff": round(diff, 9)}


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #

REGISTRY = {
    "fs": FilesystemServer, "kv": KVServer, "http": HTTPFetchServer,
    "cal": CalendarServer, "sensor": SensorServer, "compute": ComputeServer,
}

# Held-out-environment split: train on the first four, test on the last two.
TRAIN_ENVS = ["fs", "kv", "http", "cal"]
HELDOUT_ENVS = ["sensor", "compute"]


def make_server(env: str, seed: int = 0):
    return REGISTRY[env](seed)


def extract_number(text: str) -> float | None:
    """First number in a string (tasks and mutators share this)."""
    m = re.search(r"-?\d+(?:\.\d+)?", str(text))
    return float(m.group()) if m else None


def extract_path(text: str) -> str | None:
    m = re.search(r"/[\w/.-]+\.txt", str(text))
    return m.group() if m else None
