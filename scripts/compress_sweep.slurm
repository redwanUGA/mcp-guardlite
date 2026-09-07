#!/bin/bash
#SBATCH --job-name=compress
#SBATCH --array=0-19
#SBATCH --gres=gpu:A100:1
#SBATCH --mem=96G
#SBATCH --time=08:00:00
source scripts/env.sh
python -m mcpguardlite.cli quantize --grid configs/compression/grid.yaml \
       --index "$SLURM_ARRAY_TASK_ID" --out models/
