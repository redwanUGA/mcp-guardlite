"""Metrics for MCP-GuardLite.

This module owns the definitions the paper reports. If a number appears in a
table, it should be produced here and nowhere else.

Key definitions (Sec. III-B of the paper):

    TSR(c)        task success, no faults
    TSR_phi(c)    task success under fault process phi
    RSR(c)        recovery success: of episodes where a fault FIRED, fraction
                  that still succeeded
    SFR(c)        silent failure: agent asserts success, verifier disagrees
    RCG(c)        [RSR(c0) - RSR(c)] - [TSR(c0) - TSR(c)]       in pp
    ROR(c)        recovery actions taken on FAULT-FREE episodes
    E_task        joules / episode succeeding under fault
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Episode:
    episode_id: str
    config: str                 # compression config id
    fault_fired: bool
    success: bool               # verifier judgement
    asserted_success: bool      # what the agent claimed
    recovery_actions: int
    tokens: int
    wall_s: float
    joules: float | None
    fault_families: list[str]


# --------------------------------------------------------------------------- #
# point metrics
# --------------------------------------------------------------------------- #

def tsr(eps: list[Episode]) -> float:
    clean = [e for e in eps if not e.fault_fired]
    return float(np.mean([e.success for e in clean])) if clean else float("nan")


def tsr_phi(eps: list[Episode]) -> float:
    return float(np.mean([e.success for e in eps])) if eps else float("nan")


def rsr(eps: list[Episode]) -> float:
    """Only over episodes where a fault actually TRIGGERED.

    Excluding untriggered episodes is not cosmetic -- including them dilutes the
    signal and underestimates fault impact (cf. AgentChaos trigger verification).
    """
    faulted = [e for e in eps if e.fault_fired]
    return float(np.mean([e.success for e in faulted])) if faulted else float("nan")


def sfr(eps: list[Episode]) -> float:
    return float(np.mean([e.asserted_success and not e.success for e in eps]))


def ror(eps: list[Episode]) -> float:
    clean = [e for e in eps if not e.fault_fired]
    return float(np.mean([e.recovery_actions for e in clean])) if clean else 0.0


def energy_per_resolved_task(eps: list[Episode]) -> float:
    total_j = sum(e.joules or 0.0 for e in eps)
    resolved = sum(1 for e in eps if e.fault_fired and e.success)
    return total_j / resolved if resolved else float("inf")


# --------------------------------------------------------------------------- #
# the headline metric
# --------------------------------------------------------------------------- #

def rcg(baseline: list[Episode], compressed: list[Episode]) -> float:
    """Resilience Compression Gap, in percentage points.

    Positive => compression costs MORE recovery competence than nominal
    competence => fault-free evaluation understates the deployment cost of this
    configuration.

    Requires a PAIRED design: `baseline` and `compressed` must have been run
    with the same fault seed so identical faults fired at identical turns.
    """
    d_nom = tsr(baseline) - tsr(compressed)
    d_rec = rsr(baseline) - rsr(compressed)
    return 100.0 * (d_rec - d_nom)


def rcg_by_family(baseline: list[Episode],
                  compressed: list[Episode]) -> dict[str, float]:
    fams = sorted({f for e in baseline + compressed for f in e.fault_families})
    out = {}
    for fam in fams:
        b = [e for e in baseline if fam in e.fault_families]
        c = [e for e in compressed if fam in e.fault_families]
        if b and c:
            out[fam] = 100.0 * ((rsr(b) - rsr(c)) - (tsr(baseline) - tsr(compressed)))
    return out


# --------------------------------------------------------------------------- #
# uncertainty
# --------------------------------------------------------------------------- #

def bootstrap_ci(fn, *episode_lists, n_boot: int = 2000,
                 alpha: float = 0.05, seed: int = 0) -> tuple[float, float, float]:
    """Cluster bootstrap over episodes (resample episode ids, not turns)."""
    rng = np.random.default_rng(seed)
    point = fn(*episode_lists)
    stats = []
    n = len(episode_lists[0])
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        stats.append(fn(*[[lst[i] for i in idx] for lst in episode_lists]))
    lo, hi = np.nanpercentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi)


def paired_wilcoxon(a: list[float], b: list[float]) -> tuple[float, float]:
    from scipy.stats import wilcoxon
    stat, p = wilcoxon(a, b)
    return float(stat), float(p)


def holm_correct(pvals: list[float]) -> list[float]:
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adj[i] = min(running, 1.0)
    return adj.tolist()


# --------------------------------------------------------------------------- #
# detection metrics (sentinel)
# --------------------------------------------------------------------------- #

def detection_auroc(y_true: np.ndarray, p_fault: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y_true, p_fault))


def detection_latency(turns_to_detect: list[int]) -> float:
    """Mean turns between fault firing and sentinel raising. Lower is better;
    a detector that only fires at the terminal turn is useless for recovery."""
    return float(np.mean(turns_to_detect)) if turns_to_detect else float("nan")
