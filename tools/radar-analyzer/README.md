# radar-analyzer (host)

Host-side analysis of **Radar** IPC traces (`RADARTR1`, see
[../../sysmodules/radar/docs/trace-format.md](../../sysmodules/radar/docs/trace-format.md)).
Turns a trace into **interface-level facts** — per-command raw sizes, buffer
descriptor patterns, handle-count patterns, result codes, request→response
latency, and byte-stability layout hints. Development-side tooling (Verdant's own
code); stdlib only, no dependencies.

This produces *analyzer output for researcher review*, not a White Paper. Output
is interface/wire-level only (RULES.md Rule W, [docs/research-tooling.md](../../docs/research-tooling.md) §5).
A trace captured from a Nintendo service is research material and stays in
`RESOURCES/` (Rule C); only reviewed, authored facts leave.

## Use

```bash
# markdown summary (default view) to stdout
PYTHONPATH=. python3 -m radar_analyzer.cli TRACE.radar

# write report.json + report.md into an output dir
PYTHONPATH=. python3 -m radar_analyzer.cli TRACE.radar -o OUTDIR --json --md
```

When analyzing real captures, run it inside `RESOURCES/` and keep its output
there; carry only reviewed facts into a White Paper.

## Test

```bash
python3 tests/test_analyzer.py        # 7 tests, synthetic traces only, no deps
```

## Layout

```
radar_analyzer/
  traceformat.py   RADARTR1 codec (encode for fixtures / decode for analysis)
  analyze.py       trace -> per-(service,command) interface facts + layout hints
  report.py        JSON (machine) + Markdown (white-paper input)
  cli.py           command line
tests/
  test_analyzer.py synthetic fixtures + assertions
```

## What it does / does not do

- **Does:** aggregate observed boundary facts; infer first-order payload layout
  from equal-length opt-in payloads (which byte offsets are constant vs varying).
- **Does not:** decompile, disassemble, or reconstruct internal logic. It only
  reads `RADARTR1` metadata and (opt-in) observed payload bytes.
