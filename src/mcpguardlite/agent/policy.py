"""Policy backends.

Two implementations behind one interface:

  ScriptedPolicy  deterministic gold-plan follower. No GPU, no model. It applies
                  the task's own extraction spec to what it OBSERVES, so silent
                  faults corrupt its answer the same way they corrupt a model's
                  -- the whole harness (proxy, injector, mutators, verifier,
                  metrics) is exercisable end-to-end on a laptop in seconds.
  HFPolicy        HuggingFace transformers backend (FP16 teacher and any HF-side
                  quantized arm). Captures decoder statistics per emitted call
                  (mean logprob / entropy / top1 margin) -- the sentinel's only
                  compression-sensitive signal (agent/loop.py behaviour #1).

The interface is deliberately tiny:
    start_episode(task, tools)      -> None
    next_action(observation | None) -> PolicyAction
`observation` is the previous turn's outcome:
    {"tool", "args", "response", "latency_ms", "note"?}
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

from ..envs.tasks import Task, derive_answer, resolve_args
from ..envs.servers import ToolError
from ..faults.injector import prf_unit


@dataclass
class PolicyAction:
    kind: str                    # "tool_call" | "final" | "abstain"
    tool: str | None = None
    args: dict | None = None
    text: str = ""
    decoder_stats: dict = field(default_factory=dict)
    tokens_used: int = 0


class Policy(Protocol):
    def start_episode(self, task: Task, tools: list[dict]) -> None: ...
    def next_action(self, observation: dict | None) -> PolicyAction: ...


# --------------------------------------------------------------------------- #
# helpers shared by both backends
# --------------------------------------------------------------------------- #

def response_is_error(response: dict) -> bool:
    return (not isinstance(response, dict)
            or "__transport_error__" in response
            or "__raw_bytes__" in response
            or "error" in response)


_DRIFT_RE = re.compile(r"unknown parameter '(\w+)'.*expects '(\w+)'")


def drift_hint(response: dict) -> tuple[str, str] | None:
    """Extract a P3 rename hint from an error message, if present."""
    msg = str(response.get("error", {}).get("message", "")) if isinstance(response, dict) else ""
    m = _DRIFT_RE.search(msg)
    return (m.group(1), m.group(2)) if m else None


# --------------------------------------------------------------------------- #
# scripted
# --------------------------------------------------------------------------- #

class ScriptedPolicy:
    """Deterministic plan follower with shallow, believable error handling:
    retry a failed step up to `max_retries`, adapt to a P3 rename hint, then
    move on with whatever it observed. If the final extraction comes up empty
    it abstains; otherwise it asserts an answer -- possibly a corrupted one,
    which is exactly the silent-failure behaviour SFR must be able to see."""

    def __init__(self, max_retries: int = 2, seed: int = 0):
        self.max_retries = max_retries
        self.seed = seed

    def start_episode(self, task: Task, tools: list[dict]) -> None:
        self.task = task
        self.step = 0
        self.retries = 0
        self.results: list[dict] = []       # observed RESULT object per plan step
        self._errors_seen = 0
        self._rename: tuple[str, str] | None = None

    # ---- decoder stats: synthetic but deterministic and fault-responsive ----
    def _stats(self, tag: str) -> dict:
        u = prf_unit("scripted", self.seed, self.task.task_id, self.step,
                     self.retries, tag)
        stress = min(self._errors_seen, 3) * 0.25
        return {"mean_logprob": round(-0.25 - 0.1 * u - 0.3 * stress, 4),
                "entropy": round(0.6 + 0.2 * u + 0.5 * stress, 4),
                "top1_margin": round(max(0.05, 0.65 - 0.1 * u - 0.2 * stress), 4)}

    def next_action(self, observation: dict | None) -> PolicyAction:
        task = self.task
        if observation is not None:
            resp = observation["response"]
            if response_is_error(resp):
                self._errors_seen += 1
                hint = drift_hint(resp)
                if hint:
                    self._rename = hint
                if self.retries < self.max_retries:
                    self.retries += 1
                else:                        # give up on this step, record a hole
                    self.results.append({})
                    self.step += 1
                    self.retries = 0
            else:
                self.results.append(resp.get("result", {}))
                self.step += 1
                self.retries = 0
                self._rename = None

        if self.step >= len(task.gold_plan):
            answer = (derive_answer(self.results, task.answer_spec)
                      if task.answer_spec else "done")
            if answer is None:
                return PolicyAction("abstain", text="could not derive an answer",
                                    decoder_stats=self._stats("abstain"),
                                    tokens_used=24)
            return PolicyAction("final", text=str(answer),
                                decoder_stats=self._stats("final"), tokens_used=24)

        tool, template = task.gold_plan[self.step]
        try:
            args = resolve_args(template, self.results)
        except ToolError:
            # upstream result was corrupted/unusable -> cannot build this call
            self.results.append({})
            self.step += 1
            self.retries = 0
            return self.next_action(None)
        if self._rename:
            old, new = self._rename
            if old in args:
                args[new] = args.pop(old)
        return PolicyAction("tool_call", tool=tool, args=args,
                            decoder_stats=self._stats("call"), tokens_used=48)


# --------------------------------------------------------------------------- #
# huggingface
# --------------------------------------------------------------------------- #

_SYSTEM = """You are a tool-using assistant. Solve the task using ONLY the tools listed below.

