"""Failure sentinel.

Design intent (this is the paper's core architectural claim, so keep it):
the sentinel must stay OUTSIDE the quantized policy model. Three feature groups,
only one of which is affected by compression:

  protocol   -- JSON-RPC status, schema validity, size/latency anomalies  [invariant]
  semantic   -- intent<->result embedding similarity, cardinality, units  [invariant]
  decoder    -- logprob / entropy / margin of the policy model's own call [compression-sensitive]

If you find yourself moving sentinel logic into the prompt, stop: that reintroduces
the dependence on model capacity the paper is arguing against.

Budget targets: < 5 MB on disk, < 3 ms per turn on a Pi 5 CPU core.
"""

from __future__ import annotations

import json
import math
import pickle
import re
import statistics
from dataclasses import dataclass, asdict, field

import numpy as np

from ..faults.taxonomy import TAXONOMY, RecoveryOp


# --------------------------------------------------------------------------- #
# features
# --------------------------------------------------------------------------- #

@dataclass
class TurnFeatures:
    # -- protocol (compression-invariant) ---------------------------------
    is_jsonrpc_error: float = 0.0
    error_code: float = 0.0
    parse_failed: float = 0.0
    schema_valid: float = 1.0
    missing_required_fields: float = 0.0
    payload_bytes_log: float = 0.0
    payload_size_ratio: float = 1.0      # vs rolling median for this tool
    latency_z: float = 0.0               # vs rolling baseline for this tool
    retries_so_far: float = 0.0
    tool_in_last_list: float = 1.0

    # -- semantic (compression-invariant) ---------------------------------
    intent_result_cosine: float = 0.0
    result_cardinality: float = 0.0
    cardinality_ratio: float = 1.0       # vs expectation
    unit_check_failed: float = 0.0
    cross_tool_disagreement: float = 0.0
    value_delta_z: float = 0.0           # vs previously observed value (staleness)

    # -- decoder confidence (compression-SENSITIVE) -----------------------
    mean_logprob: float = 0.0
    entropy: float = 0.0
    top1_margin: float = 0.0
    mean_logprob_delta: float = 0.0      # vs episode running mean
    entropy_delta: float = 0.0

    # -- episode context ---------------------------------------------------
    turn_index: float = 0.0
    frac_budget_used: float = 0.0

    def vector(self) -> np.ndarray:
        return np.array(list(asdict(self).values()), dtype=np.float32)

    @staticmethod
    def names() -> list[str]:
        return list(TurnFeatures().__dataclass_fields__.keys())

    @staticmethod
    def group(name: str) -> str:
        protocol = {"is_jsonrpc_error", "error_code", "parse_failed", "schema_valid",
                    "missing_required_fields", "payload_bytes_log",
                    "payload_size_ratio", "latency_z", "retries_so_far",
                    "tool_in_last_list"}
        decoder = {"mean_logprob", "entropy", "top1_margin",
                   "mean_logprob_delta", "entropy_delta"}
        if name in protocol:
            return "protocol"
        if name in decoder:
            return "decoder"
        if name in {"turn_index", "frac_budget_used"}:
            return "context"
        return "semantic"


