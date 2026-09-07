"""Emulated edge profiles + on-device measurement.

    E1  2 threads / 2 GB / 2k ctx
    E2  4 threads / 4 GB / 4k ctx      ~ Raspberry Pi 5 4GB
    E3  4 threads / 8 GB / 8k ctx      ~ Raspberry Pi 5 8GB

Emulation is cgroups v2 + taskset + llama.cpp -t/-c flags. The paper reports the
EMULATION ERROR against the real Pi (Table VII, last row) rather than pretending
emulation is ground truth -- that row is what makes the emulated results
citable, so do not drop it.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class EdgeProfile:
    name: str
    threads: int
    mem_bytes: int
    ctx_tokens: int


PROFILES = {
    "E1": EdgeProfile("E1", 2, 2 * 1024**3, 2048),
    "E2": EdgeProfile("E2", 4, 4 * 1024**3, 4096),
    "E3": EdgeProfile("E3", 4, 8 * 1024**3, 8192),
}


def apply_profile(p: EdgeProfile) -> None:
    """cgroup memory.max + cpuset; raise if not root / cgroups unavailable
    rather than silently running unconstrained (silent non-application would
    invalidate every emulated number)."""
    raise NotImplementedError


def measure(cmd: list[str], power_meter: str | None = None) -> dict:
    """Return {tok_s, ttft_ms, peak_rss_mb, joules}. On the Pi, `power_meter`
    is a serial USB-C meter sampled at >=10 Hz; on hosts without one, joules
    is None and E_task is reported as tokens instead."""
    raise NotImplementedError
