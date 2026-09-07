"""Quantization, including the paper's failure-aware PTQ calibration (RQ5).

The novel bit is one line: swap the calibration corpus. GPTQ/AWQ estimate
activation statistics from calibration text -- conventionally WikiText. We
calibrate on MCP-FaultTrace recovery turns so the activation ranges preserved
are the ones exercised during fault handling. Zero inference-time cost.

Four arms, fixed bit-width:
    generic   WikiText-2
    nominal   fault-free tool-calling traces
    recovery  MCP-FaultTrace turns where a fault fired      <- ours
    mixture   50/50 generic + recovery
Keep n_samples and seq_len IDENTICAL across arms or the comparison is void
(invariant I6): every arm flows through the SAME `_pack()` below -- there is
deliberately no per-arm length/count code path.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

CALIB_ARMS = ("generic", "nominal", "recovery", "mixture")

# The GGUF grid for RQ1 (HANDOFF §5). F16 is the uncompressed anchor.
GGUF_LEVELS = ("F16", "Q8_0", "Q5_K_M", "Q4_K_M", "Q3_K_M")


# --------------------------------------------------------------------------- #
# GGUF export (llama.cpp)
# --------------------------------------------------------------------------- #

def _llama_cpp_dir() -> Path:
    d = os.environ.get("LLAMA_CPP_DIR", "")
    if not d:
        raise RuntimeError("set LLAMA_CPP_DIR to a llama.cpp checkout (the "
                           "commit is pinned in scripts/env.sh -- keep Pi and "
                           "cluster identical)")
    return Path(d)


def _run(cmd: list[str]) -> None:
    print("[quantize] $", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def export_gguf(model_dir: str, quant: str = "Q4_K_M", out: str = "",
                f16_path: str = "") -> str:
    """HF checkpoint -> GGUF at `quant`. Two steps, both llama.cpp-official:
    convert_hf_to_gguf.py (once, to F16) then llama-quantize.

    `model_dir` may be an HF repo id or a local snapshot path. `f16_path` is
    reused across quant levels so conversion happens once per model."""
    llama = _llama_cpp_dir()
    out = out or f"{Path(model_dir).name}-{quant}.gguf"
    f16 = Path(f16_path) if f16_path else Path(out).with_name(
        f"{Path(model_dir).name}-F16.gguf")

    if not f16.exists():
        _run(["python", llama / "convert_hf_to_gguf.py", model_dir,
              "--outfile", f16, "--outtype", "f16"])
    if quant.upper() == "F16":
        return str(f16)

    quantize_bin = next((p for p in (
        llama / "build" / "bin" / "llama-quantize",
        llama / "llama-quantize") if p.exists()), None)
    if quantize_bin is None:
        raise RuntimeError(f"llama-quantize not found under {llama} -- build "
                           "llama.cpp first (see gacrc/launch_w2.py bootstrap)")
    _run([quantize_bin, f16, out, quant])
    return str(out)


def export_grid(model_dir: str, out_dir: str,
                levels: tuple = GGUF_LEVELS, name: str = "") -> dict[str, str]:
    """The whole RQ1 grid in one call; returns {level: gguf_path}.

    Pass `name` explicitly when `model_dir` is an HF cache snapshot -- its
    basename is a content hash, not a model name."""
    outd = Path(out_dir)
    outd.mkdir(parents=True, exist_ok=True)
    name = (name or Path(model_dir).name).lower()
    f16 = outd / f"{name}-F16.gguf"
    paths = {}
    for level in levels:
        target = f16 if level == "F16" else outd / f"{name}-{level}.gguf"
        if not target.exists():
            export_gguf(model_dir, level, str(target), f16_path=str(f16))
        paths[level] = str(target)
    return paths


# --------------------------------------------------------------------------- #
# calibration corpora (RQ5)
# --------------------------------------------------------------------------- #

def _render_turn(tokenizer, turn: dict, instruction: str) -> str:
    """Format one FaultTrace turn EXACTLY as the model sees tool traffic at
    inference (same chat template, same result framing as policy.next_action),
    otherwise the activation statistics are off-distribution anyway."""
    call = json.dumps({"name": turn["tool"], "arguments": turn["args"]},
                      ensure_ascii=False)
    result = json.dumps(turn["response_json"], ensure_ascii=False,
                        default=str)[:4000]
    messages = [
        {"role": "user", "content": instruction},
        {"role": "assistant", "content": f"<tool_call>{call}</tool_call>"},
        {"role": "user", "content": f"Tool result for {turn['tool']}: {result}"},
    ]
    return tokenizer.apply_chat_template(messages, tokenize=False,
                                         add_generation_prompt=True)


def _trace_texts(traces_dir: str, tokenizer, *, want_fault: bool) -> list[str]:
    texts = []
    for shard in sorted(Path(traces_dir).rglob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            traj = json.loads(line)
            instruction = f"Task {traj['task_id']} in environment {traj['env']}."
            for turn in traj["turns"]:
                if bool(turn["fault_present"]) == want_fault:
                    texts.append(_render_turn(tokenizer, turn, instruction))
    return texts


def _wikitext(n_needed: int) -> list[str]:
    from datasets import load_dataset
    ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="train")
    return [t for t in ds["text"] if len(t) > 200][: n_needed * 4]


def _pack(texts: list[str], tokenizer, n_samples: int, seq_len: int):
    """The single shared exit path for every arm (I6): concatenate, tokenize,
    slice into exactly n_samples windows of exactly seq_len tokens."""
    ids: list[int] = []
    for t in texts:
        ids.extend(tokenizer(t, add_special_tokens=False).input_ids)
        if len(ids) >= n_samples * seq_len + 1:
            break
    if len(ids) < n_samples * seq_len:
        raise ValueError(f"corpus too small: {len(ids)} tokens < "
                         f"{n_samples * seq_len} needed -- generate more traces")
    return [ids[i * seq_len:(i + 1) * seq_len] for i in range(n_samples)]


def build_calibration_set(arm: str, n_samples: int = 512, seq_len: int = 2048,
                          traces_dir: str = "data/raw",
                          tokenizer_id: str = "Qwen/Qwen2.5-1.5B-Instruct"):
    """Return n_samples token sequences of seq_len for the given arm."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(tokenizer_id)
    if arm == "generic":
        texts = _wikitext(n_samples)
    elif arm == "nominal":
        texts = _trace_texts(traces_dir, tok, want_fault=False)
    elif arm == "recovery":
        texts = _trace_texts(traces_dir, tok, want_fault=True)
    elif arm == "mixture":
        rec = _trace_texts(traces_dir, tok, want_fault=True)
        gen = _wikitext(n_samples)
        texts = [t for pair in zip(rec, gen) for t in pair]   # strict 50/50
    else:
        raise ValueError(f"unknown arm: {arm} (use one of {CALIB_ARMS})")
    return _pack(texts, tok, n_samples, seq_len)


def quantize_gptq(model_id: str, arm: str, bits: int = 4, out: str = ""):
    raise NotImplementedError("W3: GPTQ arms after the RQ1 pilot verdict")


def quantize_awq(model_id: str, arm: str, bits: int = 4, out: str = ""):
    raise NotImplementedError("W3: AWQ arms after the RQ1 pilot verdict")
