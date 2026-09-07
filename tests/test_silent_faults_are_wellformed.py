"""Guards RQ3's validity: if silent faults fail schema validation they are not
silent, and the S* rows measure nothing (invariant I4).

For every registered (env, family) mutator and every op it is applicable to:
  - the mutated result must validate against the tool's outputSchema
  - the mutation must actually change the payload for at least one op of the
    family (a mutator that never bites would silently hollow out RQ3)
This is the automated half of R3; the hand audit of 50 sampled mutations per
environment still happens before the full run.
"""
import jsonschema
import pytest

from mcpguardlite.envs.mutators import MUTATORS, SILENT_OPS
from mcpguardlite.envs.servers import make_server
from mcpguardlite.faults.injector import FaultEvent
from mcpguardlite.faults.taxonomy import TAXONOMY

# one canonical argument set per (env, op)
ARGS = {
    ("fs", "read"): {"path": None}, ("fs", "stat"): {"path": None},
    ("fs", "list"): {"path": "/docs"}, ("fs", "search"): {"query": "system"},
    ("kv", "get"): {"key": None}, ("kv", "getv"): {"key": None, "version": 1},
    ("kv", "scan"): {"prefix": "config:"},
    ("http", "fetch"): {"url": "api.local/items/1"},
    ("http", "head"): {"url": "news.local/article-0"},
    ("http", "links"): {"url": "index.local/"},
    ("cal", "get"): {"event_id": None}, ("cal", "list"): {"date": "2026-09-08"},
    ("cal", "free"): {"date": "2026-09-08"},
    ("sensor", "read"): {"device_id": "dev-0"},
    ("sensor", "history"): {"device_id": "dev-0", "n": 4},
    ("compute", "stats"): {"values": [3.0, 4.5, 9.1], "op": "mean"},
    ("compute", "convert"): {"value": 21.5, "from_unit": "C", "to_unit": "F"},
    ("compute", "calc"): {"expression": "17 * 3 + 2"},
}


def _fill(env, op, server):
    args = dict(ARGS[(env, op)])
    if args.get("path", "") is None:
        args["path"] = sorted(server.files)[0]
    if args.get("key", "") is None:
        args["key"] = sorted(server.store)[0]
    if args.get("event_id", "") is None:
        args["event_id"] = sorted(server.events)[0]
    return args


def _event(fam, tool):
    params = {}
    if fam == "S1":
        params["staleness_steps"] = 2
    return FaultEvent(episode_id="audit", turn=0, tool=tool, family=fam,
                      fired=True, persistent_from=None, params=params,
                      oracle_op=TAXONOMY[fam].oracle_op)


def test_mutators_registered_for_all_envs():
    envs = {env for env, _ in MUTATORS}
    assert envs == {"fs", "kv", "http", "cal", "sensor", "compute"}
    assert all((env, f"S{i}") in MUTATORS for env in envs for i in range(1, 5))


@pytest.mark.parametrize("env,family", sorted(MUTATORS))
def test_silent_mutations_pass_schema_and_bite(env, family):
    server = make_server(env, 0)
    mut = MUTATORS[(env, family)]
    changed = 0
    for op in sorted(SILENT_OPS[(env, family)]):
        tool = f"{env}.{op}"
        args = _fill(env, op, server)
        nominal = server.call_tool(tool, args)
        ev = _event(family, tool)
        mutated = mut(dict(nominal), params=ev.params, server=server, tool=tool,
                      args=args, salt=("audit", 0, tool))
        schema = server.output_schema(tool)
        jsonschema.validate(mutated, schema)     # silent = schema-valid (I4)
        if mutated != nominal:
            changed += 1
    assert changed >= 1, f"{env}/{family} never mutated anything -- RQ3 row empty"
