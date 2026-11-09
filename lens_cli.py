"""CLI + slash-command entry points for Context Lens."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .lens_core import Analyzer
from .lens_render import format_overview, format_session

_USAGE = (
    "Context Lens\n"
    "  /lens                  current session at a glance\n"
    "  /lens full             full session view\n"
    "  /lens overview [days]  cross-session dashboard (default 7 days)\n"
    "  /lens session <id>     inspect another session\n"
    "\n"
    "CLI: hermes context-lens [overview|session] ..."
)


def _clip(text: str, limit: int = 3900) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - 80].rsplit("\n", 1)[0]
    return cut + "\n… truncated · full view: hermes context-lens session <id>"


def _parse_days(value: Any, default: int = 7) -> int:
    try:
        days = int(value)
    except (TypeError, ValueError):
        return default
    return days if days >= 0 else default


def handle_slash(raw_args: str, *, session_id: str = "", platform: str = "", **_: Any) -> str:
    """`/lens` — works in CLI, TUI, Desktop and every gateway platform."""
    words = (raw_args or "").split()
    mode = words[0].lower() if words else ""
    if mode in {"help", "?", "-h", "--help"}:
        return _USAGE

    try:
        with Analyzer() as analyzer:
            if mode in {"overview", "stats", "insights"}:
                days = _parse_days(words[1], 7) if len(words) > 1 else 7
                report = analyzer.overview(days=days)
                return _clip(format_overview(report))
            if mode == "session" and len(words) > 1:
                detail = analyzer.session(words[1])
                return _clip(format_session(detail, compact=False))
            target = session_id or None
            detail = analyzer.session(target)
            return _clip(format_session(detail, compact=(mode != "full")))
    except KeyError as exc:
        return f"Context Lens: {exc}"
    except FileNotFoundError as exc:
        return f"Context Lens: {exc}"
    except Exception as exc:  # never break the chat with a diagnostics command
        return f"Context Lens error: {type(exc).__name__}: {exc}"


def _setup(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--db", default=None, help="Path to state.db (default: active Hermes profile)")
    commands = subparser.add_subparsers(dest="lens_command")

    overview = commands.add_parser("overview", help="Cross-session usage dashboard")
    overview.add_argument("--days", type=int, default=30, help="Window in days (0 = all time)")
    overview.add_argument("--source", default=None, help="Filter by platform (telegram, cli, ...)")
    overview.add_argument("--all", action="store_true", help="Include archived sessions")
    overview.add_argument("--json", action="store_true", help="Emit JSON")
    overview.add_argument("--width", type=int, default=78, help=argparse.SUPPRESS)

    session = commands.add_parser("session", help="Inspect one session")
    session.add_argument("session_id", nargs="?", help="Session id (default: latest)")
    session.add_argument("--json", action="store_true", help="Emit JSON")
    session.add_argument("--compact", action="store_true", help="Short form")

    dashboard = commands.add_parser("dashboard", help="Where to open the visual tab")
    dashboard.set_defaults(lens_command="dashboard")


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _run(args: argparse.Namespace) -> None:
    command = getattr(args, "lens_command", None) or "overview"
    if command == "dashboard":
        print("Open the Context Lens tab in the Hermes dashboard:")
        print("  hermes dashboard")
        print("Then choose 'Context Lens' in the sidebar (after Analytics).")
        return

    db = getattr(args, "db", None)
    try:
        with Analyzer(db) as analyzer:
            if command == "session":
                detail = analyzer.session(getattr(args, "session_id", None))
                if getattr(args, "json", False):
                    _emit(detail)
                else:
                    print(format_session(detail, compact=getattr(args, "compact", False)))
                return
            report = analyzer.overview(
                days=int(getattr(args, "days", 30) or 0),
                source=getattr(args, "source", None),
                include_archived=bool(getattr(args, "all", False)),
            )
            if getattr(args, "json", False):
                _emit(report)
            else:
                print(format_overview(report, width=int(getattr(args, "width", 78) or 78)))
    except FileNotFoundError as exc:
        print(f"Context Lens: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except KeyError as exc:
        print(f"Context Lens: {exc}", file=sys.stderr)
        raise SystemExit(2)


def register_cli(ctx: Any) -> None:
    ctx.register_cli_command(
        name="context-lens",
        help="Context insight: token composition, trends, skills/tools/commands",
        setup_fn=_setup,
        handler_fn=_run,
    )
