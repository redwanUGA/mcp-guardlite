"""mcpguardlite CLI.

    mcpguardlite eval --model scripted --fault-config mixed_r15 --method naive \
                      --env fs --n-tasks 5 --seeds 0 --out results/dev
    mcpguardlite eval ... --task-index 3 --seed 0        # one episode (SLURM stride)
    mcpguardlite gen-data --env fs --fault-config mixed_r15 --teacher <hf_id> --out data/raw
    mcpguardlite tables --results results/dev --out paper/tables.tex
    mcpguardlite pair-check --baseline <dir> --compressed <dir>

train-sentinel / quantize / bench-edge land in W2-W3 (HANDOFF §3.6-3.9).
"""
import argparse


def main():
    ap = argparse.ArgumentParser(prog="mcpguardlite")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("eval", help="run episodes through the fault harness")
    ev.add_argument("--model", required=True,
                    help="'scripted' or an HF model id (optionally id@dtype)")
    ev.add_argument("--fault-config", required=True,
                    help="path to configs/faults/*.yaml or a bare name")
    ev.add_argument("--method", default="naive",
                    choices=["naive", "retry_only", "reflect", "full_replan",
                             "guardlite", "oracle"])
    ev.add_argument("--env", default=None,
                    help="one env (fs|kv|http|cal|sensor|compute); default all")
    ev.add_argument("--n-tasks", type=int, default=200)
    ev.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ev.add_argument("--task-index", type=int, default=None,
                    help="run only this task index (one joblist line per episode)")
    ev.add_argument("--sentinel", default=None, help="path for method=guardlite")
    ev.add_argument("--max-turns", type=int, default=12)
    ev.add_argument("--limit-episodes", type=int, default=None)
    ev.add_argument("--no-skip-existing", action="store_true")
    ev.add_argument("--out", required=True)

    gd = sub.add_parser("gen-data", help="teacher trajectory generation shard")
    gd.add_argument("--env", required=True)
    gd.add_argument("--fault-config", required=True)
    gd.add_argument("--teacher", required=True)
    gd.add_argument("--n-tasks", type=int, default=200)
    gd.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    gd.add_argument("--out", required=True)

    tb = sub.add_parser("tables", help="aggregate metrics from raw traces")
    tb.add_argument("--results", required=True)
    tb.add_argument("--out", required=True)

    pc = sub.add_parser("pair-check", help="assert the paired-design invariant")
    pc.add_argument("--baseline", required=True)
    pc.add_argument("--compressed", required=True)

    for name in ("train-sentinel", "quantize", "bench-edge"):
        sub.add_parser(name)

    args = ap.parse_args()

    if args.cmd == "eval":
        from .eval.harness import RunSpec, run
        spec = RunSpec(model_config=args.model, fault_config=args.fault_config,
                       method=args.method, seeds=tuple(args.seeds),
                       n_tasks=args.n_tasks, sentinel_path=args.sentinel,
                       max_turns=args.max_turns)
        run(spec, args.out, skip_existing=not args.no_skip_existing,
            task_index=args.task_index, only_env=args.env,
            limit_episodes=args.limit_episodes)
    elif args.cmd == "gen-data":
        from .data.generate import generate
        generate(env=args.env, fault_config=args.fault_config,
                 teacher=args.teacher, n_tasks=args.n_tasks,
                 seeds=tuple(args.seeds), out=args.out)
    elif args.cmd == "tables":
        from .eval.harness import make_tables
        make_tables(args.results, args.out)
    elif args.cmd == "pair-check":
        from .eval.harness import assert_paired
        assert_paired(args.baseline, args.compressed)
        print("paired-design invariant holds")
    else:
        raise SystemExit(f"not implemented yet: {args.cmd} (see HANDOFF.md §3)")


if __name__ == "__main__":
    main()
