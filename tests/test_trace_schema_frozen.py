"""The trace schema is FROZEN as of W1 (2026-09-05, HANDOFF §2/§4): four
downstream consumers read it (sentinel training, PTQ calibration, LoRA SFT,
the eval harness). If you need a new field, add it to the END and bump
SCHEMA_VERSION -- renaming or removing anything here breaks replay of every
trace generated so far, which is why this test exists."""
from mcpguardlite.data.trajectory import SCHEMA_VERSION, Trajectory, Turn

FROZEN_TURN_FIELDS = [
    "turn", "tool", "args", "request_json", "response_json", "latency_ms",
    "decoder_stats", "features", "fault_present", "fault_family", "oracle_op",
    "sentinel_p_fault", "chosen_op", "recovery_outcome",
]

FROZEN_TRAJECTORY_FIELDS = [
    "episode_id", "env", "task_id", "tier", "model_config", "fault_config",
    "seed", "turns", "success", "asserted_success", "split",
]


def test_schema_version_pinned():
    assert SCHEMA_VERSION == "faulttrace-v1"


def test_turn_fields_frozen():
    assert list(Turn.__dataclass_fields__) == FROZEN_TURN_FIELDS


def test_trajectory_fields_frozen():
    assert list(Trajectory.__dataclass_fields__) == FROZEN_TRAJECTORY_FIELDS
