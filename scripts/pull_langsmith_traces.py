#!/usr/bin/env python3
"""
Pull LangSmith traces for the health agent and dump them for analysis.

Why this exists
---------------
The biomarker analyser (and every other specialist) is invoked through the
supervisor -> specialist delegation in ``whoopdata/agent/specialists.py``. When
something feels "forgotten" across turns, the fastest way to confirm what
actually happened is to read the real trace: which specialist ran, which tools
it called, and — crucially — exactly what ``messages`` were passed into the
specialist sub-run. This script pulls that from LangSmith so it can be eyeballed
or fed back to Claude.

The LangSmith read API (``list_runs`` / ``read_run``) works on the free
(Developer) plan — only trace volume and retention are limited, not API access.

Usage
-----
    uv run python scripts/pull_langsmith_traces.py --list
    uv run python scripts/pull_langsmith_traces.py --hours 1 --filter biomarkers
    uv run python scripts/pull_langsmith_traces.py --trace <trace_id>
    uv run python scripts/pull_langsmith_traces.py --run <run_id>
    uv run python scripts/pull_langsmith_traces.py --thread <thread_id>
    uv run python scripts/pull_langsmith_traces.py <id>          # auto-detect

Filter names (``--filter`` / ``--list``) are derived live from
``whoopdata/agent/registry.AGENT_REGISTRY`` so they stay in sync automatically
whenever a specialist or tool is added or renamed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Run from the repo root (uv run python scripts/...) so ``whoopdata`` imports.
from whoopdata.agent.registry import AGENT_REGISTRY

load_dotenv()

DEFAULT_PROJECT = os.getenv("LANGSMITH_PROJECT") or os.getenv(
    "LANGCHAIN_PROJECT", "whoop-health-agent"
)
DEFAULT_OUT = Path("data/traces")


# ---------------------------------------------------------------------------
# Registry-derived targets (single source of truth)
# ---------------------------------------------------------------------------
def known_targets() -> dict[str, list[str]]:
    """Map each specialist name to the tool names it can call.

    Read straight from AGENT_REGISTRY so the CLI never goes stale: add or rename
    a specialist/tool there and ``--list`` / ``--filter`` pick it up for free.
    """
    return {
        name: list(cfg.get("tools", []))
        for name, cfg in AGENT_REGISTRY.items()
    }


def all_target_names() -> set[str]:
    """Every valid filter token: specialist names + every tool name."""
    names: set[str] = set(AGENT_REGISTRY.keys())
    for tools in known_targets().values():
        names.update(tools)
    return names


def print_targets() -> None:
    """Print each specialist and its tools (the answer to "what can I filter on?")."""
    targets = known_targets()
    print("Specialists and the tools you can filter on (from AGENT_REGISTRY):\n")
    for specialist in sorted(targets):
        print(f"  {specialist}")
        for tool in sorted(targets[specialist]):
            print(f"      - {tool}")
    print(
        "\nPass any of these names to --filter (repeatable / comma-separated), e.g.\n"
        "  --filter biomarkers   or   --filter get_biomarker_results,analytics"
    )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def _json_safe(obj):
    """Best-effort conversion of LangSmith run payloads to JSON-safe values."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _run_to_dict(run) -> dict:
    """Flatten a LangSmith run into the JSON-safe shape we persist."""
    return {
        "id": str(run.id),
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "trace_id": str(getattr(run, "trace_id", "") or ""),
        "name": run.name,
        "run_type": run.run_type,
        "start_time": _json_safe(getattr(run, "start_time", None)),
        "end_time": _json_safe(getattr(run, "end_time", None)),
        "error": run.error,
        "inputs": _json_safe(getattr(run, "inputs", None)),
        "outputs": _json_safe(getattr(run, "outputs", None)),
        "metadata": _json_safe((getattr(run, "extra", None) or {}).get("metadata")),
    }


def _latency(run) -> str:
    """Human-readable run duration, or "-" when timing is missing."""
    start = getattr(run, "start_time", None)
    end = getattr(run, "end_time", None)
    if start and end:
        return f"{(end - start).total_seconds():.2f}s"
    return "-"


