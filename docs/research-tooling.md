# Research Tooling & Methodology

> How the research side automates extraction of **interface-level facts** from the
> reference firmware, and the division of labor that keeps every white paper
> clean-room-clean. Pure engineering/methodology — this doc contains no
> proprietary content and is committed. Companion: [RULES.md](../RULES.md),
> [whitepapers/README.md](../whitepapers/README.md), [PLAN.md](../PLAN.md)
> (PR.2–PR.5, P2.5).

## 1. The line (what the tooling is *for*)

The tooling extracts **functional facts** at the client-server boundary:
command identifiers, wire/payload layouts, buffer descriptor types, handle
conventions, error-code mappings, and observable ordering/blocking behavior.

It does **not** reconstruct internal algorithms, function bodies, or
implementation details. Those are the protectable *expression*; the interface is
*function*. (RULES.md Rule 0 / Rule W; cf. the pasted specification rules:
"describe only the what and the external interaction… do not reconstruct internal
proprietary code algorithms, function names, or implementation details.")

A simple test for any proposed extractor: **does its output read like a wire
protocol / API reference, or like a translation of someone's source?** The first
is in scope; the second is not.

## 2. Division of labor

| Role | Does | Never |
|---|---|---|
| **Tool author** (may be assisted) | Writes general-purpose extractors/analyzers. The tools contain none of the subject's code. | Reads decompiled bodies to write prose; builds a function-body→prose exporter for transcription. |
| **Tooling run** (in `RESOURCES/` only) | Runs extractors on research material; emits **interface tables** + traces. Output stays in `RESOURCES/`. | Emits transcribed algorithms; writes outside `RESOURCES/`. |
| **Researcher** | Reviews extracted interface facts; authors the White Paper from them + public references. | Copies code/expression into the paper; leaks research material. |
| **Developer** | Implements from the White Paper + public sources. | Reads `RESOURCES/`. |

The extractor output is **data a person vets**, not a spec. The White Paper is
authored by a researcher and obeys the completeness contract
([whitepapers/README.md](../whitepapers/README.md)).

## 3. The pipeline

```
          ┌────────────────────────── RESOURCES/ (contained) ──────────────────────────┐
  firmware│                                                                              │
  (user)  ▼                                                                              │
   ┌──────────────┐   ┌───────────────────┐   ┌────────────────────┐                    │
   │ A. Catalog & │──▶│ B. Static iface    │──▶│  interface tables  │                    │
   │ format parse │   │    extraction      │   │  (command/layout/  │─┐                  │
   └──────────────┘   └───────────────────┘   │   boundary data)   │ │                  │
          │           ┌───────────────────┐   └────────────────────┘ │  ┌─────────────┐ │
   on-device ───────▶ │ C. Dynamic obs.    │──▶  observed traces  ────┼─▶│ E. Researcher│ │
   (Radar)            │    (IPC tracing)   │                          │  │   review     │ │
                      └───────────────────┘                          │  └─────────────┘ │
   two versions ────▶ ┌───────────────────┐   ┌────────────────────┐ │        │         │
                      │ D. Version diff    │──▶│ iface change report│─┘        │         │
                      └───────────────────┘   └────────────────────┘          │         │
          └──────────────────────────────────────────────────────────────────┼─────────┘
                                                                               ▼
                                                   White Paper (whitepapers/)  ──▶ Development
```

### Stage A — Catalog & format parsing *(static, public formats)*
Parse module container/formats (NSO/NRO/KIP headers, segments, dynamic symbol
tables, build IDs; NCA/PFS0/HFS0/RomFS structure). These formats are publicly
documented (LibHac, hactool/nstool). Output: a catalog of modules with identity,
hashes, build IDs, and segment maps. *No expression — structure only.*

### Stage B — Static interface extraction *(static)*
Walk the service-framework **dispatch metadata** to emit, per service: command
IDs, (optional) symbol-derived names, input/output raw sizes, buffer descriptor
types, and handle move/copy. Walk **marshalling metadata** to emit payload field
layouts. Output: **command tables** and **payload layout tables**. *Interface
facts, not algorithms — the extractor reads the structured dispatch/marshalling
tables, not the handler bodies.*

### Stage C — Dynamic observation *(on-device, cleanest source)*
**Radar** (IPC tracer, PLAN P2.5.1) captures live boundary traffic as a black
box: command IDs, payload bytes, buffer descriptors, handles, result codes,
timing/order. A host-side **trace analyzer** turns captures into the same
interface tables as Stage B, and infers payload layout from observed messages.
This touches no decompiled expression and is the preferred source where available.

### Stage D — Version diff *(static/structural)*
Orchestrate binary diffing (BinDiff / Diaphora as tools) between two versions to
produce an **interface-level change report**: added/removed commands, changed
argument sizes, new result codes, new modules. Feeds re-baselining (PLAN PR.4) and
the 23.0.0↔23.0.1 reconciliation (WP-ALMANAC-00 LEDGER O-1).

### Stage E — Researcher review → White Paper
A researcher reviews the extracted tables and traces, cross-checks against public
references, resolves/records Verification-Ledger items, and authors the White
Paper. Only the White Paper leaves `RESOURCES/`.

## 4. Mapping to the stated targets

| Target | Produced by |
|---|---|
| 1. External API surface & service command identifiers | Stage A (service registration/catalog) + Stage B (command tables) + Stage C (observed) |
| 2. Exact IPC request/response payload layout & field offsets | Stage B (marshalling metadata) + Stage C (inferred from traces) |
| 3. Sync primitives, handle management, error-code mappings at the boundary | Stage B (handle/result metadata) + Stage C (observed blocking/signaling, handles, result codes) |

Cross-checking Stage B against Stage C (static vs observed) is also the
**confidence mechanism**: agreement promotes a fact out of the Verification Ledger.

## 5. Output discipline

- **Interface-level only.** Tool output is tables/traces of boundary facts. If an
  extractor would emit function bodies or reconstructed algorithms, it is
  redesigned or dropped.
- **Contained.** All raw output stays in `RESOURCES/` (Rule C). Only reviewed
  facts, authored into a White Paper in our own words, leave.
- **Provenance-tagged.** Each extracted fact carries its source stage (A/B/C/D) so
  the White Paper's provenance table and Verification Ledger can cite it.
- **No code transcription.** The bridge to Development is the White Paper (prose,
  tables, behavior), never extractor output verbatim.

## 6. Tool inventory

Status legend: `buildable` = appropriate to implement now; `design` = needs a
short design pass first.

| Tool | Stage | Target(s) | Status | Notes |
|---|---|---|---|---|
| Module catalog + format parser | A | 1 | buildable | builds on public format docs / hactool |
| Dispatch-table extractor | B | 1, 3 | buildable | headless-analysis script; emits command tables |
| Marshalling-layout extractor | B | 2 | design | define the layout-table schema first |
| **Radar** IPC tracer (on-device) | C | 1, 2, 3 | record writer **done** (host-verified); mitm glue TODO (toolchain) | `sysmodules/radar/`; PLAN P2.5.1 |
| Trace analyzer (host) | C | 1, 2, 3 | **done** (built + tested) | `tools/radar-analyzer/`; traces → interface tables; layout inference |
| **Doppler** differential harness | C | all | buildable | compare two endpoints; PLAN P2.5.4 |
| Version-diff orchestrator | D | 1, 2, 3 | buildable | BinDiff/Diaphora → change report |
| Containment/provenance plumbing | all | — | buildable | tagging, `RESOURCES/`-only output, lint |

## 7. Off-limits (kept narrow)

- Transcribing decompiled function bodies into prose/specs.
- A mass function-body → prose/pseudocode exporter built for transcription.
- Reconstructing internal algorithms or implementation detail.
- Anything whose purpose is defeating a protection to enable piracy (not a project
  goal; PLAN ADR-008, RULES.md).

## 8. Suggested first build

**Radar + trace analyzer (Stage C).** It is black-box, the cleanest clean-room
source, directly yields all three targets as *observed* facts, and its output is
the strongest possible provenance ("observed on the wire"). The static extractors
(Stage A/B) are a strong complement and the natural second build, giving the
static↔dynamic cross-check in §4.
