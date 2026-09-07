"""R3 hand-audit pack: sampled silent mutations for human review.

HANDOFF §6 R3: "hand-audit 50 sampled mutations per environment before the
full run; document the audit in the paper." If S* mutations are detectable by
schema or by obvious implausibility, RQ3's headline row measures nothing.

This module generates the audit pack deterministically:
    python -m mcpguardlite.envs.audit --out audits/silent_fault_audit.md

Each row shows the nominal result and the mutated result side by side with the
family, tool, and sampled params. The reviewer marks rows IMPLAUSIBLE when a
human operator would notice something wrong WITHOUT ground truth (absurd
magnitude, broken format, self-contradiction inside one payload). The pass
bar for the paper: >= 95% plausible per environment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .mutators import MUTATORS, SILENT_OPS
from .servers import REGISTRY, make_server
from ..faults.injector import FaultScheduler, FaultConfig, prf_choice, prf_unit
from ..faults.taxonomy import TAXONOMY

# canonical per-op argument samplers (mirrors tests/test_silent_faults_*)
def _args_for(env: str, op: str, server, k: int):
    if env == "fs":
        paths = sorted(server.files)
        if op in ("read", "stat"):
            return {"path": paths[k % len(paths)]}
        if op == "list":
            return {"path": ["/docs", "/src", "/data", "/notes"][k % 4]}
        return {"query": ["system", "report", "deploy", "metric"][k % 4]}
    if env == "kv":
        keys = sorted(server.store)
        if op == "get":
            return {"key": keys[k % len(keys)]}
        if op == "getv":
            key = keys[k % len(keys)]
            return {"key": key, "version": 1 + k % len(server.store[key]["versions"])}
        return {"prefix": ["config:", "user:", "inv:", "cache:"][k % 4]}
    if env == "http":
        urls = sorted(server.pages)
        return {"url": urls[k % len(urls)]}
    if env == "cal":
        if op == "get":
            ids = sorted(server.events)
            return {"event_id": ids[k % len(ids)]}
        return {"date": f"2026-09-{8 + k % 4:02d}"}
    if env == "sensor":
        dev = f"dev-{k % 6}"
        return {"device_id": dev, "n": 4} if op == "history" else {"device_id": dev}
    # compute
    if op == "stats":
        vals = [round(3 + 0.7 * ((k + j) % 11), 1) for j in range(4 + k % 3)]
        return {"values": vals, "op": ["mean", "max", "min", "sum"][k % 4]}
    if op == "convert":
        pairs = [("C", "F"), ("C", "K"), ("km", "m"), ("kg", "lb")]
        f, t = pairs[k % 4]
        return {"value": round(5 + 2.3 * (k % 9), 2), "from_unit": f, "to_unit": t}
    return {"expression": f"{11 + k} * {3 + k % 5} + {k % 7}"}


def sample_mutations(env: str, n: int = 50, seed: int = 0) -> list[dict]:
    """n deterministic (family, op) samples with nominal vs mutated payloads."""
    rows = []
    combos = [(fam, op) for fam in ("S1", "S2", "S3", "S4")
              for op in sorted(SILENT_OPS.get((env, fam), ()))]
    server = make_server(env, seed)
    k = 0
    while len(rows) < n:
        fam, op = combos[k % len(combos)]
        tool = f"{env}.{op}"
        args = _args_for(env, op, server, k)
        try:
            nominal = server.call_tool(tool, args)
        except Exception:
            k += 1
            continue
        params = {}
        if fam == "S1":
            spec = TAXONOMY[fam].params.get("staleness_steps")
            params["staleness_steps"] = int(1 + prf_unit(seed, env, k, "st") *
                                            ((spec or (1, 10))[1] - 1))
        salt = ("audit", env, k)
        mutated = MUTATORS[(env, fam)](dict(nominal), params=params,
                                       server=server, tool=tool, args=args,
                                       salt=salt)
        if mutated == nominal:
            k += 1
            continue                      # no-bite sample: not auditable
        rows.append({"i": len(rows), "family": fam, "tool": tool,
                     "args": args, "params": params,
                     "nominal": nominal, "mutated": mutated})
        k += 1
        if k > 40 * n:                    # safety: never loop forever
            break
    return rows


def write_audit_pack(out: str, n: int = 50, seed: int = 0) -> str:
    lines = ["# Silent-fault hand-audit pack (R3)", "",
             "Mark a row IMPLAUSIBLE if a human operator would notice the",
             "mutation WITHOUT ground truth. Pass bar: >= 95% plausible per env.",
             "Fill the verdict column with `ok` or `implausible: <why>`.", ""]
    summary = {}
    for env in sorted(REGISTRY):
        rows = sample_mutations(env, n=n, seed=seed)
        summary[env] = len(rows)
        lines.append(f"\n## {env} ({len(rows)} samples)\n")
        lines.append("| # | family | tool | nominal | mutated | verdict |")
        lines.append("|---|--------|------|---------|---------|---------|")
        for r in rows:
            nom = json.dumps(r["nominal"], ensure_ascii=False)[:160]
            mut = json.dumps(r["mutated"], ensure_ascii=False)[:160]
            nom = nom.replace("|", "\\|")
            mut = mut.replace("|", "\\|")
            lines.append(f"| {r['i']} | {r['family']} | {r['tool']} "
                         f"| `{nom}` | `{mut}` |  |")
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    print(f"[audit] wrote {p} ({sum(summary.values())} samples: {summary})")
    return str(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="audits/silent_fault_audit.md")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    write_audit_pack(args.out, n=args.n, seed=args.seed)


if __name__ == "__main__":
    main()
