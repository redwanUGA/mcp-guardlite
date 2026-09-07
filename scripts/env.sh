#!/usr/bin/env bash
# Pin everything that can drift between cluster and Pi.
# llama.cpp commit built on GACRC 2026-09-05 (gacrc/launch_w2.py bootstrap);
# build the SAME commit on the Pi so tok/s and quality are comparable.
export LLAMA_CPP_COMMIT="74a7c897f049c17e7080423aa2111776eff6ebbf"
export LLAMA_CPP_PYTHON_VERSION="0.3.35"
export TORCH_VERSION="2.14.0+cu126"     # cu126: gpu_p V100S nodes lack sm_70 in cu130
export TRANSFORMERS_VERSION="5.16.1"
export PYTHONHASHSEED=0
export TOKENIZERS_PARALLELISM=false
