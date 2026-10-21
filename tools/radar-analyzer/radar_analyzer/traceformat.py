"""RADARTR1 trace codec.

Encode/decode the Radar trace wire format (see
sysmodules/radar/docs/trace-format.md). Stdlib only. Little-endian.

The encoder exists so synthetic fixtures and an on-device reference share one
definition with the decoder; the analyzer only needs the decoder.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import BinaryIO, Iterator

MAGIC = b"RADARTR1"
VERSION = 1

_STREAM_HDR = struct.Struct("<8sII")          # magic, version, stream_flags
_REC_LEN = struct.Struct("<I")                 # record_len
_FIXED = struct.Struct("<QQ8sIIIIBBBBBBH")     # 48-byte fixed header
_BUFDESC = struct.Struct("<BBHIQ")             # 16-byte buffer descriptor
_PAYLEN = struct.Struct("<I")

assert _FIXED.size == 48
assert _BUFDESC.size == 16

# flags
FLAG_DOMAIN = 0x1
FLAG_TIPC = 0x2
FLAG_HAS_PAYLOAD = 0x4

NO_OBJECT = 0xFFFFFFFF

PHASE_REQUEST = 0
PHASE_RESPONSE = 1

CMIF_TYPE_NAMES = {
    0: "Invalid", 1: "LegacyRequest", 2: "Close", 3: "LegacyControl",
    4: "Request", 5: "Control", 6: "RequestWithContext", 7: "ControlWithContext",
}
BUFFER_TYPE_NAMES = {0: "A", 1: "B", 2: "X", 3: "C"}


@dataclass
class BufferDesc:
    type: int          # 0=A 1=B 2=X 3=C
    size: int

    @property
    def type_name(self) -> str:
        return BUFFER_TYPE_NAMES.get(self.type, f"?{self.type}")


@dataclass
class TraceEvent:
    timestamp: int
    correlation_id: int
    service: str
    command_id: int
    result: int
    object_id: int
    raw_size: int
    phase: int
    cmif_type: int
    flags: int = 0
    copy_handles: int = 0
    move_handles: int = 0
    buffers: list[BufferDesc] = field(default_factory=list)
    payload: bytes | None = None

    @property
    def is_request(self) -> bool:
        return self.phase == PHASE_REQUEST

    @property
    def is_domain(self) -> bool:
        return bool(self.flags & FLAG_DOMAIN)

    @property
    def is_tipc(self) -> bool:
        return bool(self.flags & FLAG_TIPC)

    @property
    def cmif_type_name(self) -> str:
        return CMIF_TYPE_NAMES.get(self.cmif_type, f"?{self.cmif_type}")


def _service_to_bytes(name: str) -> bytes:
    raw = name.encode("ascii")
    if len(raw) > 8:
        raise ValueError(f"service name too long (>8): {name!r}")
    return raw.ljust(8, b"\x00")


def _service_from_bytes(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", "replace")


def pack_event(ev: TraceEvent) -> bytes:
    flags = ev.flags
    if ev.payload is not None:
        flags |= FLAG_HAS_PAYLOAD
    body = bytearray()
    body += _FIXED.pack(
        ev.timestamp, ev.correlation_id, _service_to_bytes(ev.service),
        ev.command_id, ev.result, ev.object_id, ev.raw_size,
        ev.phase, ev.cmif_type, flags,
        len(ev.buffers), ev.copy_handles, ev.move_handles, 0,
    )
    for b in ev.buffers:
        body += _BUFDESC.pack(b.type, 0, 0, 0, b.size)
    if ev.payload is not None:
        body += _PAYLEN.pack(len(ev.payload))
        body += ev.payload
    return _REC_LEN.pack(len(body)) + bytes(body)


def write_stream(fh: BinaryIO, events: list[TraceEvent], stream_flags: int = 0) -> None:
    fh.write(_STREAM_HDR.pack(MAGIC, VERSION, stream_flags))
    for ev in events:
        fh.write(pack_event(ev))


def encode_stream(events: list[TraceEvent], stream_flags: int = 0) -> bytes:
    out = bytearray(_STREAM_HDR.pack(MAGIC, VERSION, stream_flags))
    for ev in events:
        out += pack_event(ev)
    return bytes(out)


class TraceFormatError(ValueError):
    pass


def _unpack_record(body: memoryview) -> TraceEvent:
    (timestamp, correlation_id, service_raw, command_id, result, object_id,
     raw_size, phase, cmif_type, flags, num_buffers, copy_h, move_h,
     _res) = _FIXED.unpack_from(body, 0)
    off = _FIXED.size
    buffers: list[BufferDesc] = []
    for _ in range(num_buffers):
        btype, _r1, _r2, _r3, bsize = _BUFDESC.unpack_from(body, off)
        buffers.append(BufferDesc(type=btype, size=bsize))
        off += _BUFDESC.size
    payload = None
    if flags & FLAG_HAS_PAYLOAD:
        (plen,) = _PAYLEN.unpack_from(body, off)
        off += _PAYLEN.size
        payload = bytes(body[off:off + plen])
        if len(payload) != plen:
            raise TraceFormatError("payload shorter than declared length")
    return TraceEvent(
        timestamp=timestamp, correlation_id=correlation_id,
        service=_service_from_bytes(service_raw), command_id=command_id,
        result=result, object_id=object_id, raw_size=raw_size, phase=phase,
        cmif_type=cmif_type, flags=flags, copy_handles=copy_h, move_handles=move_h,
        buffers=buffers, payload=payload,
    )


def decode_stream(data: bytes) -> Iterator[TraceEvent]:
    """Yield TraceEvents from an in-memory RADARTR1 stream."""
    if len(data) < _STREAM_HDR.size:
        raise TraceFormatError("stream too short for header")
    magic, version, _flags = _STREAM_HDR.unpack_from(data, 0)
    if magic != MAGIC:
        raise TraceFormatError(f"bad magic {magic!r}")
    if version != VERSION:
        raise TraceFormatError(f"unsupported version {version}")
    mv = memoryview(data)
    off = _STREAM_HDR.size
    while off < len(data):
        if off + _REC_LEN.size > len(data):
            raise TraceFormatError("truncated record length")
        (rec_len,) = _REC_LEN.unpack_from(data, off)
        off += _REC_LEN.size
        end = off + rec_len
        if end > len(data):
            raise TraceFormatError("record_len exceeds stream")
        yield _unpack_record(mv[off:end])     # skips any unknown trailing bytes
        off = end


def read_stream(path: str) -> list[TraceEvent]:
    with open(path, "rb") as fh:
        return list(decode_stream(fh.read()))
