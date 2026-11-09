"""Context Lens — Hermes plugin entry point.

Registers:
  * `hermes context-lens` CLI command
  * `/lens` in-session slash command (CLI, TUI, Desktop, Telegram, Discord, ...)

The visual surface is the `dashboard/` half of this package: a Context Lens
tab in `hermes dashboard`, backed by `dashboard/plugin_api.py`.
"""

from __future__ import annotations

from .lens_cli import handle_slash, register_cli


def register(ctx) -> None:
    register_cli(ctx)
    ctx.register_command(
        "lens",
        handler=handle_slash,
        description="Context lens: composition, trends, skills/tools/commands",
        args_hint="[overview [days]|full|session <id>]",
    )
