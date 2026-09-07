"""MCP-FaultTrace record schema. Freeze this early -- everything downstream
(sentinel training, PTQ calibration, LoRA SFT, the eval harness) reads it."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json


@dataclass
class Turn:
    turn: int
    tool: str
    args: dict
    request_json: dict
    response_json: dict
    latency_ms: float
    decoder_stats: dict                 # mean_logprob, entropy, top1_margin
    features: dict                      # TurnFeatures as a flat dict
    fault_present: bool
    fault_family: str | None
    oracle_op: str | None
    sentinel_p_fault: float | None
    chosen_op: str | None
    recovery_outcome: str | None        # "resolved" | "unresolved" | "n/a"


@dataclass
class Trajectory:
    episode_id: str
    env: str
    task_id: str
    tier: str                           # single | sequential | dependent | verify
    model_config: str
    fault_config: str
    seed: int
    turns: list = field(default_factory=list)
    success: bool = False
    asserted_success: bool = False
    split: str = "iid_train"

    def to_jsonl(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

SCHEMA_VERSION = "faulttrace-v1"
