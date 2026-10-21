# RADARTR1 — Radar trace wire format

> The contract between the on-device **Radar** tracer (producer) and the host
> **trace analyzer** (consumer). Little-endian. Version 1.
> This is Verdant's own format. It carries only **boundary metadata** by default
> (command IDs, sizes, buffer descriptors, handle counts, result codes); raw
> payload bytes are included only in explicit opt-in capture. See
> [docs/research-tooling.md](../../../docs/research-tooling.md) §5 (output discipline).

## Stream

```
+0  char magic[8]   = "RADARTR1"
+8  u32 version     = 1
+12 u32 stream_flags            # reserved; 0
(record)*                       # zero or more records to EOF
```

## Record

```
+0   u32 record_len             # bytes AFTER this field, for this record
--- fixed header (48 bytes) ---
+0   u64 timestamp              # monotonic ticks at capture
+8   u64 correlation_id         # pairs a request with its response
+16  char service[8]            # mitm'd service name, null-padded ASCII
+24  u32 command_id             # CMIF/TIPC command id (request phase)
+28  u32 result                 # (module,desc) packed result; 0 on request
+32  u32 object_id              # domain sub-object id, or 0xFFFFFFFF
+36  u32 raw_size               # raw data payload size in bytes
+40  u8  phase                  # 0 = request, 1 = response
+41  u8  cmif_type              # IPC message type (see §Enums)
+42  u8  flags                  # bit0 domain, bit1 tipc, bit2 has_payload
+43  u8  num_buffers
+44  u8  num_copy_handles
+45  u8  num_move_handles
+46  u16 reserved
--- buffer descriptors (num_buffers × 16 bytes) ---
     u8  type                   # 0=A 1=B 2=X 3=C (see §Enums)
     u8  reserved
     u16 reserved
     u32 reserved
     u64 size
--- optional payload (only if flags.has_payload) ---
     u32 payload_len
     u8  payload[payload_len]    # opt-in capture only
```

`record_len` lets a reader skip a record it does not fully understand
(forward-compatibility): consume exactly `record_len` bytes after the length
field regardless of trailing fields it does not recognize.

## Enums

**cmif_type** (IPC message type): `0 Invalid`, `1 LegacyRequest`, `2 Close`,
`3 LegacyControl`, `4 Request`, `5 Control`, `6 RequestWithContext`,
`7 ControlWithContext`.

**buffer type**: `0 A` (input, mapped), `1 B` (output, mapped),
`2 X` (input, pointer), `3 C` (output, pointer).

**phase**: `0` request, `1` response.

**flags**: `0x1` domain message, `0x2` TIPC, `0x4` payload present.

## Discipline

- Default capture is metadata-only (`has_payload` clear). Payload capture is an
  explicit opt-in used only where layout inference requires it.
- Handle **values** are never recorded — only counts (copy/move). (Privacy and
  containment: handle values identify live kernel objects.)
- A trace captured from a Nintendo service is research material and stays in
  `RESOURCES/` (RULES.md Rule C). The analyzer's reviewed, interface-level output
  is what may be authored into a White Paper.