def _truncate(value, limit: int = 300) -> str:
    """Collapse whitespace and clip a value to a single readable line."""
    text = value if isinstance(value, str) else json.dumps(_json_safe(value), default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + " …(truncated)"


# ---------------------------------------------------------------------------
# Trace fetching
# ---------------------------------------------------------------------------
def fetch_trace_runs(client, project: str, trace_id: str) -> list:
    """All runs belonging to one trace, oldest first."""
    runs = list(client.list_runs(project_name=project, trace_id=trace_id))
    runs.sort(key=lambda r: getattr(r, "start_time", None) or datetime.min)
    return runs


def matches_filter(runs: list, wanted: set[str]) -> bool:
    """True if any run name substring-matches a wanted specialist/tool (case-insensitive)."""
    if not wanted:
        return True
    lowered = {w.lower() for w in wanted}
    for run in runs:
        name = (run.name or "").lower()
        if any(w in name for w in lowered):
            return True
    return False


def thread_id_of(run) -> str | None:
    """The conversation thread_id stored in a run's metadata, if present."""
    meta = (getattr(run, "extra", None) or {}).get("metadata") or {}
    return meta.get("thread_id") or meta.get("conversation_id")


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------
def render_timeline(runs: list) -> str:
    """Indented run tree. Specialist/agent runs get their input messages shown."""
    by_parent: dict[str | None, list] = {}
    for run in runs:
        key = str(run.parent_run_id) if run.parent_run_id else None
        by_parent.setdefault(key, []).append(run)

    lines: list[str] = []
    specialist_names = {n.lower() for n in AGENT_REGISTRY.keys()}

    def walk(parent_key: str | None, depth: int) -> None:
        children = by_parent.get(parent_key, [])
        children.sort(key=lambda r: getattr(r, "start_time", None) or datetime.min)
        for run in children:
            indent = "  " * depth
            tag = f"[{run.run_type}]"
            lines.append(f"{indent}{tag} {run.name}  ({_latency(run)})")
            if run.error:
                lines.append(f"{indent}  ✗ error: {_truncate(run.error, 300)}")

            inputs = getattr(run, "inputs", None) or {}
            # The key diagnostic: what messages flowed into a specialist/agent run.
            is_specialist = (run.name or "").lower() in specialist_names
            if (is_specialist or run.run_type in ("chain", "llm")) and "messages" in inputs:
                msgs = inputs.get("messages")
                if isinstance(msgs, list):
                    lines.append(f"{indent}  input messages ({len(msgs)}):")
                    for m in msgs:
                        role = ""
                        content = m
                        if isinstance(m, dict):
                            role = m.get("role") or m.get("type") or ""
                            content = m.get("content", m)
                        lines.append(
                            f"{indent}    - {role or '?'}: {_truncate(content, 300)}"
                        )
            elif run.run_type == "tool":
                if inputs:
                    lines.append(f"{indent}  args: {_truncate(inputs, 300)}")
                out = getattr(run, "outputs", None)
                if out:
                    lines.append(f"{indent}  output: {_truncate(out, 300)}")

            walk(str(run.id), depth + 1)

    # Defensive: if the true root wasn't returned, promote any run whose parent
    # is missing to a top-level node so nothing is silently dropped.
    if None not in by_parent:
        known_ids = {str(r.id) for r in runs}
        for run in runs:
            pk = str(run.parent_run_id) if run.parent_run_id else None
            if pk not in known_ids:
                by_parent.setdefault(None, []).append(run)

    walk(None, 0)
    return "\n".join(lines) if lines else "(no runs)"


def dump_trace(runs: list, trace_id: str, out_dir: Path) -> None:
    """Write a trace's raw JSON and readable timeline to disk, and print the timeline."""
    out_dir.mkdir(parents=True, exist_ok=True)
    short = trace_id.split("-")[0]

    json_path = out_dir / f"trace_{short}.json"
    json_path.write_text(
        json.dumps([_run_to_dict(r) for r in runs], indent=2, default=str)
    )

    timeline = render_timeline(runs)
    header = f"Trace {trace_id}  ({len(runs)} runs)"
    txt_path = out_dir / f"trace_{short}.txt"
    txt_path.write_text(f"{header}\n{'=' * len(header)}\n{timeline}\n")

    print(f"\n{header}")
    print("=" * len(header))
    print(timeline)
    print(f"\n  → JSON:     {json_path}")
    print(f"  → timeline: {txt_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_filters(raw: list[str] | None) -> set[str]:
    """Split repeated/comma-separated --filter values and warn on unknown names."""
    if not raw:
        return set()
    wanted: set[str] = set()
    for item in raw:
        wanted.update(part.strip() for part in item.split(",") if part.strip())
    valid = all_target_names()
    for name in sorted(wanted):
        if name not in valid and not any(name.lower() in v.lower() for v in valid):
            print(
                f"⚠️  '{name}' is not a known specialist or tool. "
                f"Run with --list to see valid names.",
                file=sys.stderr,
            )
    return wanted


def main() -> int:
    """Parse args and dispatch to --list, a targeted id pull, or a recent sweep."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("id", nargs="?", help="A trace_id, run_id, or thread_id (auto-detected)")
    parser.add_argument("--trace", help="Pull one full trace by trace_id")
    parser.add_argument("--run", help="Pull the trace containing this run_id")
    parser.add_argument("--thread", help="Pull traces for this conversation thread_id")
    parser.add_argument("--hours", type=int, default=24, help="Recent-sweep window (default 24)")
    parser.add_argument("--limit", type=int, default=20, help="Max traces in recent sweep (default 20)")
    parser.add_argument("--filter", action="append", help="Specialist/tool name(s) to keep. Repeatable / comma-separated.")
    parser.add_argument("--list", action="store_true", help="List known specialists/tools and exit")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help=f"LangSmith project (default: {DEFAULT_PROJECT})")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"Output dir (default: {DEFAULT_OUT})")
    args = parser.parse_args()

    if args.list:
        print_targets()
        return 0

    try:
        from langsmith import Client
    except ImportError:
        print("langsmith is not installed (expected in this project).", file=sys.stderr)
        return 1

    if not (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")):
        print("No LANGSMITH_API_KEY / LANGCHAIN_API_KEY in environment.", file=sys.stderr)
        return 1

    client = Client()
    out_dir = Path(args.out)
    wanted = parse_filters(args.filter)
    print(f"Project: {args.project}")

    # ---- Targeted modes -------------------------------------------------
    trace_id = args.trace
    run_id = args.run
    thread_id = args.thread

    # Auto-detect a bare positional id. run_id resolves to a trace; thread is a
    # metadata value (not a uuid we can read directly), so only treat as thread
    # when explicitly passed. A bare id is tried as trace first, then run.
    if args.id and not (trace_id or run_id or thread_id):
        trace_id = args.id

    if run_id:
        try:
            run = client.read_run(run_id)
            trace_id = str(run.trace_id)
        except Exception as exc:
            print(f"Could not read run {run_id}: {exc}", file=sys.stderr)
            return 1

    if trace_id:
        runs = fetch_trace_runs(client, args.project, trace_id)
        if not runs and args.id:
            # The bare id might actually be a run_id, not a trace_id.
            try:
                run = client.read_run(args.id)
                runs = fetch_trace_runs(client, args.project, str(run.trace_id))
                trace_id = str(run.trace_id)
            except Exception:
                pass
        if not runs:
            print(f"No runs found for trace {trace_id}.", file=sys.stderr)
            return 1
        dump_trace(runs, trace_id, out_dir)
        return 0

    # ---- Recent sweep (optionally thread-scoped) ------------------------
    start_time = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    roots = list(
        client.list_runs(
            project_name=args.project,
            is_root=True,
            start_time=start_time,
            limit=args.limit,
        )
    )
    if not roots:
        print(f"No traces in the last {args.hours}h for project '{args.project}'.")
        return 0

    print(f"Found {len(roots)} root run(s) in the last {args.hours}h.")
    matched = 0
    for root in roots:
        if thread_id and thread_id_of(root) != thread_id:
            continue
        tid = str(getattr(root, "trace_id", root.id))
        runs = fetch_trace_runs(client, args.project, tid)
        if not matches_filter(runs, wanted):
            continue
        dump_trace(runs, tid, out_dir)
        matched += 1

    if matched == 0:
        suffix = f" matching filter {sorted(wanted)}" if wanted else ""
        print(f"\nNo traces{suffix} found.")
    else:
        print(f"\n✅ Dumped {matched} trace(s) to {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
