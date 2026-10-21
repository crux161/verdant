"""Analyze a RADARTR1 trace into interface-level facts.

Produces, per (service, command), the observed command surface: raw payload
sizes, buffer-descriptor patterns, handle-count patterns, result codes, and
request->response latency. When opt-in payloads are present, infers a byte
stability map (which offsets are constant vs varying across observations) as a
first-order layout hint.

All output is at the observed-boundary (wire) level — functional facts, never
reconstructed internals. See docs/research-tooling.md.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .traceformat import (
    BUFFER_TYPE_NAMES, CMIF_TYPE_NAMES, PHASE_REQUEST, PHASE_RESPONSE,
    TraceEvent,
)


def _result_str(result: int) -> str:
    """Render a packed Horizon result as (module, description)."""
    if result == 0:
        return "Success(0)"
    module = result & 0x1FF
    desc = (result >> 9) & 0x1FFF
    return f"{module}-{desc}"


def _buffer_signature(ev: TraceEvent) -> str:
    if not ev.buffers:
        return "-"
    return ",".join(BUFFER_TYPE_NAMES.get(b.type, f"?{b.type}") for b in ev.buffers)


@dataclass
class LayoutRun:
    start: int
    length: int
    kind: str          # "const" | "var"


@dataclass
class CommandStats:
    service: str
    command_id: int
    cmif_type: int
    request_count: int = 0
    response_count: int = 0
    is_domain: bool = False
    is_tipc: bool = False
    req_raw_sizes: Counter = field(default_factory=Counter)
    resp_raw_sizes: Counter = field(default_factory=Counter)
    req_buffer_sigs: Counter = field(default_factory=Counter)
    resp_buffer_sigs: Counter = field(default_factory=Counter)
    copy_handle_counts: Counter = field(default_factory=Counter)
    move_handle_counts: Counter = field(default_factory=Counter)
    results: Counter = field(default_factory=Counter)
    latencies: list = field(default_factory=list)
    req_payload_layout: list = field(default_factory=list)     # list[LayoutRun]
    resp_payload_layout: list = field(default_factory=list)

    @property
    def cmif_type_name(self) -> str:
        return CMIF_TYPE_NAMES.get(self.cmif_type, f"?{self.cmif_type}")

    @property
    def latency_stats(self) -> dict | None:
        if not self.latencies:
            return None
        s = sorted(self.latencies)
        n = len(s)
        return {
            "count": n,
            "min": s[0],
            "max": s[-1],
            "median": s[n // 2],
            "mean": sum(s) / n,
        }


def _stability_runs(payloads: list[bytes]) -> list[LayoutRun]:
    """Byte stability map over equal-length payloads, compressed into runs."""
    lengths = {len(p) for p in payloads}
    if len(payloads) < 2 or len(lengths) != 1:
        return []                      # need >=2 samples of one length
    n = lengths.pop()
    const = bytearray(1 for _ in range(n))
    first = payloads[0]
    for p in payloads[1:]:
        for i in range(n):
            if const[i] and p[i] != first[i]:
                const[i] = 0
    runs: list[LayoutRun] = []
    i = 0
    while i < n:
        kind = "const" if const[i] else "var"
        j = i
        while j < n and ("const" if const[j] else "var") == kind:
            j += 1
        runs.append(LayoutRun(start=i, length=j - i, kind=kind))
        i = j
    return runs


@dataclass
class Analysis:
    event_count: int
    services: list                      # sorted service names
    commands: dict                      # (service, command_id, cmif_type) -> CommandStats
    unpaired_requests: int
    unpaired_responses: int

    def command_list(self) -> list[CommandStats]:
        return [self.commands[k] for k in sorted(self.commands)]


def analyze(events: list[TraceEvent]) -> Analysis:
    commands: dict[tuple, CommandStats] = {}
    # pair request/response by correlation_id for latency
    req_by_corr: dict[int, TraceEvent] = {}
    paired_resp = 0
    req_payloads: dict[tuple, list[bytes]] = defaultdict(list)
    resp_payloads: dict[tuple, list[bytes]] = defaultdict(list)

    # First pass: map correlation_id -> request command key, for responses that
    # don't carry a command_id of their own.
    corr_to_key: dict[int, tuple] = {}
    for ev in events:
        if ev.is_request:
            corr_to_key[ev.correlation_id] = (ev.service, ev.command_id, ev.cmif_type)

    def key_for(ev: TraceEvent) -> tuple:
        if ev.is_request:
            return (ev.service, ev.command_id, ev.cmif_type)
        return corr_to_key.get(ev.correlation_id,
                               (ev.service, ev.command_id, ev.cmif_type))

    services = set()
    for ev in events:
        services.add(ev.service)
        key = key_for(ev)
        cs = commands.get(key)
        if cs is None:
            cs = CommandStats(service=key[0], command_id=key[1], cmif_type=key[2])
            commands[key] = cs
        cs.is_domain = cs.is_domain or ev.is_domain
        cs.is_tipc = cs.is_tipc or ev.is_tipc
        if ev.is_request:
            cs.request_count += 1
            cs.req_raw_sizes[ev.raw_size] += 1
            cs.req_buffer_sigs[_buffer_signature(ev)] += 1
            cs.copy_handle_counts[ev.copy_handles] += 1
            cs.move_handle_counts[ev.move_handles] += 1
            req_by_corr[ev.correlation_id] = ev
            if ev.payload is not None:
                req_payloads[key].append(ev.payload)
        else:
            cs.response_count += 1
            cs.resp_raw_sizes[ev.raw_size] += 1
            cs.resp_buffer_sigs[_buffer_signature(ev)] += 1
            cs.results[_result_str(ev.result)] += 1
            if ev.payload is not None:
                resp_payloads[key].append(ev.payload)
            req = req_by_corr.pop(ev.correlation_id, None)
            if req is not None:
                paired_resp += 1
                cs.latencies.append(ev.timestamp - req.timestamp)

    for key, cs in commands.items():
        if key in req_payloads:
            cs.req_payload_layout = _stability_runs(req_payloads[key])
        if key in resp_payloads:
            cs.resp_payload_layout = _stability_runs(resp_payloads[key])

    total_resp = sum(1 for e in events if e.phase == PHASE_RESPONSE)
    total_req = sum(1 for e in events if e.phase == PHASE_REQUEST)
    return Analysis(
        event_count=len(events),
        services=sorted(services),
        commands=commands,
        unpaired_requests=len(req_by_corr),
        unpaired_responses=total_resp - paired_resp,
    )
