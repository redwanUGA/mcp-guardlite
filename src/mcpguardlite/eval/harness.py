"""Experiment driver. One entry point produces one row of one table.

Paired-design invariant (enforce it, do not trust it):
    for a given (task, fault_config, seed), EVERY compression config must see
    an identical fault schedule. assert_paired() below is called before any
    RCG is computed; if it trips, the run is discarded, not patched.

Episode identity: `episode_id = f"{env}:{task_id}:s{seed}"` -- deliberately
free of the model config, because it feeds the fault PRF (invariant I1).

Output layout (idempotent; one JSON per episode so SLURM striding workers can
--skip_existing their way through a joblist, PITL-style):
    out_dir/<model_tag>/<fault_config>/<method>/<env>__<task_id>__s<seed>.json
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from ..agent.loop import AgentLoop, LoopConfig
from ..agent.policy import make_policy
from ..agent.recovery import RecoveryBudget, RecoveryController
from ..agent.sentinel import Sentinel, rule_baseline
from ..data.trajectory import Trajectory, SCHEMA_VERSION
from ..envs.servers import TRAIN_ENVS, make_server
from ..envs.tasks import build_tasks, verify_episode
from ..faults.injector import FaultConfig
from ..faults.proxy import FaultProxy


@dataclass
class RunSpec:
    model_config: str          # "scripted" | "Qwen/Qwen2.5-1.5B-Instruct@float16"
    fault_config: str          # path to configs/faults/*.yaml, or a bare name
    profile: str = "E0"        # "E0" (unconstrained) | "E1" | "E2" | "E3"
    method: str = "naive"      # naive | retry_only | reflect | full_replan | guardlite | oracle
    seeds: tuple = (0, 1, 2)
    n_tasks: int = 200
    envs: tuple = ("fs", "kv", "http", "cal", "sensor", "compute")
    sentinel_path: str | None = None
    max_turns: int = 12


def model_tag(model_config: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model_config)


def _json_default(o):
    """Trace records must never die on a numpy scalar (llama-cpp logprobs,
    sklearn outputs). item() covers every numpy scalar type."""
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def fault_config_from(path_or_name: str) -> tuple[FaultConfig, str]:
    p = Path(path_or_name)
    if not p.exists():
        p = Path("configs/faults") / f"{path_or_name}.yaml"
    return FaultConfig.from_yaml(str(p)), p.stem


def _components(method: str, sentinel_path: str | None):
    """sentinel, controller, reflect flag -- the whole baseline grid."""
    budget = RecoveryBudget()
    if method == "naive":
        return None, None, False
    if method == "retry_only":
        return rule_baseline, RecoveryController(budget, "retry_only"), False
    if method == "reflect":
        return None, None, True
    if method == "full_replan":
        return rule_baseline, RecoveryController(budget, "replan_only"), False
    if method == "guardlite":
        if not sentinel_path:
            raise ValueError("guardlite needs --sentinel <path>")
        return Sentinel.load(sentinel_path), RecoveryController(budget, "full"), False
    if method == "oracle":
        return "oracle", RecoveryController(budget, "full"), False
    raise ValueError(f"unknown method: {method}")


async def run_episode(policy, task, seed: int, fault_cfg: FaultConfig,
                      spec: RunSpec, fault_name: str) -> dict:
    episode_id = f"{task.env}:{task.task_id}:s{seed}"
    server = make_server(task.env, seed)
    proxy = FaultProxy({task.env: server}, fault_cfg)
    sentinel, controller, reflect = _components(spec.method, spec.sentinel_path)
    loop = AgentLoop(policy, proxy, sentinel=sentinel, controller=controller,
                     cfg=LoopConfig(max_turns=spec.max_turns,
                                    reflect_on_error=reflect))
    res = await loop.run(task, episode_id)
    success = bool(res.asserted_success and
                   verify_episode(task, seed, server.state_digest(), res.answer))

    traj = Trajectory(
        episode_id=episode_id, env=task.env, task_id=task.task_id,
        tier=task.tier, model_config=spec.model_config, fault_config=fault_name,
        seed=seed, turns=res.turn_records, success=success,
        asserted_success=res.asserted_success,
        split="iid_train" if task.env in TRAIN_ENVS else "heldout_env")
    return {
        "schema": SCHEMA_VERSION,
        "trajectory": asdict(traj),
        "episode": {
            "episode_id": episode_id, "config": spec.model_config,
            "fault_fired": bool(res.fault_events), "success": success,
            "asserted_success": res.asserted_success,
            "recovery_actions": res.recovery_actions, "tokens": res.tokens,
            "wall_s": res.wall_s, "joules": res.joules,
            "answer": str(res.answer)[:500],
            "fault_families": sorted({e["family"] for e in res.fault_events}),
            "method": spec.method, "profile": spec.profile,
        },
    }


def episode_path(out_dir: str, spec: RunSpec, fault_name: str,
                 env: str, task_id: str, seed: int) -> Path:
    return (Path(out_dir) / model_tag(spec.model_config) / fault_name
            / spec.method / f"{env}__{task_id}__s{seed}.json")


def run(spec: RunSpec, out_dir: str, *, skip_existing: bool = True,
        task_index: int | None = None, only_env: str | None = None,
        limit_episodes: int | None = None) -> str:
    """Run the spec (or a single (env, task_index) slice of it for SLURM
    striding). Returns the output root."""
    fault_cfg, fault_name = fault_config_from(spec.fault_config)
    policy = make_policy(spec.model_config)
    envs = [only_env] if only_env else list(spec.envs)
    n_done = 0
    for env in envs:
        tasks = build_tasks(env, spec.n_tasks)
        if task_index is not None:
            tasks = [tasks[task_index]]
        for task in tasks:
            for seed in spec.seeds:
                if limit_episodes is not None and n_done >= limit_episodes:
                    return out_dir
                path = episode_path(out_dir, spec, fault_name, env,
                                    task.task_id, seed)
                if skip_existing and path.exists():
                    n_done += 1
                    continue
                record = asyncio.run(
                    run_episode(policy, task, seed, fault_cfg, spec, fault_name))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(record, ensure_ascii=False,
                                           default=_json_default),
                                encoding="utf-8")
                n_done += 1
                ep = record["episode"]
                print(f"[episode] {ep['episode_id']} method={spec.method} "
                      f"fault_fired={ep['fault_fired']} success={ep['success']} "
                      f"asserted={ep['asserted_success']} turns="
                      f"{len(record['trajectory']['turns'])}", flush=True)
    return out_dir


# --------------------------------------------------------------------------- #
# pairing + tables
# --------------------------------------------------------------------------- #

def _load_fault_decisions(trace_dir: str) -> dict:
    """(episode_id, turn, tool) -> family, over every fired fault in a run dir."""
    out = {}
    for p in Path(trace_dir).rglob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        for t in rec["trajectory"]["turns"]:
            if t["fault_present"]:
                key = (rec["trajectory"]["episode_id"], t["request_json"]["id"],
                       t["tool"])
                out[key] = t["fault_family"]
    return out


def assert_paired(baseline_traces: str, compressed_traces: str) -> None:
    """Compare the (episode_id, turn, family) fault sequences; raise on mismatch.

    Models diverge in WHICH calls they make, so the check is over the shared
    support: every (episode, turn, tool) coordinate that appears in both runs
    must have drawn the same fault. A single mismatch means the schedule was
    not a pure function of (seed, episode, turn, tool) -- discard the run."""
    a = _load_fault_decisions(baseline_traces)
    b = _load_fault_decisions(compressed_traces)
    shared = set(a) & set(b)
    bad = [k for k in shared if a[k] != b[k]]
    if bad:
        raise AssertionError(
            f"paired-design violation on {len(bad)}/{len(shared)} shared fault "
            f"coordinates, e.g. {bad[:3]} -- fault schedule depended on the "
            "model config; every RCG from this pair is invalid (I1)")


def load_episodes(results_dir: str) -> list:
    from ..eval.metrics import Episode
    eps = []
    for p in Path(results_dir).rglob("*.json"):
        e = json.loads(p.read_text(encoding="utf-8"))["episode"]
        eps.append(Episode(
            episode_id=e["episode_id"], config=e["config"],
            fault_fired=e["fault_fired"], success=e["success"],
            asserted_success=e["asserted_success"],
            recovery_actions=e["recovery_actions"], tokens=e["tokens"],
            wall_s=e["wall_s"], joules=e["joules"],
            fault_families=e["fault_families"]))
    return eps


def make_tables(results_dir: str, out_tex: str) -> None:
    """Regenerate summary metrics from raw traces. W1 version: one block per
    (config) with TSR / TSR_phi / RSR / SFR / ROR; the full paper tables land
    with `mcpguardlite tables` in W3 (fill cells from here, never by hand)."""
    from ..eval import metrics as M
    eps = load_episodes(results_dir)
    configs = sorted({e.config for e in eps})
    lines = ["% auto-generated by mcpguardlite -- do not hand-edit",
             "\\begin{tabular}{lrrrrrr}",
             "config & n & TSR & TSR$_\\phi$ & RSR & SFR & ROR \\\\"]
    for c in configs:
        sub = [e for e in eps if e.config == c]
        lines.append(
            f"{c} & {len(sub)} & {M.tsr(sub):.3f} & {M.tsr_phi(sub):.3f} & "
            f"{M.rsr(sub):.3f} & {M.sfr(sub):.3f} & {M.ror(sub):.3f} \\\\")
    lines.append("\\end{tabular}")
    Path(out_tex).parent.mkdir(parents=True, exist_ok=True)
    Path(out_tex).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
