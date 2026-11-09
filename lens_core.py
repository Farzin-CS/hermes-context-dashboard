"""Context Lens — Hermes-native session/context analytics.

Reads the local Hermes state database (read-only) and turns it into the
context-insight model popularized by dsh-context: what the model carries in
its window, where the tokens went, how the window evolves, which skills /
tools / commands were used, and the agent family around a session.

Everything here is computed from local data only. No network calls, no
writes to Hermes state.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Environment / estimates
# --------------------------------------------------------------------------- #

# Kept local on purpose: the plugin uses only documented Hermes surfaces and
# its own database, not private core modules. This mirrors Hermes' rough
# estimator (ASCII bytes/4; CJK codepoints ~1 token each; everything else
# UTF-8 bytes/4) so the plugin's numbers line up with the /context command.
_CJK_DENSE_RE = re.compile(
    r"[\u1100-\u11ff\u2e80-\u9fff\ua960-\ua97f\uac00-\ud7ff\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef]"
)


def estimate_tokens(text: str | None) -> int:
    """Rough token estimate, matching Hermes' byte-aware estimator family."""
    if not text:
        return 0
    raw = str(text)
    if raw.isascii():
        return (len(raw) + 3) // 4
    stripped = _CJK_DENSE_RE.sub("", raw)
    dense = len(raw) - len(stripped)
    return dense + (len(stripped.encode("utf-8", "replace")) + 3) // 4


def estimate_bytes(size: int | None) -> int:
    """Estimate tokens from a stored byte length."""
    return (int(size or 0) + 3) // 4


_CONTEXT_WINDOWS: dict[tuple[str, str], int] = {}

# Windows for models Hermes routinely sees, used only when neither the user's
# config nor Hermes' own resolved-length cache names the model. Unknown models
# deliberately resolve to 0 ("window unknown") instead of a made-up number.
_KNOWN_WINDOWS = (
    ("deepseek-flash", 1_000_000),
    ("deepseek-v4", 1_048_576),
    ("deepseek-chat", 128_000),
    ("deepseek-reasoner", 128_000),
    ("gpt-4.1", 1_047_576),
    ("gpt-4o", 128_000),
    ("gpt-4-turbo", 128_000),
    ("gpt-3.5", 16_385),
    ("claude", 200_000),
    ("gemini", 1_048_576),
    ("qwen", 131_072),
    ("kimi", 262_144),
    ("moonshot", 262_144),
    ("glm-4", 200_000),
    ("minimax", 1_048_576),
    ("llama-3", 131_072),
    ("mistral-large", 128_000),
)


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # Hermes ships PyYAML; optional here

        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _configured_context_length(home: Path) -> int:
    cfg = _read_yaml_mapping(home / "config.yaml")
    model_cfg = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
    for key in ("context_length", "context_window"):
        try:
            value = int(model_cfg.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 0


def _cached_context_length(home: Path, model: str) -> int:
    cache = _read_yaml_mapping(home / "context_length_cache.yaml")
    lengths = cache.get("context_lengths")
    if not isinstance(lengths, dict):
        return 0
    candidates: list[int] = []
    for key, value in lengths.items():
        if not isinstance(key, str):
            continue
        bare = key.split("@", 1)[0]
        if bare == model or key == model:
            try:
                number = int(value or 0)
            except (TypeError, ValueError):
                continue
            if number > 0:
                candidates.append(number)
    return max(candidates) if candidates else 0


def context_window(model: str | None, home: Path | None = None) -> int:
    """Resolve a model's context window from config, Hermes' cache, or a
    conservative known-model table. Returns 0 when unknown."""
    model = (model or "").strip()
    if not model:
        return 0
    home = home or default_db_path().parent
    cache_key = (str(home), model)
    if cache_key in _CONTEXT_WINDOWS:
        return _CONTEXT_WINDOWS[cache_key]
    value = _configured_context_length(home) or _cached_context_length(home, model)
    if not value:
        lower = model.lower()
        for prefix, window in _KNOWN_WINDOWS:
            if prefix in lower:
                value = window
                break
    _CONTEXT_WINDOWS[cache_key] = int(value or 0)
    return int(value or 0)


# --------------------------------------------------------------------------- #
# Paths / database
# --------------------------------------------------------------------------- #

def default_db_path() -> Path:
    env_db = os.environ.get("CONTEXT_LENS_DB")
    if env_db:
        return Path(env_db).expanduser()
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home) / "state.db"
    try:  # Hermes runtime (profile-aware)
        from hermes_constants import get_hermes_home

        home = Path(get_hermes_home())
        if (home / "state.db").exists():
            return home / "state.db"
    except Exception:
        pass
    home = Path.home() / ".hermes"
    if (home / "state.db").exists():
        return home / "state.db"
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "hermes" / "state.db"
        if candidate.exists():
            return candidate
    return home / "state.db"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else default_db_path()
    if not path.exists():
        raise FileNotFoundError(f"Hermes state database not found: {path}")
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=3000")
    return conn


# --------------------------------------------------------------------------- #
# Categories
# --------------------------------------------------------------------------- #

