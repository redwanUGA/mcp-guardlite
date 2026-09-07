# MCP-GuardLite / MCP-FaultBench

**A deterministic fault-injection benchmark for measuring how model compression
affects the failure *recovery* of tool-using LLM agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Everyone benchmarks compressed small language models on happy-path tool
calling, and everyone studies agent failure recovery at full precision on
cloud models. Nobody had crossed the two. This harness measures whether
compression costs an agent more *recovery* competence than *nominal*
competence — a paired quantity we call the **Resilience Compression Gap
(RCG)** — under a reproducible fault process injected at the agent↔tool
boundary, where edge deployments actually break.

## What's inside

- **16-family fault taxonomy** across four classes — Transport, Protocol,
  Semantic (silent), Resource — each with detectability, persistence, and a
  ground-truth recovery operator ([`faults/taxonomy.py`](src/mcpguardlite/faults/taxonomy.py)).
- **Deterministic, paired injection**: fault decisions are a pure function of
  `(seed, episode, turn, tool, family)` — every compression configuration
  faces *identical* faults at *identical* turns, so RCG measures the model,
  not the dice ([`faults/injector.py`](src/mcpguardlite/faults/injector.py)).
- **Silent faults that are actually silent**: semantic mutators (stale values,
  unit confusions, empty-as-success, cross-tool contradictions) provably pass
  JSON-Schema validation; a 300-sample hand-audit pack ships in
  [`audits/`](audits/).
- **Six offline MCP-style servers** (filesystem, KV store, recorded HTTP,
  calendar, sensors, compute) — no network, no API keys; the whole benchmark
  runs on a laptop or a Raspberry Pi ([`envs/servers.py`](src/mcpguardlite/envs/servers.py)).
- **100% programmatic verification**: every task carries a replayable gold
  plan; success is judged by state-digest comparison and deterministic answer
  derivation. No LLM judge anywhere.
- **Silent-failure rate (SFR)** measured by recording what the agent *claims*
  separately from what the verifier finds.
- **A recovery-assistance ladder** — `naive`, `retry_only`, `reflect`,
  `full_replan`, and a fault-`oracle` upper bound — that separates *detecting*
  faults from the capacity to *execute* recovery.
- **Compression grid tooling**: GGUF export (F16 → Q8_0/Q5_K_M/Q4_K_M/Q3_K_M
  via a pinned llama.cpp), plus policy backends for HF transformers and
  llama-cpp-python that capture per-turn decoder statistics.

## Quickstart (no GPU, no model download)

The scripted policy exercises the *entire* harness — servers, injector,
proxy, agent loop, verifier, metrics — in seconds:

```bash
pip install -e . --no-deps && pip install numpy scipy pyyaml jsonschema pytest
pytest -q                        # full test suite

python -m mcpguardlite.cli eval \
  --model scripted --fault-config configs/faults/mixed_r10_noP3.yaml \
  --method naive --env fs --n-tasks 8 --seeds 0 1 2 --out results/demo
python -m mcpguardlite.cli tables --results results/demo --out results/demo.tex
```

## Running a real model

```bash
# HF transformers arm (FP16)
python -m mcpguardlite.cli eval --model Qwen/Qwen2.5-1.5B-Instruct \
  --fault-config configs/faults/mixed_r10_noP3.yaml --method naive \
  --env fs --n-tasks 8 --seeds 0 --out results/fp16

# GGUF arm (llama.cpp; same chat template, so backend is never a confound)
python -m mcpguardlite.cli eval --model gguf:models/qwen2.5-1.5b-instruct-Q4_K_M.gguf ...
```

Build the quantization grid with
[`compress/quantize.py`](src/mcpguardlite/compress/quantize.py)
(`export_grid`) against the llama.cpp commit pinned in
[`scripts/env.sh`](scripts/env.sh).

## Key metrics

| Metric | Meaning |
|---|---|
| `TSR` | task success rate on fault-free episodes |
| `TSR_φ` | task success under the fault process |
| `RSR` | success restricted to episodes where a fault actually **fired** |
| `SFR` | agent asserts success, verifier disagrees (silent failure) |
| `RCG` | `[ΔRSR − ΔTSR]` vs the FP16 anchor, in pp — recovery loss *beyond* nominal loss |

Analysis entry points: [`eval/metrics.py`](src/mcpguardlite/eval/metrics.py)
(definitions + cluster bootstrap + paired tests) and
[`eval/rq1.py`](src/mcpguardlite/eval/rq1.py) (paired RCG with CIs and the
pre-registered GO/REFRAME/SUSPECT decision rule).

## Reproducibility invariants (tested)

1. Fault schedules are model-independent (`tests/test_determinism.py`).
2. RSR is computed only over triggered episodes.
3. Asserted success is recorded separately from verified success.
4. Silent mutations pass schema validation (`tests/test_silent_faults_are_wellformed.py`).
5. The trace schema is frozen and guarded (`tests/test_trace_schema_frozen.py`).
6. `assert_paired` verifies the paired design post-hoc before any RCG is computed.

## Citation

A paper describing the benchmark and the first controlled measurement of the
compression–recovery interaction is under review; a citation entry will
appear here.

## License

[MIT](LICENSE).
