"""Agent loop: monitor -> detect -> diagnose -> recover -> verify.

Baselines share this loop; they differ only in which components are enabled,
which keeps the comparison clean.

    naive        sentinel=None, controller=None
    retry_only   sentinel=rule_baseline, operator_set="retry_only"
    reflect      sentinel=None, prompt-based reflection turn on error
    full_replan  sentinel=rule_baseline, operator_set="replan_only"
    guardlite    sentinel=Sentinel(), operator_set="full"
    oracle       sentinel="oracle" (reads the fault event)   <- upper bound

The five required behaviours (and where they live):
  1. decoder stats captured for the emitted call on EVERY turn -> Policy
     provides them; the loop refuses to run a policy that does not.
  2. every observation flows extractor -> sentinel BEFORE the policy sees it.
  3. detections route through the RecoveryController, never inline in the
     prompt (invariant I5). The only text that ever reaches the policy is a
     recovery *instruction* note, after the decision was made outside it.
  4. `asserted_success` (agent's claim) recorded separately from verifier
     `success` (invariant I3); the gap is SFR.
  5. one JSONL trace per episode with everything needed for replay -- the loop
     returns the Turn records; the harness owns file I/O.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict

from .policy import response_is_error
from .recovery import OPERATORS, RecoveryController, OperatorResult
from .sentinel import FeatureExtractor, SentinelPrediction
from ..data.trajectory import Turn
from ..faults.taxonomy import RecoveryOp


@dataclass
class LoopConfig:
    max_turns: int = 12
    context_tokens: int = 4096
    sentinel_threshold: float = 0.5
    operator_set: str = "full"
    enable_verify_on_terminal: bool = True   # last-chance check before asserting
    reflect_on_error: bool = False           # the `reflect` baseline


@dataclass
class EpisodeResult:
    episode_id: str
    success: bool
    asserted_success: bool
    turns: int
    recovery_actions: int
    tokens: int
    wall_s: float
    joules: float | None
    fault_events: list = field(default_factory=list)
    trace_path: str | None = None
    answer: str = ""
    turn_records: list = field(default_factory=list)   # data.trajectory.Turn dicts


class _OpCtx:
    """Concrete OperatorCtx (agent/recovery.py protocol)."""

    def __init__(self, tool, args, history, tools_available, policy):
        self.tool = tool
        self.args = args
        self.history = history
        self.tools_available = tools_available
        self.policy = policy


class AgentLoop:
    def __init__(self, policy, proxy, sentinel=None, controller=None,
                 extractor=None, cfg: LoopConfig | None = None):
        self.policy = policy
        self.proxy = proxy
        self.sentinel = sentinel          # None | callable(f)->pred | Sentinel | "oracle"
        self.controller = controller      # RecoveryController | None
        self.extractor = extractor
        self.cfg = cfg or LoopConfig()

    # ------------------------------------------------------------------ run
    async def run(self, task, episode_id: str, tools: list[dict] | None = None) -> EpisodeResult:
        cfg = self.cfg
        env = task.env
        tools = tools if tools is not None else self.proxy.list_tools(env)
        extractor = self.extractor or FeatureExtractor(
            schema_lookup=lambda tool: self.proxy.registry[env].output_schema(tool))
        policy = self.policy
        controller = self.controller
        if controller is not None:
            controller.reset()

        policy.start_episode(task, tools)
        t0 = time.perf_counter()
        call_idx = 0                       # proxy-call sequence; PRF turn key
        obs = None
        history: list[dict] = []
        turn_records: list[dict] = []
        fault_events: list[dict] = []
        recovery_actions = 0
        tokens = 0
        retries = 0
        asserted = False
        answer = ""
        dec_sum = {"mean_logprob": 0.0, "entropy": 0.0}
        dec_n = 0

        for _policy_turn in range(cfg.max_turns):
            action = policy.next_action(obs)
            tokens += action.tokens_used
            if action.decoder_stats is None:
                raise RuntimeError("policy emitted no decoder stats; the "
                                   "sentinel ablation (RQ4) would be unrunnable")

            if action.kind in ("final", "abstain"):
                asserted = action.kind == "final"
                answer = action.text
                break

            # ---- call through the fault proxy ---------------------------
            orig_call_idx = call_idx
            response, latency, event = await self.proxy.call_tool(
                episode_id, call_idx, action.tool, action.args)
            call_idx += 1
            if event:
                fault_events.append(event)

            # ---- behaviour #2: extractor -> sentinel BEFORE the policy --
            frac_budget = (controller.state.frac_used(controller.budget)
                           if controller else 0.0)
            episode_state = {
                "turn": call_idx - 1, "retries": retries,
                "frac_budget_used": frac_budget,
                "decoder_baseline": ({k: v / dec_n for k, v in dec_sum.items()}
                                     if dec_n else {}),
            }
            feats = extractor.extract(
                tool=action.tool,
                request={"tool": action.tool, "args": action.args},
                response=response, latency_ms=latency,
                decoder_stats=action.decoder_stats, episode_state=episode_state)
            dec_sum["mean_logprob"] += action.decoder_stats.get("mean_logprob", 0.0)
            dec_sum["entropy"] += action.decoder_stats.get("entropy", 0.0)
            dec_n += 1

            pred = self._predict(feats, event)
            chosen_op = None
            outcome = "n/a"
            note = ""

            # ---- behaviour #3: detections route through the controller --
            if (pred is not None and pred.p_fault >= cfg.sentinel_threshold
                    and controller is not None):
                op = pred.op if pred.op is not RecoveryOp.NOOP else RecoveryOp.RETRY
                response, latency, call_idx, n_acts, note = await self._recover(
                    op, action, response, latency, episode_id, call_idx,
                    history, tools, fault_events)
                recovery_actions += n_acts
                retries += n_acts
                chosen_op = op.value
                outcome = ("resolved" if not response_is_error(response)
                           else "unresolved")

            turn_records.append(asdict(Turn(
                turn=len(turn_records), tool=action.tool, args=action.args,
                request_json={"jsonrpc": "2.0", "id": orig_call_idx,
                              "method": "tools/call",
                              "params": {"name": action.tool,
                                         "arguments": action.args}},
                response_json=response, latency_ms=latency,
                decoder_stats=action.decoder_stats, features=asdict(feats),
                fault_present=event is not None,
                fault_family=event["family"] if event else None,
                oracle_op=event["oracle_op"] if event else None,
                sentinel_p_fault=pred.p_fault if pred else None,
                chosen_op=chosen_op, recovery_outcome=outcome)))

            obs = {"tool": action.tool, "args": action.args,
                   "response": response, "latency_ms": latency}
            if note:
                obs["note"] = note
            elif cfg.reflect_on_error and response_is_error(response):
                # `reflect` baseline: a prompt-side nudge and nothing else
                obs["note"] = ("the previous tool call failed; think about why "
                               "and adjust your next step")
            history.append(obs)

        return EpisodeResult(
            episode_id=episode_id,
            success=False,                    # verifier's verdict; harness fills it
            asserted_success=asserted,        # behaviour #4: the agent's CLAIM
            turns=len(turn_records),
            recovery_actions=recovery_actions,
            tokens=tokens,
            wall_s=time.perf_counter() - t0,
            joules=None,
            fault_events=fault_events,
            answer=answer,
            turn_records=turn_records)

    # ------------------------------------------------------------- sentinel
    def _predict(self, feats, event) -> SentinelPrediction | None:
        s = self.sentinel
        if s is None:
            return None
        if s == "oracle":
            if event is None:
                return SentinelPrediction(0.0, None, RecoveryOp.NOOP)
            return SentinelPrediction(1.0, event["family"],
                                      RecoveryOp(event["oracle_op"]))
        if callable(s) and not hasattr(s, "predict"):
            return s(feats)
        return s.predict(feats)

    # ------------------------------------------------------------- recovery
    async def _recover(self, op: RecoveryOp, action, response, latency,
                       episode_id, call_idx, history, tools, fault_events):
        """Execute ONE typed operator under budget. Returns the (possibly
        repaired) response plus the advanced call index."""
        controller = self.controller
        ctx = _OpCtx(action.tool, action.args,
                     history + [{"tool": action.tool, "args": action.args,
                                 "response": response}],
                     tools, self.policy)
        result: OperatorResult = controller.step(ctx, op)
        n_acts = 1
        note = ""

        if result.action == "stop":
            return response, latency, call_idx, n_acts, "budget exhausted; abstain"
        if result.action == "replan":
            return response, latency, call_idx, n_acts, result.note

        if result.action in ("recall", "call_other"):
            new_resp, new_lat, ev = await self.proxy.call_tool(
                episode_id, call_idx, result.tool, result.args)
            call_idx += 1
            if ev:
                fault_events.append(ev)
            if result.note == "verify":
                note = self._reconcile(action.tool, response, result.tool, new_resp)
                # prefer the corroborating source when the two disagree -- but
                # only in the original tool's result shape (adapter), else keep
                # the original payload and let the note carry the suspicion
                if note:
                    adapted = self._adapt_verify(action.tool, new_resp)
                    if adapted is not None:
                        response, latency = adapted, new_lat
            elif result.note == "substitute":
                adapted = self._adapt_substitute(action.tool, new_resp)
                if adapted is not None:
                    response, latency = adapted, new_lat
            else:
                response, latency = new_resp, new_lat
        return response, latency, call_idx, n_acts, note

    @staticmethod
    def _reconcile(tool, orig, alt_tool, alt) -> str:
        """Compare original vs corroborating result; '' means consistent."""
        if response_is_error(alt):
            return ""
        a = orig.get("result", {}) if isinstance(orig, dict) else {}
        b = alt.get("result", {}) if isinstance(alt, dict) else {}
        va, vb = a.get("value"), b.get("value")
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            scale = max(abs(va), abs(vb), 1e-9)
            if abs(va - vb) / scale > 0.01:
                return f"cross-check disagreed ({va} vs {vb}); using corroborated value"
            return ""
        if a and b and a != b:
            return "cross-check disagreed; using corroborated result"
        return ""

    @staticmethod
    def _adapt_substitute(tool, response):
        from .recovery import SUBSTITUTES
        sub = SUBSTITUTES.get(tool)
        if sub is None or sub[2] is None or response_is_error(response):
            return None
        adapted = sub[2](response.get("result", {}))
        if adapted is None:
            return None
        return {**response, "result": adapted}

    @staticmethod
    def _adapt_verify(tool, response):
        from .recovery import VERIFY_ALT
        alt = VERIFY_ALT.get(tool)
        if alt is None or alt[2] is None or response_is_error(response):
            return None
        adapted = alt[2](response.get("result", {}))
        if adapted is None:
            return None
        return {**response, "result": adapted}
