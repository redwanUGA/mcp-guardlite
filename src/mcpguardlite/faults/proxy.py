"""Transparent MCP middlebox.

The agent connects here instead of the real server. We forward JSON-RPC both
ways and apply the scheduled fault process on the response path.

Boundary choice matters: AgentChaos injects at the agent<->LLM API boundary.
We inject at the agent<->TOOL boundary, because on the edge the LLM is local and
the tools are the unreliable part. Do not move this.

Latency faults are SHAPED, not slept: T2 adds its sampled delay_ms and R2
multiplies by slowdown_x on the *reported* latency_ms. The sentinel's latency_z
sees exactly what a slow server would produce, while a 3,000-episode run stays
tractable on the cluster. Real wall-clock throttling belongs to the emulated
edge profiles (eval/edge_profile.py), not to the fault process.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .injector import (FaultConfig, FaultScheduler, RESULT_FAMILIES,
                       apply_fault, drift_rename)
from ..envs.servers import ToolError


@dataclass
class ProxyStats:
    calls: int = 0
    faults_fired: int = 0
    faults_configured: int = 0


class FaultProxy:
    """`registry` maps env name -> live in-process server instance. The proxy
    stays transport-shaped (async, JSON-RPC envelopes) so swapping in a real
    network MCP client later cannot change any observable behaviour."""

    def __init__(self, registry: dict, cfg: FaultConfig, trace_writer=None):
        self.registry = registry
        self.sched = FaultScheduler(cfg)
        self.trace = trace_writer
        self.stats = ProxyStats()
        self._drift: dict[str, tuple[str, str]] = {}   # tool -> (old, new) P3 rename

    async def call_tool(self, episode_id: str, turn: int, tool: str,
                        args: dict) -> tuple[dict, float, dict | None]:
        """Returns (response, latency_ms, fault_event_json | None)."""
        t0 = time.perf_counter()
        event = self.sched.decide(episode_id, turn, tool)
        self.stats.calls += 1

        # P3 aftermath: once a tool's schema has drifted, a caller that uses the
        # NEW parameter name has adapted -- translate back and forward cleanly.
        fwd_args = dict(args or {})
        if tool in self._drift:
            old, new = self._drift[tool]
            if new in fwd_args:
                fwd_args[old] = fwd_args.pop(new)
                if event is not None and event.family == "P3":
                    event = None

        nominal = await self._forward(tool, fwd_args, turn)

        # A result-corrupting fault has nothing to bite on a legitimate error
        # response; drop the event rather than log a fired fault with no effect.
        if (event is not None and event.family in RESULT_FAMILIES
                and "result" not in nominal):
            event = None

        if event is None:
            latency = (time.perf_counter() - t0) * 1e3
            self._log(episode_id, turn, tool, args, nominal, latency, None)
            return nominal, latency, None

        self.stats.faults_fired += 1
        if event.family == "P3" and tool not in self._drift:
            server = self.registry.get(tool.split(".", 1)[0])
            rename = drift_rename(server, tool)
            if rename:
                self._drift[tool] = rename

        try:
            faulted = apply_fault(nominal, event, ctx={
                "args": fwd_args, "tool": tool,
                "env": tool.split(".", 1)[0],
                "server": self.registry.get(tool.split(".", 1)[0]),
            })
        except (TimeoutError, ConnectionError) as exc:
            faulted = {"__transport_error__": type(exc).__name__, "message": str(exc)}

        latency = (time.perf_counter() - t0) * 1e3
        if event.family == "T2":
            latency += float(event.params.get("delay_ms", 0.0))
        elif event.family == "R2":
            latency *= float(event.params.get("slowdown_x", 1.0))
        self._log(episode_id, turn, tool, args, faulted, latency, event.to_json())
        return faulted, latency, event.to_json()

    async def _forward(self, tool: str, args: dict, turn: int = 0) -> dict:
        env = tool.split(".", 1)[0]
        server = self.registry.get(env)
        if server is None:
            return {"jsonrpc": "2.0", "id": turn,
                    "error": {"code": -32601, "message": f"unknown server: {env}"}}
        try:
            result = server.call_tool(tool, args)
        except ToolError as e:
            return {"jsonrpc": "2.0", "id": turn,
                    "error": {"code": e.code, "message": e.message}}
        return {"jsonrpc": "2.0", "id": turn, "result": result}

    def list_tools(self, env: str) -> list[dict]:
        """tools/list with any latched P3 drift applied -- the agent can
        rediscover the renamed parameter here (that is the intended recovery)."""
        tools = self.registry[env].list_tools()
        for t in tools:
            drift = self._drift.get(t["name"])
            if drift:
                old, new = drift
                schema = t["inputSchema"]
                props = dict(schema.get("properties", {}))
                if old in props:
                    props[new] = props.pop(old)
                required = [new if r == old else r for r in schema.get("required", [])]
                t["inputSchema"] = {**schema, "properties": props, "required": required}
        return tools

    def reset_episode(self, episode_id: str) -> None:
        self.sched.reset_episode(episode_id)
        self._drift.clear()

    def _log(self, episode_id, turn, tool, args, response, latency, event):
        if self.trace is None:
            return
        self.trace.write({
            "episode_id": episode_id, "turn": turn, "tool": tool,
            "args": args, "response_preview": str(response)[:2000],
            "latency_ms": latency, "fault": event,
        })