class FeatureExtractor:
    """Maintains per-tool rolling baselines so anomalies are relative, not absolute."""

    def __init__(self, embedder=None, window: int = 32, schema_lookup=None):
        self.embedder = embedder            # ~20-30M param sentence encoder, optional
        self.window = window
        self.schema_lookup = schema_lookup  # tool -> outputSchema (from the proxy)
        self._latency: dict[str, list[float]] = {}
        self._size: dict[str, list[float]] = {}
        self._values: dict[str, list[float]] = {}

    def extract(self, *, tool: str, request: dict, response: dict,
                latency_ms: float, decoder_stats: dict | None,
                episode_state: dict) -> TurnFeatures:
        f = TurnFeatures()

        # ---- protocol ----------------------------------------------------
        raw = response.get("__raw_bytes__")
        f.parse_failed = 1.0 if raw is not None else 0.0
        err = response.get("error") if isinstance(response, dict) else None
        f.is_jsonrpc_error = 1.0 if err else 0.0
        f.error_code = float(err.get("code", 0)) if err else 0.0
        f.schema_valid = float(self._schema_ok(tool, response))
        f.payload_bytes_log = math.log1p(len(str(response)))
        f.payload_size_ratio = self._ratio(self._size, tool, len(str(response)))
        f.latency_z = self._zscore(self._latency, tool, latency_ms)
        f.retries_so_far = float(episode_state.get("retries", 0))

        # ---- semantic ----------------------------------------------------
        f.intent_result_cosine = self._cosine(request, response)
        result = response.get("result") if isinstance(response, dict) else None
        if isinstance(result, dict):
            for key in ("entries", "matches", "keys", "events", "slots",
                        "readings", "links"):
                if isinstance(result.get(key), list):
                    f.result_cardinality = float(len(result[key]))
                    break
            val = result.get("value")
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                f.value_delta_z = self._zscore(self._values, tool, float(val))
                self._push(self._values, tool, float(val))

        # ---- decoder confidence -----------------------------------------
        if decoder_stats:
            f.mean_logprob = float(decoder_stats.get("mean_logprob", 0.0))
            f.entropy = float(decoder_stats.get("entropy", 0.0))
            f.top1_margin = float(decoder_stats.get("top1_margin", 0.0))
            base = episode_state.get("decoder_baseline", {})
            f.mean_logprob_delta = f.mean_logprob - base.get("mean_logprob", f.mean_logprob)
            f.entropy_delta = f.entropy - base.get("entropy", f.entropy)

        f.turn_index = float(episode_state.get("turn", 0))
        f.frac_budget_used = float(episode_state.get("frac_budget_used", 0.0))
        self._push(self._latency, tool, latency_ms)
        self._push(self._size, tool, float(len(str(response))))
        return f

    # ------------------------------------------------------------ helpers
    def _push(self, store, key, val):
        store.setdefault(key, []).append(val)
        if len(store[key]) > self.window:
            store[key].pop(0)

    def _zscore(self, store, key, val) -> float:
        hist = store.get(key, [])
        if len(hist) < 4:
            return 0.0
        sd = statistics.pstdev(hist) or 1e-6
        return (val - statistics.fmean(hist)) / sd

    def _ratio(self, store, key, val) -> float:
        hist = store.get(key, [])
        if not hist:
            return 1.0
        med = statistics.median(hist) or 1.0
        return val / med

    def _schema_ok(self, tool: str, response: dict) -> bool:
        """Validate the RESULT object against the advertised outputSchema.
        Unparseable / transport-failed payloads are schema-invalid by fiat;
        an error envelope carries no result to validate (its errorness is
        already a separate feature)."""
        if not isinstance(response, dict) or "__raw_bytes__" in response \
                or "__transport_error__" in response:
            return False
        if "result" not in response:
            return True
        schema = self.schema_lookup(tool) if self.schema_lookup else None
        if not schema:
            return True
        try:
            import jsonschema
            jsonschema.validate(response["result"], schema)
            return True
        except jsonschema.ValidationError:
            return False

    def _cosine(self, request, response) -> float:
        """intent<->result similarity. With an embedder: true cosine. Without
        one (laptop/Pi floor): token Jaccard -- crude, but monotone in overlap
        and dependency-free."""
        a = json.dumps(request, default=str)
        b = json.dumps(response, default=str)
        if self.embedder is not None:
            va, vb = self.embedder.encode([a, b])
            denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1e-9
            return float(np.dot(va, vb) / denom)
        ta = set(re.findall(r"[a-z0-9_]+", a.lower()))
        tb = set(re.findall(r"[a-z0-9_]+", b.lower()))
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)


# --------------------------------------------------------------------------- #
# classifier
# --------------------------------------------------------------------------- #

