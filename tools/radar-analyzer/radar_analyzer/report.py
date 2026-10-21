"""Render an Analysis as JSON (machine) or Markdown (white-paper input)."""
from __future__ import annotations

import json

from .analyze import Analysis, CommandStats, LayoutRun


def _counter_top(counter, n=6):
    return [{"value": v, "count": c} for v, c in counter.most_common(n)]


def _layout(runs: list[LayoutRun]):
    return [{"start": r.start, "length": r.length, "kind": r.kind} for r in runs]


def _cmd_dict(cs: CommandStats) -> dict:
    return {
        "service": cs.service,
        "command_id": cs.command_id,
        "cmif_type": cs.cmif_type_name,
        "domain": cs.is_domain,
        "tipc": cs.is_tipc,
        "request_count": cs.request_count,
        "response_count": cs.response_count,
        "req_raw_sizes": _counter_top(cs.req_raw_sizes),
        "resp_raw_sizes": _counter_top(cs.resp_raw_sizes),
        "req_buffers": _counter_top(cs.req_buffer_sigs),
        "resp_buffers": _counter_top(cs.resp_buffer_sigs),
        "copy_handles": _counter_top(cs.copy_handle_counts),
        "move_handles": _counter_top(cs.move_handle_counts),
        "results": _counter_top(cs.results),
        "latency": cs.latency_stats,
        "req_payload_layout": _layout(cs.req_payload_layout),
        "resp_payload_layout": _layout(cs.resp_payload_layout),
    }


def to_json(analysis: Analysis, indent: int = 2) -> str:
    return json.dumps({
        "event_count": analysis.event_count,
        "services": analysis.services,
        "unpaired_requests": analysis.unpaired_requests,
        "unpaired_responses": analysis.unpaired_responses,
        "commands": [_cmd_dict(cs) for cs in analysis.command_list()],
    }, indent=indent)


def _top_value(counter) -> str:
    items = counter.most_common(3)
    return ", ".join(str(v) for v, _ in items) if items else "-"


def to_markdown(analysis: Analysis) -> str:
    lines: list[str] = []
    lines.append("# Radar trace — observed interface facts")
    lines.append("")
    lines.append("> **Provenance: Stage C (observed on the wire).** This is "
                 "analyzer output for researcher review, not a White Paper. "
                 "Interface-level facts only; confirm and author per RULES.md "
                 "Rule W before use.")
    lines.append("")
    lines.append(f"- events: {analysis.event_count}")
    lines.append(f"- services: {', '.join(analysis.services) or '-'}")
    lines.append(f"- unpaired requests/responses: "
                 f"{analysis.unpaired_requests}/{analysis.unpaired_responses}")
    lines.append("")

    by_service: dict[str, list[CommandStats]] = {}
    for cs in analysis.command_list():
        by_service.setdefault(cs.service, []).append(cs)

    for service in sorted(by_service):
        lines.append(f"## `{service}`")
        lines.append("")
        lines.append("| cmd id | type | reqs | resps | req raw | resp raw | "
                     "buffers (req/resp) | copy/move h | results |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for cs in by_service[service]:
            lat = cs.latency_stats
            dom = " ·domain" if cs.is_domain else ""
            tipc = " ·tipc" if cs.is_tipc else ""
            lines.append(
                f"| {cs.command_id} | {cs.cmif_type_name}{dom}{tipc} "
                f"| {cs.request_count} | {cs.response_count} "
                f"| {_top_value(cs.req_raw_sizes)} | {_top_value(cs.resp_raw_sizes)} "
                f"| {_top_value(cs.req_buffer_sigs)} / {_top_value(cs.resp_buffer_sigs)} "
                f"| {_top_value(cs.copy_handle_counts)}/{_top_value(cs.move_handle_counts)} "
                f"| {_top_value(cs.results)} |"
            )
        lines.append("")
        # layout hints, if any
        for cs in by_service[service]:
            for label, runs in (("request", cs.req_payload_layout),
                                ("response", cs.resp_payload_layout)):
                if runs:
                    desc = ", ".join(
                        f"[{r.start}:{r.start + r.length}){r.kind[0]}" for r in runs)
                    lines.append(f"- cmd {cs.command_id} {label} layout hint "
                                 f"(const=c/var=v): {desc}")
        if any(cs.req_payload_layout or cs.resp_payload_layout
               for cs in by_service[service]):
            lines.append("")
    return "\n".join(lines) + "\n"
