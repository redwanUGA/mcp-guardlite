"""Servers + task-suite guarantees the harness leans on."""
import pytest

from mcpguardlite.envs.servers import REGISTRY, make_server
from mcpguardlite.envs.tasks import build_tasks, replay_gold, verify_episode


@pytest.mark.parametrize("env", sorted(REGISTRY))
def test_digest_deterministic_and_seed_sensitive(env):
    a, b = make_server(env, 3), make_server(env, 3)
    assert a.state_digest() == b.state_digest()
    c = make_server(env, 4)
    # http/compute state is immutable; sensor's mutable state (alarms) starts
    # empty at every seed -- readings vary by seed but live outside the digest
    if env not in ("http", "compute", "sensor"):
        assert a.state_digest() != c.state_digest()


@pytest.mark.parametrize("env", sorted(REGISTRY))
def test_readonly_calls_do_not_move_digest(env):
    s = make_server(env, 1)
    d0 = s.state_digest()
    for t in s.list_tools():
        pass
    # a read-heavy episode with retries must end at the same digest
    probe = {"fs": ("fs.read", {"path": sorted(s.files)[0]}) if env == "fs" else None,
             "kv": ("kv.scan", {"prefix": "config:"}) if env == "kv" else None,
             "http": ("http.fetch", {"url": "index.local/"}) if env == "http" else None,
             "cal": ("cal.list", {"date": "2026-09-08"}) if env == "cal" else None,
             "sensor": ("sensor.read", {"device_id": "dev-0"}) if env == "sensor" else None,
             "compute": ("compute.calc", {"expression": "1+1"}) if env == "compute" else None,
             }[env]
    for _ in range(3):
        s.call_tool(*probe)
    assert s.state_digest() == d0


@pytest.mark.parametrize("env", sorted(REGISTRY))
@pytest.mark.parametrize("seed", [0, 1])
def test_gold_plans_replay_and_verify(env, seed):
    """Every task's gold plan must run clean and satisfy its own verifier --
    otherwise TSR has a false floor baked in."""
    for task in build_tasks(env, 8):
        gold = replay_gold(task, seed)
        assert gold.answer is not None, task.task_id
        assert verify_episode(task, seed, gold.digest, gold.answer), task.task_id


def test_tier_mix_present():
    for env in REGISTRY:
        tiers = {t.tier for t in build_tasks(env, 8)}
        assert tiers == {"single", "sequential", "dependent", "verify"}