Protocol (follow exactly):
- Make ONE tool call per reply, using exactly this form:
  <tool_call>{{"name": "<tool name>", "arguments": {{...}}}}</tool_call>
- Keep calling tools, one per reply, until EVERY part of the task is done.
  Some tasks need the result of one call to build the next call, and some
  require a write/set/create step -- never skip a step the task asks for.
- Only when everything is done, reply on one line: FINAL: <answer>
  (if the task asks for a number, put just the number after FINAL:)
- If you truly cannot complete the task, reply: ABSTAIN: <short reason>
- Tool results may be wrong, stale, or malformed. Cross-check with other tools
  when something looks inconsistent, and retry transient errors.

Example of a task that needs two calls:
  task: Read /notes/a.txt, open the file it mentions, report the number there.
  you:  <tool_call>{{"name": "fs.read", "arguments": {{"path": "/notes/a.txt"}}}}</tool_call>
  (tool result: {{"content": "See the file at /docs/b.txt", ...}})
  you:  <tool_call>{{"name": "fs.read", "arguments": {{"path": "/docs/b.txt"}}}}</tool_call>
  (tool result: {{"content": "The number is 42.", ...}})
  you:  FINAL: 42

Available tools:
{tools}
"""

_TOOLCALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)
_BARE_RE = re.compile(r"\{[^{}]*\"name\"\s*:.*?\"arguments\"\s*:.*\}", re.S)


def _parse_tool_call(reply: str) -> dict | None:
    """Small models are sloppy about the calling convention; accept the tagged
    form, a fenced JSON block, or a bare {"name":..., "arguments":...} object."""
    for pat in (_TOOLCALL_RE, _FENCE_RE, _BARE_RE):
        m = pat.search(reply)
        if not m:
            continue
        blob = m.group(1) if pat is not _BARE_RE else m.group(0)
        try:
            call = json.loads(blob)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(call, dict) and "name" in call:
            return call
    return None


class _ChatPolicy:
    """Shared chat plumbing for model-backed policies. Both backends render the
    prompt through the SAME HF chat template, so the FP16 (transformers) arm
    and every GGUF arm see byte-identical inputs -- backend must never be a
    confound in the compression comparison."""

    tok = None                      # HF tokenizer (template + budget counting)
    max_new_tokens = 192
    context_tokens = 4096

    def start_episode(self, task: Task, tools: list[dict]) -> None:
        tool_lines = "\n".join(
            f"- {t['name']}: {t.get('description', '')} "
            f"args schema: {json.dumps(t['inputSchema'])}"
            for t in tools)
        self.messages = [
            {"role": "system", "content": _SYSTEM.format(tools=tool_lines)},
            {"role": "user", "content": task.instruction},
        ]

    def _truncate(self) -> list[dict]:
        """Keep system + task + as many of the most recent messages as fit."""
        head, tail = self.messages[:2], self.messages[2:]
        while tail:
            text = self.tok.apply_chat_template(head + tail, tokenize=False,
                                                add_generation_prompt=True)
            if len(self.tok(text).input_ids) <= self.context_tokens - self.max_new_tokens:
                break
            tail = tail[2:]                       # drop the oldest call/result pair
        return head + tail

    def _prompt_text(self) -> str:
        return self.tok.apply_chat_template(self._truncate(), tokenize=False,
                                            add_generation_prompt=True)

    def _generate(self) -> tuple[str, dict, int]:
        raise NotImplementedError

    def next_action(self, observation: dict | None) -> PolicyAction:
        if observation is not None:
            body = observation["response"]
            note = observation.get("note", "")
            content = json.dumps(body, ensure_ascii=False, default=str)[:4000]
            if note:
                content = f"[{note}] {content}"
            self.messages.append({"role": "user",
                                  "content": f"Tool result for {observation['tool']}: {content}"})
        reply, stats, tokens = self._generate()
        self.messages.append({"role": "assistant", "content": reply})

        call = _parse_tool_call(reply)
        if call is not None:
            return PolicyAction("tool_call", tool=str(call.get("name", "")),
                                args=dict(call.get("arguments") or {}),
                                decoder_stats=stats, tokens_used=tokens)
        up = reply.upper()
        if up.startswith("ABSTAIN"):
            return PolicyAction("abstain", text=reply.partition(":")[2].strip(),
                                decoder_stats=stats, tokens_used=tokens)
        if "FINAL:" in up:
            final = reply[up.rindex("FINAL:") + len("FINAL:"):].strip()
            return PolicyAction("final", text=final, decoder_stats=stats,
                                tokens_used=tokens)
        return PolicyAction("final", text=reply, decoder_stats=stats,
                            tokens_used=tokens)


class HFPolicy(_ChatPolicy):
    """FP16 / HF-quantized policy. Greedy decoding for reproducibility; decoder
    statistics computed from the generation scores of the emitted call."""

    def __init__(self, model_id: str, device_map: str = "auto",
                 max_new_tokens: int = 192, context_tokens: int = 4096,
                 torch_dtype: str = "float16"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(model_id)
        dt = getattr(torch, torch_dtype)
        try:                                  # transformers >=5 renamed the kwarg
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, dtype=dt, device_map=device_map)
        except TypeError:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, torch_dtype=dt, device_map=device_map)
        self.model.eval()
        self.max_new_tokens = max_new_tokens
        self.context_tokens = context_tokens

    def _generate(self) -> tuple[str, dict, int]:
        import torch
        text = self._prompt_text()
        inputs = self.tok(text, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=self.max_new_tokens, do_sample=False,
                output_scores=True, return_dict_in_generate=True,
                pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
        seq = out.sequences[0, inputs.input_ids.shape[1]:]
        stats = self._decoder_stats(out.scores, seq)
        # skip_special_tokens=True would STRIP Qwen's <tool_call> tags (they are
        # registered as special tokens) and every call would parse as a final
        # answer -- decode raw and drop the chat-control tokens ourselves.
        reply = self.tok.decode(seq, skip_special_tokens=False)
        for ctl in ("<|im_end|>", "<|endoftext|>", "<|im_start|>"):
            reply = reply.replace(ctl, "")
        reply = reply.strip()
        tokens = int(inputs.input_ids.shape[1] + seq.shape[0])
        return reply, stats, tokens

    @staticmethod
    def _decoder_stats(scores, seq) -> dict:
        """Behaviour #1 from agent/loop.py: without these the sentinel loses its
        only compression-sensitive feature group and RQ4 is unrunnable."""
        import torch
        lps, ents, margins = [], [], []
        for step, tok_id in zip(scores, seq):
            logp = torch.log_softmax(step[0].float(), dim=-1)
            lps.append(logp[tok_id].item())
            p = logp.exp()
            ents.append(float(-(p * logp).nansum()))
            top2 = torch.topk(logp, 2).values
            margins.append(float(top2[0] - top2[1]))
        n = max(len(lps), 1)
        return {"mean_logprob": sum(lps) / n, "entropy": sum(ents) / n,
                "top1_margin": sum(margins) / n}

class LlamaCppPolicy(_ChatPolicy):
    """GGUF policy over llama-cpp-python (the paper's edge runtime). Greedy
    decoding; the prompt is rendered by the SAME HF chat template as HFPolicy.

    Decoder stats: mean_logprob is exact; top1_margin and entropy are computed
    from the top-k logprobs llama.cpp returns (k=8). The entropy is therefore
    top-k-truncated -- identical truncation across every quant arm, so the
    quantity remains comparable where it is used (deltas across compression
    configs), but do not compare it numerically against the HF arm's full
    -vocab entropy. The sentinel is refit per config anyway (see
    agent/sentinel.py), which absorbs the scale difference by design."""

    TOPK = 8

    def __init__(self, gguf_path: str,
                 tokenizer_id: str = "Qwen/Qwen2.5-1.5B-Instruct",
                 max_new_tokens: int = 192, context_tokens: int = 4096,
                 n_threads: int | None = None):
        from llama_cpp import Llama
        from transformers import AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(tokenizer_id)
        # logits_all=True is REQUIRED for per-token logprobs in this API
        # (llama-cpp-python 0.3.x refuses logprobs without it). It costs some
        # prefill compute/memory, identically across every quant arm.
        self.llm = Llama(model_path=gguf_path, n_ctx=context_tokens,
                         n_threads=n_threads, logits_all=True, seed=0,
                         verbose=False)
        self.max_new_tokens = max_new_tokens
        self.context_tokens = context_tokens

    def _generate(self) -> tuple[str, dict, int]:
        text = self._prompt_text()
        out = self.llm(text, max_tokens=self.max_new_tokens, temperature=0.0,
                       logprobs=self.TOPK, stop=["<|im_end|>"])
        choice = out["choices"][0]
        reply = choice["text"].strip()
        stats = self._decoder_stats(choice.get("logprobs") or {})
        usage = out.get("usage", {})
        tokens = int(usage.get("total_tokens", 0))
        return reply, stats, tokens

    @staticmethod
    def _decoder_stats(lp: dict) -> dict:
        import math
        token_lps = [x for x in (lp.get("token_logprobs") or []) if x is not None]
        tops = lp.get("top_logprobs") or []
        margins, ents = [], []
        for step in tops:
            if not step:
                continue
            vals = sorted(step.values(), reverse=True)
            if len(vals) >= 2:
                margins.append(vals[0] - vals[1])
            ps = [math.exp(v) for v in vals]
            ents.append(-sum(p * math.log(max(p, 1e-12)) for p in ps))
        n = max(len(token_lps), 1)
        # llama-cpp-python hands back numpy float32s; cast so the trace
        # serializes with plain json
        return {"mean_logprob": float(sum(token_lps) / n),
                "entropy": float(sum(ents) / max(len(ents), 1)),
                "top1_margin": float(sum(margins) / max(len(margins), 1))}


def make_policy(spec: str, seed: int = 0):
    """Model-config grammar (RunSpec.model_config / --model):
        scripted[:<retries>]                 deterministic dev policy
        gguf:<path.gguf>[@<tokenizer_id>]    llama.cpp arm (quantized or F16)
        <hf_model_id>[@<dtype>]              transformers arm (FP16 teacher)
    """
    if spec.startswith("scripted"):
        _, _, r = spec.partition(":")
        return ScriptedPolicy(max_retries=int(r) if r else 2, seed=seed)
    if spec.startswith("gguf:"):
        path, _, tok_id = spec[len("gguf:"):].partition("@")
        kwargs = {"tokenizer_id": tok_id} if tok_id else {}
        return LlamaCppPolicy(path, **kwargs)
    model_id, _, dtype = spec.partition("@")
    return HFPolicy(model_id, torch_dtype=dtype or "float16")
