"""W2 scaffolding guards: tuning configs, GGUF grid constants, model-spec
grammar, and the retry_only controller path end-to-end (scripted policy)."""
import pytest

from mcpguardlite.compress.quantize import CALIB_ARMS, GGUF_LEVELS
from mcpguardlite.faults.injector import FaultConfig


@pytest.mark.parametrize("name,rate,has_p3", [
    ("mixed_r15", 0.15, True), ("mixed_r10", 0.10, True),
    ("mixed_r05", 0.05, True),
    ("mixed_r15_noP3", 0.15, False), ("mixed_r10_noP3", 0.10, False),
])
def test_tuning_configs_load(name, rate, has_p3):
    cfg = FaultConfig.from_yaml(f"configs/faults/{name}.yaml")
    assert cfg.rate == pytest.approx(rate)
    assert ("P3" in cfg.families) == has_p3
    assert cfg.seed == 0                    # shared seed keeps arms comparable


def test_grid_constants():
    assert GGUF_LEVELS == ("F16", "Q8_0", "Q5_K_M", "Q4_K_M", "Q3_K_M")
    assert CALIB_ARMS == ("generic", "nominal", "recovery", "mixture")


def test_retry_only_beats_naive_on_transients(tmp_path):
    """The controller path must actually recover: under an overt-transient-only
    process the retry_only method should strictly beat naive RSR with the
    scripted policy (T2/T3 are one-retry-fixable by construction)."""
    import yaml
    from mcpguardlite.eval.harness import RunSpec, load_episodes, run
    from mcpguardlite.eval.metrics import rsr
    cfg = tmp_path / "transient.yaml"
    cfg.write_text(yaml.safe_dump({
        "families": ["T2", "T3"], "rate": 0.35, "seed": 0,
        "max_faults_per_episode": 3}))
    out = {}
    for method in ("naive", "retry_only"):
        spec = RunSpec(model_config="scripted:0", fault_config=str(cfg),
                       method=method, seeds=(0, 1, 2), n_tasks=6,
                       envs=("fs", "kv"))
        run(spec, str(tmp_path / method), skip_existing=False)
        eps = load_episodes(str(tmp_path / method))
        out[method] = rsr([e for e in eps if e.fault_fired])
    assert out["retry_only"] > out["naive"], out
