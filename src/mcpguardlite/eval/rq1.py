"""RQ1 analysis: the GO/NO-GO computation (HANDOFF §5).

    python -m mcpguardlite.eval.rq1 --results results/rq1_pilot

For every compression level vs the F16 anchor:
  1. assert_paired() -- a single mismatch discards the pair (I1),
  2. RCG in pp with a cluster-bootstrap 95% CI over PAIRED episode resamples,
  3. the §5 verdict:
       GO        RCG > 3pp with CI excluding zero on any level
       REFRAME   every CI covers zero            (negative-result paper)
       SUSPECT   RCG < 0 with CI excluding zero  (check R2 floor/ceiling first)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .harness import assert_paired, load_episodes
from . import metrics as M


def paired_rcg_ci(base_eps, comp_eps, n_boot: int = 2000, seed: int = 0):
    """Bootstrap over the SHARED episode ids (paired resampling: the same
    episode draw is applied to both arms, matching the paired design)."""
    base = {e.episode_id: e for e in base_eps}
    comp = {e.episode_id: e for e in comp_eps}
    ids = sorted(set(base) & set(comp))
    if not ids:
        raise ValueError("no shared episode ids between arms")
    b = [base[i] for i in ids]
    c = [comp[i] for i in ids]
    point = M.rcg(b, c)
    rng = np.random.default_rng(seed)
    stats = []
    n = len(ids)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        stats.append(M.rcg([b[i] for i in idx], [c[i] for i in idx]))
    lo, hi = np.nanpercentile(stats, [2.5, 97.5])
    return point, float(lo), float(hi), len(ids)


def analyze(results_dir: str, anchor: str = "F16") -> dict:
    root = Path(results_dir)
    # layout: <results>/<model_tag>/<fault>/<method>/*.json ; model_tag encodes
    # the gguf path, whose basename carries the quant level
    arms: dict[str, str] = {}
    for d in root.iterdir():
        if not d.is_dir():
            continue
        for level in ("F16", "Q8_0", "Q5_K_M", "Q4_K_M", "Q3_K_M"):
            if level.lower() in d.name.lower():
                arms[level] = str(d)
    if anchor not in arms:
        raise SystemExit(f"anchor {anchor} not found under {root} "
                         f"(arms found: {sorted(arms)})")

    base_eps = load_episodes(arms[anchor])
    print(f"== RQ1 vs {anchor} (n={len(base_eps)} episodes) ==")
    print(f"{anchor:8s} TSR={M.tsr(base_eps):.3f} TSRphi={M.tsr_phi(base_eps):.3f} "
          f"RSR={M.rsr(base_eps):.3f} SFR={M.sfr(base_eps):.3f}")

    out = {}
    verdict = "REFRAME"
    for level in ("Q8_0", "Q5_K_M", "Q4_K_M", "Q3_K_M"):
        if level not in arms:
            continue
        assert_paired(arms[anchor], arms[level])
        comp_eps = load_episodes(arms[level])
        rcg, lo, hi, n = paired_rcg_ci(base_eps, comp_eps)
        excl0 = lo > 0 or hi < 0
        out[level] = {"rcg_pp": rcg, "ci": (lo, hi), "n_paired": n,
                      "tsr": M.tsr(comp_eps), "rsr": M.rsr(comp_eps),
                      "sfr": M.sfr(comp_eps)}
        print(f"{level:8s} TSR={M.tsr(comp_eps):.3f} RSR={M.rsr(comp_eps):.3f} "
              f"SFR={M.sfr(comp_eps):.3f} | RCG={rcg:+.1f}pp "
              f"CI[{lo:+.1f},{hi:+.1f}] n={n} {'*' if excl0 else ''}")
        if rcg > 3.0 and lo > 0:
            verdict = "GO"
        elif rcg < 0 and hi < 0 and verdict != "GO":
            verdict = "SUSPECT (check R2 floor/ceiling before believing it)"
    print(f"\n== §5 verdict: {verdict} ==")
    out["verdict"] = verdict
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--anchor", default="F16")
    args = ap.parse_args()
    analyze(args.results, args.anchor)


if __name__ == "__main__":
    main()
