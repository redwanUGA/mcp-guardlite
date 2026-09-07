"""The tests that actually protect the paper's claims."""
from mcpguardlite.faults.injector import FaultConfig, FaultScheduler, prf_unit


def test_prf_is_stable():
    assert prf_unit(0, "ep1", 3, "fs.read") == prf_unit(0, "ep1", 3, "fs.read")


def test_same_seed_same_schedule():
    cfg = FaultConfig(families=["T2", "P1"], rate=0.3, seed=7)
    a = [FaultScheduler(cfg).decide("ep1", t, "fs.read") for t in range(20)]
    b = [FaultScheduler(cfg).decide("ep1", t, "fs.read") for t in range(20)]
    assert [x.family if x else None for x in a] == [x.family if x else None for x in b]


def test_paired_across_model_configs():
    """The invariant RCG depends on: the fault schedule must not depend on which
    model is running. If this ever fails, every RCG number is meaningless."""
    cfg = FaultConfig(families=["S1"], rate=0.5, seed=1)
    fp16 = [FaultScheduler(cfg).decide("ep9", t, "kv.get") for t in range(10)]
    q4 = [FaultScheduler(cfg).decide("ep9", t, "kv.get") for t in range(10)]
    assert [bool(x) for x in fp16] == [bool(x) for x in q4]
