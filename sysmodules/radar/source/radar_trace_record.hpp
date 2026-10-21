// radar_trace_record.hpp — RADARTR1 record writer (framework-independent).
//
// The on-device half of Radar. This header serializes trace records in the exact
// RADARTR1 layout documented in sysmodules/radar/docs/trace-format.md, so the
// producer (device) and consumer (tools/radar-analyzer) cannot drift.
//
// It is deliberately framework-independent: it takes already-extracted boundary
// fields and emits bytes to a caller-provided sink. The libstratosphere mitm
// integration that *extracts* those fields lives in the (stubbed) service layer
// and is the part that needs the devkitPro + libstratosphere toolchain to build.
//
// Scope: boundary metadata only (command id, sizes, buffer descriptors, handle
// COUNTS, result). Handle values are never recorded. Raw payload capture is
// opt-in. (RULES.md Rule C; trace-format.md "Discipline".)
//
// License: GPL-2.0-only (Verdant core).
#pragma once

#include <cstddef>
#include <cstdint>

namespace radar {

// ---- wire constants (keep in lockstep with trace-format.md & traceformat.py) ----
inline constexpr char   kMagic[8]   = {'R','A','D','A','R','T','R','1'};
inline constexpr uint32_t kVersion  = 1;

inline constexpr uint8_t  kPhaseRequest  = 0;
inline constexpr uint8_t  kPhaseResponse = 1;

inline constexpr uint8_t  kFlagDomain     = 0x1;
inline constexpr uint8_t  kFlagTipc       = 0x2;
inline constexpr uint8_t  kFlagHasPayload = 0x4;

inline constexpr uint32_t kNoObject = 0xFFFFFFFFu;

enum class BufferType : uint8_t { A = 0, B = 1, X = 2, C = 3 };

struct BufferDesc {
    BufferType type;
    uint64_t   size;
};

struct Event {
    uint64_t   timestamp      = 0;
    uint64_t   correlation_id = 0;
    char       service[8]     = {};   // null-padded ASCII
    uint32_t   command_id     = 0;
    uint32_t   result         = 0;    // 0 on request
    uint32_t   object_id      = kNoObject;
    uint32_t   raw_size       = 0;
    uint8_t    phase          = kPhaseRequest;
    uint8_t    cmif_type      = 4;    // Request
    uint8_t    flags          = 0;
    uint8_t    copy_handles   = 0;
    uint8_t    move_handles   = 0;
    const BufferDesc* buffers = nullptr;
    uint8_t    num_buffers    = 0;
    const void* payload       = nullptr;  // opt-in; null => metadata only
    uint32_t   payload_len    = 0;
};

// A sink receives serialized bytes (e.g. writes to USB / TCP / an SD ring buffer).
using Sink = void (*)(void* ctx, const void* data, size_t len);

namespace detail {
template <typename T>
inline void put(uint8_t*& p, T v) {                 // little-endian store
    for (size_t i = 0; i < sizeof(T); ++i) { *p++ = uint8_t(v >> (8 * i)); }
}
}  // namespace detail

// Writes the 16-byte stream header. Call once at the start of a trace stream.
inline void WriteStreamHeader(Sink sink, void* ctx, uint32_t stream_flags = 0) {
    uint8_t hdr[16];
    uint8_t* p = hdr;
    for (char c : kMagic) { *p++ = uint8_t(c); }
    detail::put<uint32_t>(p, kVersion);
    detail::put<uint32_t>(p, stream_flags);
    sink(ctx, hdr, sizeof(hdr));
}

// Serializes one Event as a RADARTR1 record and emits it through the sink.
// Caller guarantees `service` is <=8 bytes and buffers/payload pointers valid.
inline void WriteEvent(Sink sink, void* ctx, const Event& ev) {
    // record_len = fixed(48) + buffers(16*n) + optional payload(4 + len)
    const bool has_payload = ev.payload != nullptr && ev.payload_len > 0;
    uint8_t flags = ev.flags | (has_payload ? kFlagHasPayload : 0);
    uint32_t rec_len = 48u + uint32_t(ev.num_buffers) * 16u
                     + (has_payload ? 4u + ev.payload_len : 0u);

    uint8_t len_buf[4];
    { uint8_t* p = len_buf; detail::put<uint32_t>(p, rec_len); }
    sink(ctx, len_buf, sizeof(len_buf));

    uint8_t fixed[48];
    uint8_t* p = fixed;
    detail::put<uint64_t>(p, ev.timestamp);
    detail::put<uint64_t>(p, ev.correlation_id);
    for (int i = 0; i < 8; ++i) { *p++ = uint8_t(ev.service[i]); }
    detail::put<uint32_t>(p, ev.command_id);
    detail::put<uint32_t>(p, ev.result);
    detail::put<uint32_t>(p, ev.object_id);
    detail::put<uint32_t>(p, ev.raw_size);
    *p++ = ev.phase;
    *p++ = ev.cmif_type;
    *p++ = flags;
    *p++ = ev.num_buffers;
    *p++ = ev.copy_handles;
    *p++ = ev.move_handles;
    detail::put<uint16_t>(p, 0);  // reserved
    sink(ctx, fixed, sizeof(fixed));

    for (uint8_t i = 0; i < ev.num_buffers; ++i) {
        uint8_t bd[16];
        uint8_t* q = bd;
        *q++ = uint8_t(ev.buffers[i].type);
        *q++ = 0; detail::put<uint16_t>(q, 0); detail::put<uint32_t>(q, 0);
        detail::put<uint64_t>(q, ev.buffers[i].size);
        sink(ctx, bd, sizeof(bd));
    }

    if (has_payload) {
        uint8_t pl[4];
        { uint8_t* q = pl; detail::put<uint32_t>(q, ev.payload_len); }
        sink(ctx, pl, sizeof(pl));
        sink(ctx, ev.payload, ev.payload_len);
    }
}

}  // namespace radar
