"""LoRA/QLoRA adaptation on recovery trajectories (the in-weights upper bound).

Order matters and is a reviewer question: adapt -> merge -> quantize.
Report the alternative order (quantize -> adapt) as a secondary arm, since
QLoRA-on-quantized is what a practitioner would actually do on a laptop.
"""
def train_recovery_lora(base: str, data: str, r: int = 16, alpha: int = 32): ...
def merge_and_quantize(base: str, adapter: str, quant: str = "Q4_K_M"): ...
