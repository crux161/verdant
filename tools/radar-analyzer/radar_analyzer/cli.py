"""radar-analyze — turn a RADARTR1 trace into interface-level facts.

Usage:
    python3 -m radar_analyzer.cli TRACE [-o OUTDIR] [--json] [--md] [--stdout]

With no output flags, prints the Markdown summary to stdout.
"""
from __future__ import annotations

import argparse
import os
import sys

from .analyze import analyze
from .report import to_json, to_markdown
from .traceformat import TraceFormatError, read_stream


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="radar-analyze", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace", help="path to a RADARTR1 trace file")
    ap.add_argument("-o", "--outdir", help="write report.json / report.md here")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--md", action="store_true", help="emit Markdown")
    ap.add_argument("--stdout", action="store_true",
                    help="print selected format(s) to stdout")
    args = ap.parse_args(argv)

    try:
        events = read_stream(args.trace)
    except (OSError, TraceFormatError) as e:
        print(f"radar-analyze: {e}", file=sys.stderr)
        return 2

    analysis = analyze(events)
    want_json = args.json
    want_md = args.md or not (args.json)       # md is the default view

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        if want_json:
            with open(os.path.join(args.outdir, "report.json"), "w") as f:
                f.write(to_json(analysis))
        if want_md:
            with open(os.path.join(args.outdir, "report.md"), "w") as f:
                f.write(to_markdown(analysis))
        print(f"radar-analyze: wrote report to {args.outdir} "
              f"({analysis.event_count} events, {len(analysis.commands)} commands)",
              file=sys.stderr)
        if not args.stdout:
            return 0

    if want_json:
        print(to_json(analysis))
    if want_md:
        print(to_markdown(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
