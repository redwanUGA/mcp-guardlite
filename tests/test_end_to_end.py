"""End-to-end: scripted policy through proxy + injector + verifier + traces.
This is the laptop-sized replica of the W1 gate ('20 episodes end-to-end with
faults firing') -- if this passes, the cluster job is plumbing, not physics."""
import json
from pathlib import Path

from mcpguardlite.eval.harness import RunSpec, assert_paired, load_episodes, run
from mcpguardlite.eval.metrics import rsr, sfr, tsr_phi
from mcpguardlite.faults.injector import FaultEvent, apply_fault
from mcpguardlite.faults.taxonomy import TAXONOMY


def _spec(model="scripted", fault="configs/faults/mixed_r15.yaml"):
    return RunSpec(model_config=model, fault_config=fault, method="naive",
                   seeds=(0, 1), n_tasks=5, envs=("fs", "kv"))


def test_apply_fault_is_total():
    """Every family must produce SOMETHING deliverable (HANDOFF §3.3)."""
    from mcpguardlite.envs.servers import make_server
    server = make_server("kv", 0)
    key = sorted(server.store)[0]
    nominal = {"jsonrpc": "2.0", "id": 0,
               "result": server.call_tool("kv.get", {"key": key})}
    for fam, spec in TAXONOMY.items():
        params = {"staleness_steps": 2, "truncate_frac": 0.5, "code": -32603,
                  "inflate_x": 3, "slowdown_x": 2.0, "delay_ms": 100}
        ev = FaultEvent("t", 0, "kv.get", fam, True, None, params, spec.oracle_op)
        try:
            out = apply_fault(dict(nominal), ev,
                              ctx={"args": {"key": key}, "env": "kv",
                                   "tool": "kv.get", "server": server})
            assert isinstance(out, dict)
        except (TimeoutError, ConnectionError):
            pass                                   # transport families raise


def test_scripted_episodes_run_and_faults_fire(tmp_path):
    out = tmp_path / "run_a"
    run(_spec(), str(out), skip_existing=False)
    eps = load_episodes(str(out))
    assert len(eps) == 20                          # 2 envs x 5 tasks x 2 seeds
    fired = [e for e in eps if e.fault_fired]
    assert fired, "mixed_r15 at rate 0.15 fired nothing across 20 episodes"
    assert 0.0 <= tsr_phi(eps) <= 1.0
    assert rsr(eps) == rsr(fired)                  # RSR only over triggered (I2)
    # traces exist, one JSON per episode, schema field present
    files = list(Path(out).rglob("*.json"))
    assert len(files) == 20
    rec = json.loads(files[0].read_text(encoding="utf-8"))
    assert rec["schema"] == "faulttrace-v1"
    assert all("decoder_stats" in t for t in rec["trajectory"]["turns"])


def test_clean_config_gives_high_tsr(tmp_path):
    out = tmp_path / "clean"
    run(_spec(fault="configs/faults/clean.yaml"), str(out), skip_existing=False)
    eps = load_episodes(str(out))
    assert not any(e.fault_fired for e in eps)
    assert tsr_phi(eps) >= 0.9, (
        "scripted policy fails clean tasks -- task suite or verifier is broken")


def test_paired_across_model_configs(tmp_path):
    """Same fault schedule for two different 'model configs' (I1, end-to-end)."""
    a, b = tmp_path / "fp16", tmp_path / "q4"
    run(_spec(model="scripted"), str(a), skip_existing=False)
    run(_spec(model="scripted:1"), str(b), skip_existing=False)
    assert_paired(str(a), str(b))


def test_sfr_is_measurable(tmp_path):
    """Silent-only config must produce at least one asserted-but-wrong episode
    somewhere in a small sweep; if it cannot, SFR is structurally invisible."""
    out = tmp_path / "silent"
    spec = RunSpec(model_config="scripted",
                   fault_config="configs/faults/silent_only.yaml",
                   method="naive", seeds=(0, 1, 2), n_tasks=6,
                   envs=("fs", "kv", "sensor"))
    run(spec, str(out), skip_existing=False)
    eps = load_episodes(str(out))
    assert sfr(eps) > 0.0, "no silent failures under silent_only -- S* toothless"