@dataclass
class SentinelPrediction:
    p_fault: float
    family: str | None
    op: RecoveryOp
    p_family: dict[str, float] = field(default_factory=dict)


class Sentinel:
    """Gradient-boosted-tree head by default; MLP variant for comparison.

    IMPORTANT: refit per compression configuration by default. The decoder
    features shift under quantization, and the paper reports the no-refit case
    as an ablation, not as the system.
    """

    def __init__(self, backend: str = "gbt", threshold: float = 0.5):
        self.backend = backend
        self.threshold = threshold
        self.model = None
        self.families: list[str] = list(TAXONOMY.keys())

    def fit(self, X: np.ndarray, y_fault: np.ndarray, y_family: np.ndarray) -> None:
        """One multiclass head over ["none"] + families: p_fault = 1 - P(none),
        family = argmax over the rest. LightGBM when available (the paper's
        default: <5 MB, <3 ms on a Pi core), sklearn GBT as the fallback so the
        harness never hard-depends on it.

        NB: tune `threshold` on val to a target FPR before the full run --
        ROR is a reported metric and a trigger-happy sentinel loses on energy
        even if it wins on RSR (that tuning lives in the training script, W3)."""
        classes = ["none"] + [f for f in self.families]
        y = np.array([0 if not yf else classes.index(fam)
                      for yf, fam in zip(y_fault, y_family)])
        try:
            import lightgbm as lgb
            self.model = lgb.LGBMClassifier(
                n_estimators=200, num_leaves=31, learning_rate=0.08,
                min_child_samples=10, deterministic=True, random_state=0,
                verbose=-1)
        except ImportError:
            from sklearn.ensemble import HistGradientBoostingClassifier
            self.model = HistGradientBoostingClassifier(random_state=0)
        self.model.fit(X, y)
        self._classes = classes

    def predict(self, f: TurnFeatures) -> SentinelPrediction:
        if self.model is None:
            raise RuntimeError("Sentinel not fitted/loaded")
        proba = self.model.predict_proba(f.vector().reshape(1, -1))[0]
        present = list(self.model.classes_)
        p_by_name = {self._classes[c]: float(proba[i])
                     for i, c in enumerate(present)}
        p_fault = 1.0 - p_by_name.get("none", 0.0)
        fam_probs = {k: v for k, v in p_by_name.items() if k != "none"}
        family = max(fam_probs, key=fam_probs.get) if fam_probs else None
        op = TAXONOMY[family].oracle_op if family else RecoveryOp.NOOP
        if p_fault < self.threshold:
            return SentinelPrediction(p_fault, None, RecoveryOp.NOOP, fam_probs)
        return SentinelPrediction(p_fault, family, op, fam_probs)

    def save(self, path: str) -> None:
        with open(path, "wb") as fh:
            pickle.dump({"backend": self.backend, "threshold": self.threshold,
                         "model": self.model, "classes": self._classes,
                         "families": self.families}, fh)

    @classmethod
    def load(cls, path: str) -> "Sentinel":
        with open(path, "rb") as fh:
            blob = pickle.load(fh)
        s = cls(backend=blob["backend"], threshold=blob["threshold"])
        s.model = blob["model"]
        s._classes = blob["classes"]
        s.families = blob["families"]
        return s


def rule_baseline(f: TurnFeatures) -> SentinelPrediction:
    """Protocol-only rule detector. This is the honest floor to beat:
    if the learned sentinel does not beat this on overt faults, the only real
    contribution is on the silent (S*) families -- which is fine, but say so."""
    if f.parse_failed or f.is_jsonrpc_error or not f.schema_valid:
        return SentinelPrediction(1.0, None, RecoveryOp.RETRY)
    if f.latency_z > 3.0:
        return SentinelPrediction(0.7, "T2", RecoveryOp.RETRY_BACKOFF)
    return SentinelPrediction(0.0, None, RecoveryOp.NOOP)
