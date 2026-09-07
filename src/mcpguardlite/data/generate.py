"""Trajectory generation (the GACRC-heavy stage).

Sharding: one SLURM array task per (env x fault_config) cell; each writes its
own JSONL shard so nothing needs a shared writer.

Cost control: the teacher rollout is the expensive part. Generate ONCE at FP16
with the teacher, then reuse the same task/fault schedule for every compression
config in evaluation -- do not regenerate per config (R6).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..eval.harness import RunSpec, run, fault_config_from, model_tag


def generate(*, env: str, fault_config: str, teacher: str, n_tasks: int,
             seeds: tuple, out: str) -> str:
    """Run the teacher (method=naive: the sentinel trains on UNassisted
    behaviour) over one env x fault_config cell, then concatenate the per-
    episode trajectories into the shard JSONL the downstream consumers read."""
    spec = RunSpec(model_config=teacher, fault_config=fault_config,
                   method="naive", seeds=tuple(seeds), n_tasks=n_tasks,
                   envs=(env,))
    _, fault_name = fault_config_from(fault_config)
    ep_root = Path(out) / "episodes"
    run(spec, str(ep_root), skip_existing=True, only_env=env)

    shard = Path(out) / f"{env}__{fault_name}.jsonl"
    src = ep_root / model_tag(teacher) / fault_name / "naive"
    with shard.open("w", encoding="utf-8") as fh:
        for p in sorted(src.glob(f"{env}__*.json")):
            rec = json.loads(p.read_text(encoding="utf-8"))
            fh.write(json.dumps(rec["trajectory"], ensure_ascii=False) + "\n")
    print(f"[gen-data] wrote {shard}")
    return str(shard)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--fault-config", required=True)
    ap.add_argument("--teacher", required=True)
    ap.add_argument("--n-tasks", type=int, default=200)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    generate(env=args.env, fault_config=args.fault_config, teacher=args.teacher,
             n_tasks=args.n_tasks, seeds=tuple(args.seeds), out=args.out)


if __name__ == "__main__":
    main()
