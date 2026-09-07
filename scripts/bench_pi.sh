#!/usr/bin/env bash
# Run ON the Pi 5. Everything must already be local: models, envs, traces.
set -euo pipefail
source scripts/env.sh

sudo cpufreq-set -g performance 2>/dev/null || true
vcgencmd measure_temp

for Q in Q5_K_M Q4_K_M Q3_K_M; do
  llama-bench -m "models/qwen1.5b-${Q}.gguf" -t 4 -c 4096 -p 512 -n 128 \
    -o json > "results/pi/bench_${Q}.json"
  python -m mcpguardlite.cli eval --spec configs/runs/rq6_pi.yaml \
    --model "models/qwen1.5b-${Q}.gguf" --out "results/pi/eval_${Q}/"
done

# Thermal honesty: log temperature throughout and discard runs that throttle,
# or report them separately. A silently throttled Pi produces a number that
# looks like a result and is not one.
