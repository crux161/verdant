"""radar_analyzer — host-side analysis of RADARTR1 IPC traces.

Produces interface-level facts (command surface, payload sizes, buffer/handle
patterns, result codes, latency, byte-stability layout hints) from Radar traces.
Development-side tooling; consumes only RADARTR1 streams. See
docs/research-tooling.md and sysmodules/radar/docs/trace-format.md.
"""
from .analyze import Analysis, CommandStats, analyze
from .report import to_json, to_markdown
from .traceformat import (
    BufferDesc, TraceEvent, decode_stream, encode_stream, read_stream,
    write_stream,
)

__all__ = [
    "Analysis", "CommandStats", "analyze", "to_json", "to_markdown",
    "BufferDesc", "TraceEvent", "decode_stream", "encode_stream",
    "read_stream", "write_stream",
]
__version__ = "0.1.0"
