"""Structured pruning + LoRA healing (10 / 25 / 40 percent).

Report BOTH pruned-only and pruned+healed. The healing data is the second place
where the failure-aware idea applies: heal on recovery trajectories, not on
generic text, and report it as an arm.
"""
def prune_structured(model_id: str, ratio: float, method: str = "llm_pruner"): ...
def heal_lora(model_dir: str, data: str, steps: int = 2000): ...