CATEGORIES: list[dict[str, str]] = [
    {"id": "system", "label": "System prompt", "color": "#6366f1", "glyph": "■"},
    {"id": "tools", "label": "Tool definitions", "color": "#f59e0b", "glyph": "▣"},
    {"id": "skills", "label": "Skills index", "color": "#f97316", "glyph": "▤"},
    {"id": "user", "label": "User messages", "color": "#22c55e", "glyph": "▨"},
    {"id": "injected", "label": "Injected context", "color": "#a855f7", "glyph": "▧"},
    {"id": "assistant", "label": "Assistant replies", "color": "#3b82f6", "glyph": "▪"},
    {"id": "thinking", "label": "Reasoning", "color": "#8b5cf6", "glyph": "▫"},
    {"id": "tool_calls", "label": "Tool calls", "color": "#14b8a6", "glyph": "▥"},
    {"id": "tool_results", "label": "Tool results", "color": "#0ea5e9", "glyph": "▦"},
]
_CATEGORY_BY_ID = {c["id"]: c for c in CATEGORIES}
_CATEGORY_IDS = tuple(_CATEGORY_BY_ID)

_SKILLS_RE = re.compile(r"<available_skills>.*?</available_skills>", re.DOTALL)
_MEMORY_RE = re.compile(r"<memory-context>.*?</memory-context>", re.DOTALL)

FILE_READ_TOOLS = {"read_file"}
FILE_WRITE_TOOLS = {"write_file"}
FILE_EDIT_TOOLS = {"patch", "file_edit", "edit_file", "apply_patch"}
SHELL_TOOLS = {"terminal"}
CODE_TOOLS = {"execute_code"}


def _empty_categories() -> dict[str, int]:
    return {cid: 0 for cid in _CATEGORY_IDS}


def _category_list(tokens: dict[str, int]) -> list[dict[str, Any]]:
    out = []
    for meta in CATEGORIES:
        value = int(tokens.get(meta["id"], 0))
        if value <= 0:
            continue
        out.append({**meta, "tokens": value})
    return out


# --------------------------------------------------------------------------- #
# Small parsing helpers
# --------------------------------------------------------------------------- #

def _json_load(value: Any, kind: type) -> Any:
    if isinstance(value, kind):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, kind) else None


def iter_tool_calls(raw: Any) -> Iterable[tuple[str, dict[str, Any], str]]:
    """Yield (name, args, call_id) from a stored assistant tool_calls blob."""
    calls = _json_load(raw, list) or []
    for call in calls:
        if not isinstance(call, dict):
            continue
        fn = call.get("function")
        if not isinstance(fn, dict):
            fn = call
        name = str(fn.get("name") or "").strip()
        if not name:
            continue
        args = fn.get("arguments")
        if isinstance(args, str):
            args = _json_load(args, dict) or {}
        if not isinstance(args, dict):
            args = {}
        call_id = str(call.get("call_id") or call.get("id") or "")
        yield name, args, call_id


def _first_program(command: str) -> str:
    """Best-effort program name from a shell command line.

    Walks the chain (`cd x && python y`) and skips shell plumbing so the
    ledger counts the program that actually did the work.
    """
    text = (command or "").strip()
    if not text:
        return ""
    noise = {
        "cd", "export", "set", "unset", "source", ".", "echo", "printf", "sleep",
        "true", "false", "test", "[", "]", "read", "shift", "wait", "trap",
        "pushd", "popd", "umask", "local", "declare", "typeset",
    }
    segments = re.split(r"&&|\|\||;|\n|\|", text)
    fallback = ""
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$", segment):
            continue
        probe = segment
        while probe:
            m = re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S*\s+", probe)
            if m:
                probe = probe[m.end():].strip()
                continue
            m = re.match(r"^(?:sudo|time|command|exec|nohup|env)\s+(?:-\S+\s+)*", probe)
            if m:
                probe = probe[m.end():].strip()
                continue
            break
        if not probe:
            continue
        token = probe.split()[0].strip("\"'")
        if token.startswith(("/", "./", "../", "~/")):
            token = token.rstrip("/").split("/")[-1]
        if not fallback:
            fallback = token
        if token.lower() in noise or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            continue
        return token[:48]
    return fallback[:48]


def _exit_code_from_result(content: Any) -> int | None:
    text = content
    if isinstance(text, (dict, list)):
        text = json.dumps(text, ensure_ascii=False)
    if not isinstance(text, str):
        return None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            for key in ("exit_code", "exitCode", "returncode", "code"):
                value = payload.get(key)
                if isinstance(value, int) and not isinstance(value, bool):
                    return value
    except (ValueError, TypeError):
        pass
    m = re.search(r'"?exit_code"?\s*[:=]\s*(-?\d+)', text)
    return int(m.group(1)) if m else None


