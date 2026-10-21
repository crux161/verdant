"""Self-contained tests for radar_analyzer. Run: python3 tests/test_analyzer.py

No pytest dependency: plain asserts, a tiny runner, synthetic traces only.
Synthetic data contains no proprietary content (RULES.md Rule C).
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from radar_analyzer.analyze import analyze                     # noqa: E402
from radar_analyzer.report import to_json, to_markdown         # noqa: E402
from radar_analyzer.traceformat import (                       # noqa: E402
    FLAG_DOMAIN, NO_OBJECT, PHASE_REQUEST, PHASE_RESPONSE, BufferDesc,
    TraceEvent, decode_stream, encode_stream, read_stream, write_stream,
)

_corr = [0]


def _next_corr() -> int:
    _corr[0] += 1
    return _corr[0]


def req(service, cmd, ts, raw_size=8, buffers=None, copy=0, move=0,
        cmif_type=4, flags=0, payload=None, corr=None):
    return TraceEvent(
        timestamp=ts, correlation_id=corr if corr is not None else _next_corr(),
        service=service, command_id=cmd, result=0, object_id=NO_OBJECT,
        raw_size=raw_size, phase=PHASE_REQUEST, cmif_type=cmif_type, flags=flags,
        copy_handles=copy, move_handles=move, buffers=buffers or [], payload=payload)


def resp(ev_req, ts, result=0, raw_size=8, buffers=None, copy=0, move=0,
         payload=None):
    return TraceEvent(
        timestamp=ts, correlation_id=ev_req.correlation_id, service=ev_req.service,
        command_id=ev_req.command_id, result=result, object_id=NO_OBJECT,
        raw_size=raw_size, phase=PHASE_RESPONSE, cmif_type=ev_req.cmif_type,
        flags=ev_req.flags, copy_handles=copy, move_handles=move,
        buffers=buffers or [], payload=payload)


def build_trace():
    events = []
    # set:sys cmd 23 (GetColorSetId-like): 4 calls, all success, small out
    for i in range(4):
        r = req("set:sys", 23, ts=100 + i * 10, raw_size=0)
        events.append(r)
        events.append(resp(r, ts=105 + i * 10, result=0, raw_size=4))
    # set:sys cmd 37 (GetSettingsItemValue-like): out buffer type B; one not-found
    for i, result in enumerate([0, 0, (0x1F5 << 9) | 0x19]):  # fabricated (25-501-ish)
        r = req("set:sys", 37, ts=200 + i * 10, raw_size=16,
                buffers=[BufferDesc(type=2, size=32), BufferDesc(type=1, size=64)])
        events.append(r)
        events.append(resp(r, ts=203 + i * 10, result=result, raw_size=4,
                           buffers=[BufferDesc(type=1, size=64)]))
    # set cmd 0 (GetLanguageCode-like): response payload is an 8-byte code,
    # first 2 bytes constant ("en"), rest varies -> layout hint
    payloads = [b"en-US\x00\x00\x00", b"en-GB\x00\x00\x00", b"en-XX\x00\x00\x00"]
    for i, pl in enumerate(payloads):
        r = req("set", 0, ts=300 + i * 10, raw_size=0)
        events.append(r)
        events.append(resp(r, ts=302 + i * 10, result=0, raw_size=8, payload=pl))
    # a request with a moved handle, no response (unpaired)
    events.append(req("set:sys", 99, ts=400, raw_size=8, move=1))
    return events


def test_roundtrip_codec():
    events = build_trace()
    blob = encode_stream(events)
    decoded = list(decode_stream(blob))
    assert len(decoded) == len(events), (len(decoded), len(events))
    # spot check a payload event survived
    pls = [e.payload for e in decoded if e.payload is not None]
    assert b"en-US\x00\x00\x00" in pls
    # file round-trip
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.radar")
        with open(p, "wb") as fh:
            write_stream(fh, events)
        again = read_stream(p)
        assert len(again) == len(events)


def test_forward_compat_trailing_bytes():
    # Append unknown trailing bytes inside a record; record_len must let us skip.
    from radar_analyzer import traceformat as tf
    ev = req("set", 0, ts=1, raw_size=0)
    rec = tf.pack_event(ev)
    (rlen,) = tf._REC_LEN.unpack_from(rec, 0)
    body = rec[tf._REC_LEN.size:]
    extra = b"\xAA\xBB\xCC\xDD"
    patched = tf._REC_LEN.pack(rlen + len(extra)) + body + extra
    stream = tf._STREAM_HDR.pack(tf.MAGIC, tf.VERSION, 0) + patched
    got = list(decode_stream(stream))
    assert len(got) == 1 and got[0].service == "set"


def test_command_aggregation():
    a = analyze(build_trace())
    assert a.services == ["set", "set:sys"]
    cs = a.commands[("set:sys", 23, 4)]
    assert cs.request_count == 4 and cs.response_count == 4
    assert cs.results.most_common(1)[0] == ("Success(0)", 4)
    # cmd 37: two success, one failure; out buffer sig "B"
    cs37 = a.commands[("set:sys", 37, 4)]
    assert cs37.response_count == 3
    assert cs37.results["Success(0)"] == 2
    assert sum(cs37.results.values()) == 3
    assert cs37.req_buffer_sigs.most_common(1)[0][0] == "X,B"
    assert cs37.resp_buffer_sigs.most_common(1)[0][0] == "B"
    # latency present and positive
    assert cs.latency_stats["count"] == 4
    assert cs.latency_stats["min"] == 5


def test_unpaired():
    a = analyze(build_trace())
    assert a.unpaired_requests == 1       # the move-handle request with no response
    assert a.unpaired_responses == 0


def test_handle_counts():
    a = analyze(build_trace())
    cs99 = a.commands[("set:sys", 99, 4)]
    assert cs99.move_handle_counts[1] == 1


def test_payload_layout_hint():
    a = analyze(build_trace())
    cs = a.commands[("set", 0, 4)]
    runs = cs.resp_payload_layout
    assert runs, "expected a layout hint from 3 equal-length payloads"
    # payloads en-US / en-GB / en-XX share the constant prefix "en-" (len 3)
    assert runs[0].kind == "const" and runs[0].start == 0 and runs[0].length == 3
    # total coverage == payload length (8)
    assert sum(r.length for r in runs) == 8
    # there must be at least one varying region
    assert any(r.kind == "var" for r in runs)


def test_reports_render():
    a = analyze(build_trace())
    js = to_json(a)
    assert '"service": "set:sys"' in js
    md = to_markdown(a)
    assert "## `set:sys`" in md and "Stage C" in md
    # no deny-listed / decompiler fingerprints in rendered output
    for bad in ("FUN_", "DAT_", "undefined8", "Lotus", "Mariko"):
        assert bad not in md and bad not in js


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERR   {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
