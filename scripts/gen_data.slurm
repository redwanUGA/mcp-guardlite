#!/bin/bash
#SBATCH --job-name=faulttrace
#SBATCH --array=0-23
#SBATCH --partition=gpu_p
#SBATCH --gres=gpu:A100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/gen_%A_%a.out

# One array task per (env x fault_config) cell -> independent JSONL shards.
source scripts/env.sh
ENVS=(fs kv http cal sensor compute)
FCFGS=(mixed_r15 overt_only silent_only clean)
E=${ENVS[$((SLURM_ARRAY_TASK_ID / 4))]}
F=${FCFGS[$((SLURM_ARRAY_TASK_ID % 4))]}

python -m mcpguardlite.data.generate \
  --env "$E" --fault-config "configs/faults/${F}.yaml" \
  --teacher "$TEACHER" --n-tasks 200 --seeds 0 1 2 \
  --out "data/raw/${E}__${F}.jsonl"
