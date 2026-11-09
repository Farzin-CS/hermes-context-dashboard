"""Unit tests for Context Lens (stdlib unittest, synthetic state DB)."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import lens_core  # noqa: E402
from lens_render import format_overview, format_session  # noqa: E402

SCHEMA = """
CREATE TABLE system_prompts (hash TEXT PRIMARY KEY, prompt TEXT NOT NULL);
CREATE TABLE sessions (
    id TEXT PRIMARY KEY, source TEXT NOT NULL, created_source TEXT, title TEXT,
    model TEXT, cwd TEXT, started_at REAL NOT NULL, ended_at REAL,
    last_activity_at REAL, message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0, api_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0, cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0, estimated_cost_usd REAL,
    actual_cost_usd REAL, parent_session_id TEXT, archived INTEGER DEFAULT 0,
    hidden INTEGER DEFAULT 0, profile_name TEXT, model_config TEXT,
    system_prompt TEXT, system_prompt_hash TEXT, tool_names TEXT
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
    content TEXT, tool_calls TEXT, tool_name TEXT, tool_call_id TEXT,
    timestamp REAL NOT NULL, reasoning TEXT, _compressed_summary INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
);
CREATE TABLE session_model_usage (
    session_id TEXT NOT NULL, model TEXT NOT NULL, billing_provider TEXT DEFAULT '',
    billing_base_url TEXT DEFAULT '', billing_mode TEXT DEFAULT '', task TEXT DEFAULT '',
    api_call_count INTEGER DEFAULT 0, input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0, cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0, reasoning_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0, actual_cost_usd REAL DEFAULT 0,
    cost_status TEXT, cost_source TEXT, first_seen REAL, last_seen REAL
);
CREATE TABLE async_delegations (
    delegation_id TEXT PRIMARY KEY, origin_session TEXT NOT NULL,
    origin_ui_session_id TEXT DEFAULT '', parent_session_id TEXT, state TEXT NOT NULL,
    dispatched_at REAL NOT NULL, completed_at REAL, updated_at REAL NOT NULL,
    event_json TEXT, result_json TEXT, delivery_state TEXT DEFAULT 'pending',
    delivery_attempts INTEGER DEFAULT 0, delivered_at REAL, owner_pid INTEGER,
    owner_started_at INTEGER, task_json TEXT
);
"""

SYSTEM_PROMPT = (
    "You are a test agent. " * 20
    + '<available_skills><skill name="pdf">PDF things</skill></available_skills>'
    + " Stable tail."
)
TOOLS_JSON = json.dumps([{
    "type": "function",
    "function": {
        "name": "terminal",
        "description": "Run a command",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}},
    },
}])


def _call(name: str, args: dict, call_id: str) -> dict:
    return {"id": call_id, "call_id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def make_db(path: Path) -> None:
    now = time.time() - 120
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("INSERT INTO system_prompts VALUES (?, ?)", ("sys1", SYSTEM_PROMPT))
        conn.execute("INSERT INTO system_prompts VALUES (?, ?)", ("tools1", TOOLS_JSON))
        conn.execute(
            "INSERT INTO sessions (id, source, created_source, title, model, cwd, started_at, "
            "last_activity_at, message_count, tool_call_count, api_call_count, input_tokens, "
            "output_tokens, cache_read_tokens, reasoning_tokens, estimated_cost_usd, "
            "parent_session_id, archived, hidden, profile_name, model_config, "
            "system_prompt_hash, tool_names) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s1", "telegram", "telegram", "Demo session", "deepseek-flash", "/work",
             now - 60, now, 6, 3, 3, 1000, 200, 5000, 40, 0.0123,
             None, 0, 0, "default",
             json.dumps({"_usage_anchor": {"prompt_tokens": 12345, "completion_tokens": 10}}),
             "sys1", "tools1"),
        )
        conn.execute(
            "INSERT INTO sessions (id, source, created_source, title, model, started_at, "
            "last_activity_at, message_count, tool_call_count, api_call_count, input_tokens, "
            "output_tokens, cache_read_tokens, estimated_cost_usd, parent_session_id, archived, "
            "hidden, model_config, system_prompt_hash, tool_names) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("s2", "subagent", "subagent", "Child worker", "deepseek-flash", now - 30, now - 10,
             2, 0, 1, 100, 20, 0, 0.001, "s1", 0, 0, "{}", "sys1", "tools1"),
        )
        conn.execute(
            "INSERT INTO session_model_usage (session_id, model, task, api_call_count, "
            "input_tokens, output_tokens, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?)",
            ("s1", "deepseek-flash", "", 3, 1000, 200, now - 60, now),
        )
        conn.execute(
            "INSERT INTO session_model_usage (session_id, model, task, api_call_count, "
            "input_tokens, output_tokens, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?)",
            ("s1", "deepseek-flash", "title_generation", 1, 30, 5, now - 50, now),
        )
        conn.execute(
            "INSERT INTO async_delegations (delegation_id, origin_session, state, dispatched_at, "
            "updated_at, task_json) VALUES (?,?,?,?,?,?)",
            ("d1", "s1", "completed", now - 30, now - 20, json.dumps({"goal": "Check the child"})),
        )

        def msg(role, content=None, tool_calls=None, tool_name=None, tool_call_id=None,
                reasoning=None, summary=0, ts=None):
            conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, tool_name, "
                "tool_call_id, timestamp, reasoning, _compressed_summary) VALUES (?,?,?,?,?,?,?,?,?)",
                ("s1", role, content, tool_calls, tool_name, tool_call_id,
                 ts if ts is not None else now - 55, reasoning, summary),
            )

        msg("user", "Hello <memory-context>remember this</memory-context>")
        msg("assistant", "", json.dumps([
            _call("terminal", {"command": 'cd /work && python -c "print(1)"'}, "c1"),
            _call("skill_view", {"name": "pdf"}, "c2"),
            _call("read_file", {"path": "/work/a.txt"}, "c3"),
        ]), reasoning="I should read the file first.")
        msg("tool", '{"output": "1", "exit_code": 0}', tool_name="terminal", tool_call_id="c1")
        msg("tool", '{"content": "pdf docs"}', tool_name="skill_view", tool_call_id="c2")
        msg("tool", '{"content": "file body"}', tool_name="read_file", tool_call_id="c3")
        msg("assistant", "Done.", reasoning="All set.")
        conn.commit()
    finally:
        conn.close()


class AnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "state.db"
        make_db(self.db)
        self.analyzer = lens_core.Analyzer(self.db)

    def tearDown(self) -> None:
        self.analyzer.close()
        self.tmp.cleanup()

    def test_overview_totals(self) -> None:
        report = self.analyzer.overview(days=30)
        totals = report["totals"]
        self.assertEqual(totals["sessions"], 2)
        self.assertEqual(totals["billed_tokens"], 1000 + 200 + 5000 + 100 + 20)
        self.assertAlmostEqual(totals["cost_usd"], 0.0133, places=4)
        self.assertEqual(totals["cache_hit_pct"], 82.0)
        self.assertEqual(len(report["daily"]), 30)
        self.assertEqual(len(report["heatmap"]), 56)

    def test_overview_ledgers(self) -> None:
        report = self.analyzer.overview(days=30)
        self.assertEqual(report["skills"][0]["name"], "pdf")
        self.assertEqual(report["skills"][0]["count"], 1)
        tools = {item["name"]: item for item in report["tools"]}
        self.assertEqual(tools["terminal"]["count"], 1)
        self.assertEqual(tools["terminal"]["errors"], 0)
        programs = {item["program"]: item["count"] for item in report["commands"]}
        self.assertIn("python", programs)
        self.assertEqual(programs["python"], 1)
        files = {item["path"]: item for item in report["files"]}
        self.assertEqual(files["/work/a.txt"]["read"], 1)

    def test_session_detail(self) -> None:
        detail = self.analyzer.session("s1")
        self.assertEqual(detail["context"]["used"], 12345)
        self.assertEqual(detail["context"]["source"], "provider_anchor")
        self.assertEqual(detail["stats"]["turns"], 1)
        self.assertEqual(detail["stats"]["tool_calls"], 3)
        self.assertEqual(len(detail["trend"]), 2)
        self.assertAlmostEqual(detail["trend"][-1]["tokens"], detail["composition_total"], delta=20)
        self.assertTrue(any(c["id"] == "tool_results" for c in detail["composition"]))
        self.assertTrue(any(c["id"] == "injected" for c in detail["composition"]))
        self.assertGreater(detail["composition"][4]["tokens"], 0)
        self.assertEqual(detail["fleet"]["children"][0]["id"], "s2")
        self.assertEqual(len(detail["fleet"]["delegations"]), 1)
        self.assertEqual(detail["files"][0]["path"], "/work/a.txt")
        self.assertEqual(detail["commands"][0]["program"], "python")
        self.assertEqual(detail["commands"][0]["exit_code"], 0)
        self.assertEqual(detail["skills"][0]["name"], "pdf")
        # The title-generation row must not become a model event.
        model_events = [e for e in detail["events"] if e["kind"] == "model"]
        self.assertEqual(len(model_events), 1)

    def test_parent_and_child(self) -> None:
        child = self.analyzer.session("s2")
        self.assertEqual(child["fleet"]["parent"]["id"], "s1")
        self.assertEqual(child["stats"]["turns"], 0)

    def test_unknown_session(self) -> None:
        with self.assertRaises(KeyError):
            self.analyzer.session("nope")

    def test_renderers(self) -> None:
        overview = format_overview(self.analyzer.overview(days=7))
        self.assertIn("Context Lens", overview)
        self.assertIn("Skills loaded", overview)
        detail = format_session(self.analyzer.session("s1"))
        self.assertIn("Composition", detail)
        self.assertIn("Fleet", detail)
        compact = format_session(self.analyzer.session("s1"), compact=True)
        self.assertLess(len(compact), len(detail))


class HelperTests(unittest.TestCase):
    def test_first_program_skips_shell_plumbing(self) -> None:
        cases = {
            'cd /work && python -c "print(1)"': "python",
            "export FOO=bar; git status": "git",
            "ls -la | head": "ls",
            "sudo -E env FOO=1 pytest -q": "pytest",
            "R=/tmp && echo ok": "echo",
            "sleep 2 && curl x": "curl",
            "": "",
        }
        for command, expected in cases.items():
            self.assertEqual(lens_core._first_program(command), expected, command)

    def test_exit_code_parsing(self) -> None:
        self.assertEqual(lens_core._exit_code_from_result('{"exit_code": 0}'), 0)
        self.assertEqual(lens_core._exit_code_from_result('{"exit_code": 2}'), 2)
        self.assertIsNone(lens_core._exit_code_from_result("plain output"))
        self.assertEqual(lens_core._exit_code_from_result('"exit_code": 7'), 7)

    def test_empty_overview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.db"
            conn = sqlite3.connect(db)
            try:
                conn.executescript(SCHEMA)
                conn.commit()
            finally:
                conn.close()
            with lens_core.Analyzer(db) as analyzer:
                report = analyzer.overview(days=7)
            self.assertEqual(report["totals"]["sessions"], 0)
            self.assertEqual(report["sessions"], [])
            self.assertIn("Context Lens", format_overview(report))


if __name__ == "__main__":
    unittest.main()