def _day_key(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _iso(ts: float | None) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(float(ts)).astimezone().isoformat(timespec="seconds")
    except (ValueError, OSError, OverflowError):
        return ""


def _chunks(values: list[str], size: int = 500):
    """Yield id chunks so an IN(...) never crosses SQLite's variable cap."""
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _clean_title(title: str | None) -> str:
    text = " ".join(str(title or "").split())
    return text[:120]


# --------------------------------------------------------------------------- #
# Analyzer
# --------------------------------------------------------------------------- #

_SESSION_COLUMNS = """
    s.id, s.source, s.created_source, s.title, s.model, s.cwd,
    s.started_at, s.ended_at, s.last_activity_at,
    s.message_count, s.tool_call_count, s.api_call_count,
    s.input_tokens, s.output_tokens, s.cache_read_tokens, s.cache_write_tokens,
    s.reasoning_tokens, s.estimated_cost_usd, s.actual_cost_usd,
    s.parent_session_id, s.archived, s.hidden, s.profile_name, s.model_config,
    COALESCE(sp.prompt, s.system_prompt) AS system_prompt,
    COALESCE(tp.prompt, s.tool_names) AS tools_json
"""


class Analyzer:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.conn = connect(self.db_path)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def __enter__(self) -> "Analyzer":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ---------------------------- session queries ------------------------- #

    def _session_rows(
        self,
        days: int | None,
        source: str | None = None,
        include_archived: bool = False,
        fetch_days: int | None = None,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[Any] = []
        window = fetch_days if fetch_days is not None else days
        if window:
            cutoff = time.time() - window * 86400
            clauses.append(
                "(COALESCE(s.last_activity_at, s.ended_at, s.started_at) >= ? OR s.started_at >= ?)"
            )
            params += [cutoff, cutoff]
        if not include_archived:
            clauses.append("COALESCE(s.archived, 0) = 0")
        if source:
            clauses.append("(s.source = ? OR (s.source = 'local' AND s.created_source = ?))")
            params += [source, source]
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            f"SELECT {_SESSION_COLUMNS} FROM sessions s "
            "LEFT JOIN system_prompts sp ON sp.hash = s.system_prompt_hash "
            "LEFT JOIN system_prompts tp ON tp.hash = s.tool_names"
            f"{where} ORDER BY COALESCE(s.last_activity_at, s.started_at) DESC"
        )
        return list(self.conn.execute(sql, params))

    def latest_session(self) -> sqlite3.Row | None:
        row = self.conn.execute(
            f"SELECT {_SESSION_COLUMNS} FROM sessions s "
            "LEFT JOIN system_prompts sp ON sp.hash = s.system_prompt_hash "
            "LEFT JOIN system_prompts tp ON tp.hash = s.tool_names "
            "WHERE COALESCE(s.hidden, 0) = 0 "
            "ORDER BY COALESCE(s.last_activity_at, s.started_at) DESC LIMIT 1"
        ).fetchone()
        return row

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            f"SELECT {_SESSION_COLUMNS} FROM sessions s "
            "LEFT JOIN system_prompts sp ON sp.hash = s.system_prompt_hash "
            "LEFT JOIN system_prompts tp ON tp.hash = s.tool_names "
            "WHERE s.id = ?",
            (session_id,),
        ).fetchone()

    def _messages(self, session_id: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT role, content, tool_calls, tool_name, tool_call_id, timestamp, "
                "reasoning, _compressed_summary, active "
                "FROM messages WHERE session_id = ? AND role != 'session_meta' ORDER BY id",
                (session_id,),
            )
        )

    def _children(self, session_id: str) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                f"SELECT {_SESSION_COLUMNS} FROM sessions s "
                "LEFT JOIN system_prompts sp ON sp.hash = s.system_prompt_hash "
                "LEFT JOIN system_prompts tp ON tp.hash = s.tool_names "
                "WHERE s.parent_session_id = ? "
                "ORDER BY COALESCE(s.started_at, 0) DESC",
                (session_id,),
            )
        )

    # ---------------------------- composition ----------------------------- #

    @staticmethod
    def _prompt_parts(row: sqlite3.Row) -> tuple[str, int, int]:
        prompt = row["system_prompt"] or ""
        skills_match = _SKILLS_RE.search(prompt)
        skills = skills_match.group(0) if skills_match else ""
        system = prompt.replace(skills, "") if skills else prompt
        tools = row["tools_json"] or ""
        return system, skills, tools

    def _message_categories(self, messages: list[sqlite3.Row]) -> dict[str, int]:
        tokens = _empty_categories()
        for msg in messages:
            role = msg["role"]
            content = msg["content"] or ""
            if role == "user":
                memory = "".join(_MEMORY_RE.findall(content))
                tokens["injected"] += estimate_tokens(memory)
                tokens["user"] += max(0, estimate_tokens(content) - estimate_tokens(memory))
            elif role == "assistant":
                tokens["assistant"] += estimate_tokens(content)
                tokens["thinking"] += estimate_tokens(msg["reasoning"] or "")
                tokens["tool_calls"] += estimate_tokens(msg["tool_calls"] or "")
            elif role == "tool":
                tokens["tool_results"] += estimate_tokens(content)
        return tokens

    def _composition(self, row: sqlite3.Row, messages: list[sqlite3.Row] | None = None) -> dict[str, int]:
        system, skills, tools = self._prompt_parts(row)
        tokens = _empty_categories()
        tokens["system"] = estimate_tokens(system)
        tokens["skills"] = estimate_tokens(skills)
        tokens["tools"] = estimate_tokens(tools)
        if messages is None:
            # Lightweight aggregate for overview: byte lengths, user content split.
            sid = row["id"]
            agg = self.conn.execute(
                "SELECT role, "
                "SUM(LENGTH(CAST(COALESCE(content,'') AS BLOB))) AS clen, "
                "SUM(LENGTH(CAST(COALESCE(tool_calls,'') AS BLOB))) AS tclen, "
                "SUM(LENGTH(CAST(COALESCE(reasoning,'') AS BLOB))) AS rlen "
                "FROM messages WHERE session_id = ? AND role IN ('assistant','tool') GROUP BY role",
                (sid,),
            ).fetchall()
            for group in agg:
                role = group["role"]
                if role == "assistant":
                    tokens["assistant"] += estimate_bytes(group["clen"])
                    tokens["thinking"] += estimate_bytes(group["rlen"])
                    tokens["tool_calls"] += estimate_bytes(group["tclen"])
                elif role == "tool":
                    tokens["tool_results"] += estimate_bytes(group["clen"])
            for user_row in self.conn.execute(
                "SELECT content FROM messages WHERE session_id = ? AND role = 'user'", (sid,)
            ):
                content = user_row["content"] or ""
                memory = "".join(_MEMORY_RE.findall(content))
                tokens["injected"] += estimate_tokens(memory)
                tokens["user"] += max(0, estimate_tokens(content) - estimate_tokens(memory))
        else:
            for cid, value in self._message_categories(messages).items():
                tokens[cid] += value
        return tokens

    def _context_figures(self, row: sqlite3.Row, composition: dict[str, int]) -> dict[str, Any]:
        estimate = sum(composition.values())
        used = 0
        anchor = None
        try:
            cfg = _json_load(row["model_config"], dict) or {}
            anchor = cfg.get("_usage_anchor")
            if isinstance(anchor, dict):
                used = int(anchor.get("prompt_tokens") or 0)
        except Exception:
            used = 0
        source = "provider_anchor" if used > 0 else "estimate"
        if used <= 0:
            used = estimate
        maximum = context_window(row["model"])
        if maximum and used > maximum:
            used = maximum
        return {
            "used": int(used),
            "max": int(maximum or 0),
            "pct": round(used / maximum * 100, 1) if maximum else 0.0,
            "headroom": max(0, maximum - used) if maximum else 0,
            "source": source,
            "estimate": int(estimate),
            "anchor": anchor if isinstance(anchor, dict) else None,
        }

    def _session_brief(self, row: sqlite3.Row, composition: dict[str, int] | None = None) -> dict[str, Any]:
        composition = composition if composition is not None else self._composition(row)
        context = self._context_figures(row, composition)
        total_tokens = (
            int(row["input_tokens"] or 0)
            + int(row["output_tokens"] or 0)
            + int(row["cache_read_tokens"] or 0)
            + int(row["cache_write_tokens"] or 0)
        )
        cost = row["actual_cost_usd"] if row["actual_cost_usd"] is not None else row["estimated_cost_usd"]
        return {
            "id": row["id"],
            "title": _clean_title(row["title"]),
            "source": row["source"] or "",
            "model": row["model"] or "",
            "started_at": float(row["started_at"] or 0),
            "last_activity_at": float(row["last_activity_at"] or row["ended_at"] or row["started_at"] or 0),
            "ended": bool(row["ended_at"]),
            "message_count": int(row["message_count"] or 0),
            "tool_call_count": int(row["tool_call_count"] or 0),
            "api_call_count": int(row["api_call_count"] or 0),
            "input_tokens": int(row["input_tokens"] or 0),
            "output_tokens": int(row["output_tokens"] or 0),
            "cache_read_tokens": int(row["cache_read_tokens"] or 0),
            "cache_write_tokens": int(row["cache_write_tokens"] or 0),
            "reasoning_tokens": int(row["reasoning_tokens"] or 0),
            "tokens": total_tokens,
            "cost_usd": float(cost or 0.0),
            "cost_estimated": row["actual_cost_usd"] is None,
            "parent_session_id": row["parent_session_id"] or "",
            "archived": bool(row["archived"]),
            "hidden": bool(row["hidden"]),
            "profile": row["profile_name"] or "",
            "context": context,
            "composition": _category_list(composition),
            "composition_total": int(sum(composition.values())),
        }

    # ---------------------------- overview -------------------------------- #

    def overview(
        self,
        days: int = 30,
        source: str | None = None,
        include_archived: bool = False,
        now: float | None = None,
    ) -> dict[str, Any]:
        now = now or time.time()
        range_days = max(0, int(days or 0))
        fetch_days = max(range_days, 56) if range_days else None
        rows = self._session_rows(
            days=range_days or None,
            source=source,
            include_archived=include_archived,
            fetch_days=fetch_days,
        )
        sessions_by_id = {row["id"]: row for row in rows}
        ids = list(sessions_by_id)
        if not ids:
            return self._empty_overview(range_days, source, now)

        cutoff = now - range_days * 86400 if range_days else 0.0

        # ---- per-message timestamps for daily attribution -----------------
        assistant_ts: dict[str, list[float]] = defaultdict(list)
        user_ts: dict[str, list[float]] = defaultdict(list)
        tool_ts: dict[str, list[float]] = defaultdict(list)
        active_ms: dict[str, int] = defaultdict(int)
        last_ts: dict[str, float] = {}
        for chunk in _chunks(ids):
            ph = ",".join("?" for _ in chunk)
            for msg in self.conn.execute(
                f"SELECT session_id, role, timestamp FROM messages "
                f"WHERE session_id IN ({ph}) AND role IN ('user','assistant','tool') "
                "ORDER BY session_id, id",
                chunk,
            ):
                ts = float(msg["timestamp"] or 0)
                if ts <= 0:
                    continue
                sid = msg["session_id"]
                if msg["role"] == "assistant":
                    assistant_ts[sid].append(ts)
                elif msg["role"] == "user":
                    user_ts[sid].append(ts)
                else:
                    tool_ts[sid].append(ts)
                if cutoff and ts < cutoff:
                    continue
                prev = last_ts.get(sid)
                if prev:
                    gap = ts - prev
                    if 0 < gap <= 300:
                        active_ms[sid] += int(gap * 1000)
                    elif gap > 300:
                        active_ms[sid] += 60_000
                else:
                    active_ms[sid] += 60_000
                last_ts[sid] = ts

        # ---- ledger: skills / commands / files ----------------------------
        skill_counts: Counter[str] = Counter()
        skill_last: dict[str, float] = {}
        cmd_counts: Counter[str] = Counter()
        cmd_last: dict[str, float] = {}
        file_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"read": 0, "write": 0, "edit": 0, "touches": 0})
        tool_names_by_call: dict[str, str] = {}
        for chunk in _chunks(ids):
            ph = ",".join("?" for _ in chunk)
            for row in self.conn.execute(
                f"SELECT session_id, timestamp, tool_calls FROM messages "
                f"WHERE session_id IN ({ph}) AND role = 'assistant' "
                "AND tool_calls IS NOT NULL AND tool_calls != ''",
                chunk,
            ):
                ts = float(row["timestamp"] or 0)
                if cutoff and ts < cutoff:
                    continue
                for name, args, call_id in iter_tool_calls(row["tool_calls"]):
                    if call_id:
                        tool_names_by_call[call_id] = name
                    if name == "skill_view":
                        skill = str(args.get("name") or "").strip()
                        if skill:
                            skill_counts[skill] += 1
                            skill_last[skill] = max(skill_last.get(skill, 0), ts)
                    elif name in SHELL_TOOLS:
                        command = str(args.get("command") or "")
                        program = _first_program(command)
                        if program:
                            cmd_counts[program] += 1
                            cmd_last[program] = max(cmd_last.get(program, 0), ts)
                    elif name in CODE_TOOLS:
                        cmd_counts["python (code)"] += 1
                        cmd_last["python (code)"] = max(cmd_last.get("python (code)", 0), ts)
                    path = str(args.get("path") or args.get("file") or "").strip()
                    if path:
                        entry = file_counts[path]
                        if name in FILE_READ_TOOLS:
                            entry["read"] += 1
                            entry["touches"] += 1
                        elif name in FILE_WRITE_TOOLS:
                            entry["write"] += 1
                            entry["touches"] += 1
                        elif name in FILE_EDIT_TOOLS:
                            entry["edit"] += 1
                            entry["touches"] += 1

        # ---- tool execution counts + errors -------------------------------
        tool_counts: Counter[str] = Counter()
        tool_errors: Counter[str] = Counter()
        tool_last: dict[str, float] = {}
        result_by_call: dict[str, str] = {}
        for chunk in _chunks(ids):
            ph = ",".join("?" for _ in chunk)
            for row in self.conn.execute(
                f"SELECT tool_call_id, tool_name, content, timestamp FROM messages "
                f"WHERE session_id IN ({ph}) AND role = 'tool'",
                chunk,
            ):
                ts = float(row["timestamp"] or 0)
                if cutoff and ts < cutoff:
                    continue
                name = row["tool_name"] or "unknown"
                tool_counts[name] += 1
                tool_last[name] = max(tool_last.get(name, 0), ts)
                if row["tool_call_id"]:
                    result_by_call[row["tool_call_id"]] = row["content"] or ""
        for call_id, name in tool_names_by_call.items():
            code = _exit_code_from_result(result_by_call.get(call_id))
            if code not in (None, 0):
                tool_errors[name] += 1

        # ---- daily attribution -------------------------------------------
        daily: dict[str, dict[str, float]] = {}
        day_sessions: dict[str, set[str]] = defaultdict(set)

        def day_bucket(ts: float) -> dict[str, float]:
            key = _day_key(ts)
            if key not in daily:
                daily[key] = {"tokens": 0.0, "input_tokens": 0.0, "output_tokens": 0.0,
                              "cache_read_tokens": 0.0, "cost_usd": 0.0, "turns": 0.0,
                              "tool_calls": 0.0}
            return daily[key]

        for sid, row in sessions_by_id.items():
            points = assistant_ts.get(sid) or [float(row["started_at"] or 0)]
            points = [p for p in points if p > 0]
            if not points:
                continue
            n = len(points)
            inp = float(row["input_tokens"] or 0) / n
            out = float(row["output_tokens"] or 0) / n
            cache = float(row["cache_read_tokens"] or 0) / n
            cost = float((row["actual_cost_usd"] if row["actual_cost_usd"] is not None
                          else row["estimated_cost_usd"]) or 0) / n
            for ts in points:
                bucket = day_bucket(ts)
                bucket["input_tokens"] += inp
                bucket["output_tokens"] += out
                bucket["cache_read_tokens"] += cache
                bucket["tokens"] += inp + out + cache
                bucket["cost_usd"] += cost
                day_sessions[_day_key(ts)].add(sid)
            for ts in user_ts.get(sid, []):
                day_bucket(ts)["turns"] += 1
            for ts in tool_ts.get(sid, []):
                day_bucket(ts)["tool_calls"] += 1

        # ---- sessions in range + compositions -----------------------------
        in_range: list[sqlite3.Row] = []
        for row in rows:
            last = float(row["last_activity_at"] or row["ended_at"] or row["started_at"] or 0)
            if cutoff and last < cutoff:
                continue
            in_range.append(row)

        briefs: list[dict[str, Any]] = []
        composition_total = _empty_categories()
        for row in in_range:
            composition = self._composition(row)
            for cid, value in composition.items():
                composition_total[cid] += value
            briefs.append(self._session_brief(row, composition))

        # ---- KPI ----------------------------------------------------------
        range_days_keys = {
            key for key in daily
            if not cutoff or datetime.strptime(key, "%Y-%m-%d").timestamp() + 86400 > cutoff
        }
        tokens = sum(daily[k]["tokens"] for k in range_days_keys)
        input_tokens = sum(daily[k]["input_tokens"] for k in range_days_keys)
        output_tokens = sum(daily[k]["output_tokens"] for k in range_days_keys)
        cache_read = sum(daily[k]["cache_read_tokens"] for k in range_days_keys)
        cost = sum(daily[k]["cost_usd"] for k in range_days_keys)
        turns = int(sum(daily[k]["turns"] for k in range_days_keys))
        tool_calls = int(sum(daily[k]["tool_calls"] for k in range_days_keys))
        active_seconds = int(sum(active_ms.values()) / 1000)

        # ---- charts -------------------------------------------------------
        chart_days = range_days if range_days and range_days <= 90 else 30
        daily_series = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for offset in range(chart_days - 1, -1, -1):
            key = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
            bucket = daily.get(key, {})
            daily_series.append({
                "date": key,
                "tokens": int(round(bucket.get("tokens", 0))),
                "cost_usd": round(float(bucket.get("cost_usd", 0)), 6),
                "turns": int(bucket.get("turns", 0)),
                "tool_calls": int(bucket.get("tool_calls", 0)),
            })
        heatmap = []
        for offset in range(55, -1, -1):
            key = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
            bucket = daily.get(key, {})
            heatmap.append({"date": key, "tokens": int(round(bucket.get("tokens", 0))),
                            "sessions": len(day_sessions.get(key, set()))})

        models: Counter[tuple[str, str]] = Counter()
        model_tokens: dict[tuple[str, str], int] = defaultdict(int)
        model_cost: dict[tuple[str, str], float] = defaultdict(float)
        sources: Counter[str] = Counter()
        source_tokens: Counter[str] = Counter()
        for row in in_range:
            model = row["model"] or "unknown"
            provider = row["source"] or ""
            key = (model, provider)
            models[key] += 1
            total = int(row["input_tokens"] or 0) + int(row["output_tokens"] or 0) + int(row["cache_read_tokens"] or 0)
            model_tokens[key] += total
            model_cost[key] += float((row["actual_cost_usd"] if row["actual_cost_usd"] is not None
                                      else row["estimated_cost_usd"]) or 0)
            sources[row["source"] or "unknown"] += 1
            source_tokens[row["source"] or "unknown"] += total

        cache_pct = round(cache_read / (input_tokens + cache_read) * 100, 1) if (input_tokens + cache_read) else 0.0
        cost_sessions = sum(1 for row in in_range if (row["actual_cost_usd"] or row["estimated_cost_usd"] or 0) > 0)

        return {
            "generated_at": now,
            "range": {
                "days": range_days,
                "label": f"last {range_days} days" if range_days else "all time",
                "source": source or "",
            },
            "totals": {
                "sessions": len(in_range),
                "messages": sum(int(r["message_count"] or 0) for r in in_range),
                "turns": turns,
                "tool_calls": tool_calls,
                "api_calls": sum(int(r["api_call_count"] or 0) for r in in_range),
                "input_tokens": int(round(input_tokens)),
                "output_tokens": int(round(output_tokens)),
                "cache_read_tokens": int(round(cache_read)),
                "billed_tokens": int(round(tokens)),
                "cost_usd": round(cost, 6),
                "cache_hit_pct": cache_pct,
                "active_seconds": active_seconds,
                "cost_sessions": cost_sessions,
            },
            "daily": daily_series,
            "heatmap": heatmap,
            "composition": _category_list(composition_total),
            "composition_total": int(sum(composition_total.values())),
            "skills": [
                {"name": name, "count": count, "last_ts": skill_last.get(name, 0)}
                for name, count in skill_counts.most_common(24)
            ],
            "tools": [
                {"name": name, "count": count, "errors": tool_errors.get(name, 0),
                 "last_ts": tool_last.get(name, 0)}
                for name, count in tool_counts.most_common(24)
            ],
            "commands": [
                {"program": program, "count": count, "last_ts": cmd_last.get(program, 0)}
                for program, count in cmd_counts.most_common(24)
            ],
            "files": [
                {"path": path, **counts}
                for path, counts in sorted(file_counts.items(), key=lambda kv: kv[1]["touches"], reverse=True)[:20]
            ],
            "models": [
                {"model": model, "source": src, "sessions": count,
                 "tokens": model_tokens[(model, src)], "cost_usd": round(model_cost[(model, src)], 6)}
                for (model, src), count in models.most_common(12)
            ],
            "sources": [
                {"source": src, "sessions": count, "tokens": source_tokens[src]}
                for src, count in sources.most_common(12)
            ],
            "sessions": sorted(briefs, key=lambda s: s["last_activity_at"], reverse=True),
        }

    def _empty_overview(self, days: int, source: str | None, now: float) -> dict[str, Any]:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        chart_days = days if days and days <= 90 else 30
        daily = [
            {"date": (today - timedelta(days=offset)).strftime("%Y-%m-%d"),
             "tokens": 0, "cost_usd": 0.0, "turns": 0, "tool_calls": 0}
            for offset in range(chart_days - 1, -1, -1)
        ]
        heatmap = [
            {"date": (today - timedelta(days=offset)).strftime("%Y-%m-%d"),
             "tokens": 0, "sessions": 0}
            for offset in range(55, -1, -1)
        ]
        return {
            "generated_at": now,
            "range": {"days": days, "label": f"last {days} days" if days else "all time",
                      "source": source or ""},
            "totals": {"sessions": 0, "messages": 0, "turns": 0, "tool_calls": 0, "api_calls": 0,
                       "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                       "billed_tokens": 0, "cost_usd": 0.0, "cache_hit_pct": 0.0,
                       "active_seconds": 0, "cost_sessions": 0},
            "daily": daily,
            "heatmap": heatmap,
            "composition": [],
            "composition_total": 0,
            "skills": [], "tools": [], "commands": [], "files": [], "models": [], "sources": [],
            "sessions": [],
        }

    # ---------------------------- session detail -------------------------- #

    def session(self, session_id: str | None = None) -> dict[str, Any]:
        row = self.get_session(session_id) if session_id else self.latest_session()
        if row is None:
            raise KeyError(f"Unknown session: {session_id}")
        messages = self._messages(row["id"])
        composition = self._composition(row, messages)
        brief = self._session_brief(row, composition)
        context = brief["context"]

        # ---- trend: cumulative estimated prompt at each assistant step ----
        base = composition["system"] + composition["skills"] + composition["tools"]
        running = base
        trend: list[dict[str, Any]] = []
        for msg in messages:
            role = msg["role"]
            ts = float(msg["timestamp"] or 0)
            if role == "user":
                running += estimate_tokens(msg["content"] or "")
            elif role == "assistant":
                running += estimate_tokens(msg["content"] or "")
                running += estimate_tokens(msg["reasoning"] or "")
                running += estimate_tokens(msg["tool_calls"] or "")
                trend.append({"index": len(trend) + 1, "timestamp": ts,
                              "tokens": int(running)})
            elif role == "tool":
                running += estimate_tokens(msg["content"] or "")

        # ---- events -------------------------------------------------------
        events: list[dict[str, Any]] = []
        cfg = _json_load(row["model_config"], dict) or {}
        reset_from = cfg.get("_reset_from")
        if reset_from and str(reset_from) != str(row["parent_session_id"] or ""):
            events.append({"kind": "reset", "timestamp": float(row["started_at"] or 0),
                           "label": "Session reset", "detail": f"continued from {reset_from}"})
        if row["parent_session_id"]:
            events.append({"kind": "parent", "timestamp": float(row["started_at"] or 0),
                           "label": "Continues a previous session",
                           "detail": str(row["parent_session_id"])})
        for msg in messages:
            if msg["_compressed_summary"]:
                events.append({"kind": "compaction", "timestamp": float(msg["timestamp"] or 0),
                               "label": "Compaction summary",
                               "detail": f"≈{estimate_tokens(msg['content'] or ''):,} tokens"})
        last_model = None
        for usage in self.conn.execute(
            "SELECT model, task, api_call_count, input_tokens, output_tokens, first_seen, last_seen "
            "FROM session_model_usage WHERE session_id = ? ORDER BY COALESCE(first_seen, 0)",
            (row["id"],),
        ):
            if usage["task"]:
                continue
            model = usage["model"] or "unknown"
            if model == last_model:
                continue
            last_model = model
            events.append({
                "kind": "model",
                "timestamp": float(usage["first_seen"] or 0),
                "label": f"Model {model}",
                "detail": f"{int(usage['api_call_count'] or 0)} calls · "
                          f"{int(usage['input_tokens'] or 0) + int(usage['output_tokens'] or 0):,} tokens",
            })
        events.sort(key=lambda e: e["timestamp"])

        # ---- files --------------------------------------------------------
        files: dict[str, dict[str, Any]] = {}
        commands: list[dict[str, Any]] = []
        skills: Counter[str] = Counter()
        tool_counts: Counter[str] = Counter()
        calls: list[tuple[str, dict[str, Any], str, float]] = []
        for msg in messages:
            if msg["role"] == "tool" and msg["tool_name"]:
                tool_counts[msg["tool_name"]] += 1
            if msg["role"] != "assistant" or not msg["tool_calls"]:
                continue
            ts = float(msg["timestamp"] or 0)
            for name, args, call_id in iter_tool_calls(msg["tool_calls"]):
                calls.append((name, args, call_id, ts))
                if name == "skill_view":
                    skill = str(args.get("name") or "").strip()
                    if skill:
                        skills[skill] += 1
                if name in SHELL_TOOLS or name in CODE_TOOLS:
                    command = str(args.get("command") or "") if name in SHELL_TOOLS else "<execute_code>"
                    program = _first_program(command) if name in SHELL_TOOLS else "python (code)"
                    commands.append({"timestamp": ts, "tool": name, "command": command[:400],
                                     "program": program, "call_id": call_id, "exit_code": None})
                path = str(args.get("path") or args.get("file") or "").strip()
                if path:
                    entry = files.setdefault(path, {"path": path, "read": 0, "write": 0,
                                                    "edit": 0, "touches": 0, "last_ts": 0})
                    if name in FILE_READ_TOOLS:
                        entry["read"] += 1
                    elif name in FILE_WRITE_TOOLS:
                        entry["write"] += 1
                    elif name in FILE_EDIT_TOOLS:
                        entry["edit"] += 1
                    entry["touches"] += 1
                    entry["last_ts"] = max(entry["last_ts"], ts)

        results = {
            msg["tool_call_id"]: msg["content"]
            for msg in messages
            if msg["role"] == "tool" and msg["tool_call_id"]
        }
        for cmd in commands:
            code = _exit_code_from_result(results.get(cmd["call_id"]))
            cmd["exit_code"] = code

        # ---- fleet --------------------------------------------------------
        parent = None
        if row["parent_session_id"]:
            parent_row = self.get_session(row["parent_session_id"])
            if parent_row is not None:
                parent = {"id": parent_row["id"], "title": _clean_title(parent_row["title"]),
                          "source": parent_row["source"], "model": parent_row["model"],
                          "last_activity_at": float(parent_row["last_activity_at"] or 0)}
        children = []
        for child in self._children(row["id"]):
            child_brief = self._session_brief(child)
            children.append({
                "id": child_brief["id"], "title": child_brief["title"],
                "source": child_brief["source"], "model": child_brief["model"],
                "tokens": child_brief["tokens"], "cost_usd": child_brief["cost_usd"],
                "context_pct": child_brief["context"]["pct"],
                "last_activity_at": child_brief["last_activity_at"],
                "ended": child_brief["ended"], "tool_call_count": child_brief["tool_call_count"],
            })
        delegations = []
        try:
            for d in self.conn.execute(
                "SELECT delegation_id, state, dispatched_at, completed_at, task_json, result_json "
                "FROM async_delegations WHERE origin_session = ? OR parent_session_id = ? "
                "ORDER BY dispatched_at DESC",
                (row["id"], row["id"]),
            ):
                task = _json_load(d["task_json"], dict) or {}
                delegations.append({
                    "id": d["delegation_id"], "state": d["state"],
                    "goal": str(task.get("goal") or "")[:300],
                    "dispatched_at": float(d["dispatched_at"] or 0),
                    "completed_at": float(d["completed_at"] or 0),
                })
        except sqlite3.Error:
            pass

        stats = {
            "messages": len(messages),
            "turns": sum(1 for m in messages if m["role"] == "user"),
            "steps": sum(1 for m in messages if m["role"] == "assistant"),
            "tool_calls": sum(tool_counts.values()),
            "api_calls": int(row["api_call_count"] or 0),
            "input_tokens": int(row["input_tokens"] or 0),
            "output_tokens": int(row["output_tokens"] or 0),
            "reasoning_tokens": int(row["reasoning_tokens"] or 0),
            "cache_read_tokens": int(row["cache_read_tokens"] or 0),
            "cache_write_tokens": int(row["cache_write_tokens"] or 0),
            "cost_usd": round(float((row["actual_cost_usd"] if row["actual_cost_usd"] is not None
                                     else row["estimated_cost_usd"]) or 0), 6),
            "duration_seconds": max(0, int(float(row["last_activity_at"] or 0) - float(row["started_at"] or 0))),
            "cache_hit_pct": round(
                int(row["cache_read_tokens"] or 0)
                / max(1, int(row["input_tokens"] or 0) + int(row["cache_read_tokens"] or 0)) * 100, 1),
        }

        return {
            "session": {**brief, "cwd": row["cwd"] or "", "profile": row["profile_name"] or ""},
            "stats": stats,
            "context": context,
            "composition": _category_list(composition),
            "composition_total": int(sum(composition.values())),
            "trend": trend,
            "events": events,
            "files": sorted(files.values(), key=lambda f: f["touches"], reverse=True)[:30],
            "commands": commands[-40:],
            "skills": [{"name": n, "count": c} for n, c in skills.most_common(20)],
            "tools": [{"name": n, "count": c} for n, c in tool_counts.most_common(20)],
            "fleet": {"parent": parent, "children": children, "delegations": delegations},
        }
