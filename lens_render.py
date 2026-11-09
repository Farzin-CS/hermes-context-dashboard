"""Terminal / chat renderers for Context Lens."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_BLOCKS = "▁▂▃▄▅▆▇█"


def fmt_int(value: Any) -> str:
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "0"


def fmt_tokens(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}B"
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 10_000:
        return f"{number / 1_000:.1f}k"
    return f"{int(number):,}"


def fmt_cost(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "$0"
    if number and number < 0.01:
        return f"${number:.4f}"
    if number < 1:
        return f"${number:.3f}"
    return f"${number:,.2f}"


def fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "0%"


def fmt_duration(seconds: Any) -> str:
    try:
        total = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "0m"
    if total >= 86400:
        return f"{total // 86400}d {total % 86400 // 3600}h"
    if total >= 3600:
        return f"{total // 3600}h {total % 3600 // 60}m"
    if total >= 60:
        return f"{total // 60}m"
    return f"{total}s"


def time_ago(ts: Any) -> str:
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        return ""
    if ts <= 0:
        return ""
    delta = max(0, int(datetime.now().timestamp() - ts))
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"


def _date_label(key: str) -> str:
    try:
        return datetime.strptime(key, "%Y-%m-%d").strftime("%b %d")
    except ValueError:
        return key


def _fit(text: str, width: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


def _bar(value: float, maximum: float, width: int = 22) -> str:
    if maximum <= 0 or value <= 0:
        return ""
    filled = max(1, int(round(value / maximum * width)))
    return "█" * min(width, filled)


def _spark(values: list[float]) -> str:
    if not values:
        return ""
    peak = max(values) or 1
    out = []
    for value in values:
        index = int(round(max(0.0, value) / peak * (len(_BLOCKS) - 1)))
        out.append(_BLOCKS[index])
    return "".join(out)


def _header(title: str) -> str:
    return f"{title}\n" + "=" * min(78, len(title) + 6)


def format_overview(report: dict[str, Any], width: int = 78) -> str:
    totals = report.get("totals") or {}
    lines = [_header(f"Context Lens - {report.get('range', {}).get('label', 'overview')}"), ""]
    lines.append(
        f"Sessions {fmt_int(totals.get('sessions'))} · Turns {fmt_int(totals.get('turns'))} · "
        f"Tool calls {fmt_int(totals.get('tool_calls'))} · Active {fmt_duration(totals.get('active_seconds'))}"
    )
    lines.append(
        f"Billed {fmt_tokens(totals.get('billed_tokens'))} tokens · "
        f"est. {fmt_cost(totals.get('cost_usd'))} · cache hit {fmt_pct(totals.get('cache_hit_pct'))}"
    )
    lines.append(
        f"In {fmt_tokens(totals.get('input_tokens'))} · Out {fmt_tokens(totals.get('output_tokens'))} · "
        f"Cache {fmt_tokens(totals.get('cache_read_tokens'))}"
    )

    daily = report.get("daily") or []
    if daily:
        lines += ["", "Usage"]
        peak = max(int(d.get("tokens") or 0) for d in daily) or 1
        for day in daily[-14:]:
            tokens = int(day.get("tokens") or 0)
            lines.append(f"  {_date_label(day.get('date', ''))}  {_bar(tokens, peak, 24):<24} {fmt_tokens(tokens)}")

    composition = report.get("composition") or []
    if composition:
        total = sum(int(c.get("tokens") or 0) for c in composition) or 1
        lines += ["", "Current context composition (estimated)"]
        for cat in sorted(composition, key=lambda c: c.get("tokens", 0), reverse=True)[:6]:
            tokens = int(cat.get("tokens") or 0)
            share = tokens / total * 100
            lines.append(f"  {cat.get('label', ''):<18} {_bar(tokens, total, 16):<16} {fmt_pct(share)}  {fmt_tokens(tokens)}")

    skills = report.get("skills") or []
    if skills:
        lines += ["", "Skills loaded"]
        for item in skills[:8]:
            lines.append(f"  {_fit(item.get('name', ''), 28):<28} {fmt_int(item.get('count')):>5}")

    tools = report.get("tools") or []
    if tools:
        lines += ["", "Tools"]
        for item in tools[:10]:
            errs = int(item.get("errors") or 0)
            suffix = f"  ({errs} err)" if errs else ""
            lines.append(f"  {_fit(item.get('name', ''), 28):<28} {fmt_int(item.get('count')):>6}{suffix}")

    commands = report.get("commands") or []
    if commands:
        lines += ["", "Commands"]
        for item in commands[:10]:
            lines.append(f"  {_fit(item.get('program', ''), 28):<28} {fmt_int(item.get('count')):>6}")

    files = report.get("files") or []
    if files:
        lines += ["", "Files"]
        for item in files[:8]:
            ops = []
            if item.get("read"):
                ops.append(f"r{item['read']}")
            if item.get("write"):
                ops.append(f"w{item['write']}")
            if item.get("edit"):
                ops.append(f"e{item['edit']}")
            lines.append(f"  {_fit(item.get('path', ''), 52):<52} {' '.join(ops)}")

    sessions = report.get("sessions") or []
    if sessions:
        lines += ["", f"Sessions ({len(sessions)})"]
        for item in sessions[:12]:
            ctx = item.get("context") or {}
            context = f"{fmt_tokens(ctx.get('used'))} ctx"
            if ctx.get("pct"):
                context += f" ({fmt_pct(ctx.get('pct'))})"
            title = _fit(item.get("title") or item.get("id", ""), 34)
            lines.append(
                f"  {item.get('id', '')[:22]:<22} {item.get('source', ''):<8} "
                f"{_fit(item.get('model', ''), 18):<18} {context:<18} {fmt_cost(item.get('cost_usd')):>8}  {title}"
            )
        if len(sessions) > 12:
            lines.append(f"  ... {len(sessions) - 12} more")

    lines += ["", "Tip: `hermes context-lens session <id>` for one session; `hermes dashboard` for the visual tab."]
    return "\n".join(lines)


def format_session(detail: dict[str, Any], compact: bool = False) -> str:
    session = detail.get("session") or {}
    stats = detail.get("stats") or {}
    context = detail.get("context") or {}
    composition = detail.get("composition") or []
    total = sum(int(c.get("tokens") or 0) for c in composition) or 1

    title = _fit(session.get("title") or "(untitled)", 70)
    head = "Context Lens"
    if compact:
        lines = [f"{head} · {session.get('id', '')[:22]}", title,
                 f"{session.get('source', '')} · {session.get('model', '')} · {time_ago(session.get('last_activity_at'))}"]
    else:
        lines = [_header(f"{head} - session {session.get('id', '')}"), title, ""]
        lines.append(
            f"{session.get('source', '')} · {session.get('model', '')} · "
            f"{'ended' if session.get('ended') else 'active'} · started {time_ago(session.get('started_at'))}"
        )

    used = int(context.get("used") or 0)
    maximum = int(context.get("max") or 0)
    pct = float(context.get("pct") or 0)
    if maximum:
        gauge_width = 24
        filled = max(0, min(gauge_width, int(round(pct / 100 * gauge_width))))
        gauge = "█" * filled + "░" * (gauge_width - filled)
        lines.append(f"Context [{gauge}] {fmt_tokens(used)} / {fmt_tokens(maximum)} ({fmt_pct(pct)})")
        if not compact:
            lines.append(f"  headroom {fmt_tokens(context.get('headroom'))} · source {context.get('source')}")
    else:
        lines.append(f"Context {fmt_tokens(used)} (window unknown)")

    lines.append(
        f"Usage  in {fmt_tokens(stats.get('input_tokens'))} · out {fmt_tokens(stats.get('output_tokens'))} · "
        f"cache {fmt_tokens(stats.get('cache_read_tokens'))} ({fmt_pct(stats.get('cache_hit_pct'))} hit) · "
        f"{fmt_cost(stats.get('cost_usd'))}"
    )
    if compact:
        lines.append(
            f"Calls  {fmt_int(stats.get('api_calls'))} API · {fmt_int(stats.get('messages'))} messages · "
            f"{fmt_int(stats.get('turns'))} turns · {fmt_int(stats.get('tool_calls'))} tools"
        )
    else:
        lines.append(
            f"Calls  {fmt_int(stats.get('api_calls'))} API · {fmt_int(stats.get('messages'))} messages · "
            f"{fmt_int(stats.get('turns'))} turns · {fmt_int(stats.get('tool_calls'))} tool calls · "
            f"thinking {fmt_tokens(stats.get('reasoning_tokens'))}"
        )

    if composition:
        lines += ["", "Composition (estimated)"]
        ordered = sorted(composition, key=lambda c: c.get("tokens", 0), reverse=True)
        shown = ordered if not compact else ordered[:6]
        for cat in shown:
            tokens = int(cat.get("tokens") or 0)
            share = tokens / total * 100
            bar_width = 12 if compact else 18
            lines.append(
                f"  {_fit(cat.get('label', ''), 18):<18} {_bar(tokens, total, bar_width):<{bar_width}} "
                f"{fmt_pct(share):>6}  {fmt_tokens(tokens)}"
            )

    trend = detail.get("trend") or []
    if trend and not compact:
        lines += ["", f"Context trend ({len(trend)} steps, estimated)"]
        values = [int(p.get("tokens") or 0) for p in trend]
        lines.append(f"  {_spark(values[-40:])}")
        last = trend[-1]
        lines.append(f"  {fmt_tokens(last.get('tokens'))} at step {last.get('index')} · "
                     f"peak {fmt_tokens(max(values) if values else 0)}")

    skills = detail.get("skills") or []
    if skills:
        lines += ["", "Skills loaded"]
        for item in skills[:8]:
            lines.append(f"  {_fit(item.get('name', ''), 30):<30} {fmt_int(item.get('count')):>4}")

    files = detail.get("files") or []
    if files and not compact:
        lines += ["", "File activity"]
        for item in files[:8]:
            ops = []
            if item.get("read"):
                ops.append(f"r{item['read']}")
            if item.get("write"):
                ops.append(f"w{item['write']}")
            if item.get("edit"):
                ops.append(f"e{item['edit']}")
            lines.append(f"  {_fit(item.get('path', ''), 56):<56} {' '.join(ops)}")

    commands = detail.get("commands") or []
    if commands and not compact:
        lines += ["", "Commands (recent)"]
        for cmd in commands[-8:]:
            code = cmd.get("exit_code")
            mark = "" if code in (None, 0) else f"  exit {code}"
            lines.append(f"  {_fit(cmd.get('command') or cmd.get('program', ''), 64):<64}{mark}")

    events = detail.get("events") or []
    if events and not compact:
        lines += ["", "Context events"]
        for event in events[-8:]:
            stamp = ""
            if event.get("timestamp"):
                stamp = datetime.fromtimestamp(event["timestamp"]).strftime("%b %d %H:%M")
            detail_text = f" · {event.get('detail')}" if event.get("detail") else ""
            lines.append(f"  {stamp:<12} {event.get('label', '')}{detail_text}")

    fleet = detail.get("fleet") or {}
    children = fleet.get("children") or []
    parent = fleet.get("parent")
    if parent or children:
        lines += ["", "Fleet"]
        if parent:
            lines.append(f"  parent  {parent.get('id', '')[:22]}  {_fit(parent.get('title', ''), 40)}")
        for child in children[:6]:
            lines.append(
                f"  child   {child.get('id', '')[:22]}  {_fit(child.get('title', ''), 30):<30} "
                f"{fmt_tokens(child.get('tokens')):>8}  ctx {fmt_pct(child.get('context_pct'))}"
            )

    if compact:
        lines += ["", "Full view: /lens full  ·  overview: /lens overview"]
    return "\n".join(lines)
