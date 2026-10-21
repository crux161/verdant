# Radar — on-device IPC tracer

Radar is a Verdant sysmodule that observes the client-server IPC boundary as a
**black box** and emits `RADARTR1` traces for the host
[radar-analyzer](../../tools/radar-analyzer/). It is the cleanest clean-room input
source (Stage C in [docs/research-tooling.md](../../docs/research-tooling.md)):
it records *observed* command IDs, payload sizes, buffer descriptors, handle
counts, and result codes — never decompiled internals.

Plan: PLAN.md P2.5.1 (LEXICON: Radar). License: GPL-2.0-only.

## Status

| Part | State |
|---|---|
| `RADARTR1` wire format ([docs/trace-format.md](docs/trace-format.md)) | defined |
| `source/radar_trace_record.hpp` — record writer | **done; host-compiles (`-Wall -Wextra`); byte-for-byte cross-checked against the Python codec** |
| mitm service layer (hook extraction via libstratosphere `sf`) | **skeleton / TODO — needs devkitPro + libstratosphere toolchain (PLAN P0.3) and the Phase-2 boot/mitm plumbing (P2.3/P2.5) to build and run** |
| transports (USB / TCP / SD ring buffer) | TODO |

The record writer is framework-independent and already verified. What remains is
the device-side glue that extracts boundary fields from intercepted IPC and feeds
them to `WriteEvent()`, plus a transport. That glue is written against
libstratosphere's mitm framework and is **not buildable in a host-only
environment**; it lands when the toolchain and boot chain exist.

## Design

```
   intercepted IPC (libstratosphere sf mitm)
            │  extract boundary fields (no handle values, no payload unless opt-in)
            ▼
   radar::Event  ──WriteEvent()──▶  RADARTR1 bytes  ──Sink──▶  transport
                                                                 (USB/TCP/SD)
            host: radar-analyzer  ◀───────────────────────────────┘
```

- **Metadata by default.** Command id, sizes, buffer descriptor types, handle
  *counts*, result. Handle values are never recorded. Raw payload capture is an
  explicit opt-in flag used only where layout inference needs it.
- **Configurable target list.** Which services to trace is configuration, not
  hard-coded; default is empty (traces nothing until asked).
- **Containment.** A trace captured from a Nintendo service is research material
  and stays in `RESOURCES/` (RULES.md Rule C). Only reviewed, authored facts leave.

## Building (when the toolchain exists)

Requires the pinned devkitPro A64 toolchain and libstratosphere (PLAN P0.3). Not
buildable host-only. The record writer alone can be host-compiled for testing:

```bash
clang++ -std=c++17 -I source -Wall -Wextra -c source/radar_trace_record.hpp -o /dev/null
```
