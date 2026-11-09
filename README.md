# Context Lens

**Context insight for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — see what your agent is carrying, where it came from, and how it changes.**

Context Lens is a Hermes-native take on the context dashboard idea from
[`dsh-context`](https://github.com/bowenliang123/dsh-context) (DeepSeek Harness).
It does not port DSH code or depend on its runtime: it reads Hermes' own
`state.db`, so it works on every session Hermes has already recorded — no
instrumentation, no extra logging, no network.

```
Context Lens - last 30 days
=================================

Sessions 42 · Turns 318 · Tool calls 2,914 · Active 9h 12m
Billed 184.6M tokens · est. $4.21 · cache hit 93.8%
In 21.4M · Out 1.9M · Cache 161.3M

Usage
  Nov 03  ███████                  18.4M
  Nov 04  ████████████████████     51.2M
  ...

Current context composition (estimated)
  Tool results       ██████           36.2%  2.4M
  Reasoning          ███              20.7%  1.3M
  Tool definitions   ███              15.9%  1.0M
  ...

Sessions (42)
  20261109_0542  telegram  deepseek-flash  204.3k ctx (20.4%)  $0.077  ...
```

## What it gives you

| Surface | What you get |
|---|---|
| `/lens` in chat | Current session at a glance: context gauge, token split, composition, skills, fleet. Works in CLI, TUI, Desktop, Telegram, Discord, … |
| `hermes context-lens` | Cross-session dashboard in the terminal: KPI, daily usage, skills/tools/commands, file activity, session list. `--json` for scripts. |
| `hermes dashboard` → **Context Lens** | Visual tab: KPI cards, daily chart, 8-week activity heatmap, composition donut, skill/tool/command ledgers, session table, full session detail with context trend, files, commands, events and the agent fleet. |
| English / فارسی toggle | The dashboard tab ships an RTL Persian UI alongside English. |

### Session detail

```bash
hermes context-lens session              # latest session
hermes context-lens session <session-id> # any recorded session
hermes context-lens session --json       # machine-readable
```

The detail view covers:

- **Context window** — provider-anchored prompt size when Hermes recorded one
  (`model_config._usage_anchor`), otherwise an estimate; resolved against the
  model's real window.
- **Composition** — system prompt, tool schemas, skills index, user messages,
  injected context, assistant replies, reasoning, tool calls, tool results.
- **Trend** — estimated prompt size at every assistant step.
- **Events** — session resets, parent continuation, compaction summaries, model
  changes.
- **File activity** — reads / writes / edits per path.
- **Commands** — shell and code executions with exit codes when the tool result
  recorded one.
- **Fleet** — parent session, child sessions, and async delegations.

## Install

From GitHub (after the repo is public):

```bash
hermes plugins install Farzin-CS/hermes-context-lens --enable
```

Manual install:

```bash
git clone https://github.com/Farzin-CS/hermes-context-lens \
  ~/.hermes/plugins/context-lens
hermes plugins enable context-lens
```

On Windows the default Hermes home is `%LOCALAPPDATA%\hermes`; the plugin
directory is `%LOCALAPPDATA%\hermes\plugins\context-lens`.

Then open the dashboard tab:

```bash
hermes dashboard
```

The **Context Lens** tab appears after **Analytics**. In chat, type `/lens`.

## Usage

```bash
# last 30 days (default)
hermes context-lens

# a window, a platform, archived sessions
hermes context-lens overview --days 7
hermes context-lens overview --days 30 --source telegram
hermes context-lens overview --days 0            # all time
hermes context-lens overview --all --json

# one session
hermes context-lens session 20261109_054212_2be8a15c

# another profile's database
hermes context-lens --db /path/to/state.db overview
```

Chat commands:

```text
/lens                  current session, compact
/lens full             full session view
/lens overview         cross-session dashboard (7 days)
/lens overview 30      30-day window
/lens session <id>     another session
```

## How the numbers are produced

Context Lens reads `state.db` in **read-only** mode and never writes to it.

| Metric | Source |
|---|---|
| Sessions, messages, turns, tool calls | `sessions` / `messages` |
| Billed input / output / cache | `sessions.input_tokens`, `output_tokens`, `cache_read_tokens` |
| Cost | `estimated_cost_usd` (or `actual_cost_usd` when present) |
| Composition | Stored system prompt + tool schemas + per-message content, tokens estimated with Hermes' own `estimate_tokens_rough` |
| Current context | `model_config._usage_anchor.prompt_tokens`, else the composition estimate |
| Context window | Hermes model metadata (`get_model_context_length`) |
| Skills | `skill_view` calls |
| Commands | `terminal` / `execute_code` arguments; exit codes parsed from tool results |
| Files | `read_file` / `write_file` / `patch` arguments |
| Fleet | `sessions.parent_session_id`, `async_delegations` |

Known limits, stated rather than hidden:

- **Composition and trend are estimates.** Hermes does not persist a
  per-request token ledger for historical sessions, so categories use the same
  byte-aware estimate family as its `/context` command. The current-context
  number prefers the provider's own anchor when one exists.
- **Daily attribution is approximate.** Session totals are distributed across
  the assistant steps' timestamps; a session with one API call has one bucket.
- **Command exit codes are best-effort.** They are parsed from the stored tool
  result; a tool that never reports one shows as unknown.
- **Injected memory is not persisted** in the transcript by Hermes, so it is
  counted only when it appears inside a stored message or system prompt.
- **Archived sessions are excluded by default**; pass `--all` to include them.

## Development

No build step. Python uses the standard library; the dashboard bundle is plain
JavaScript (React comes from the dashboard SDK). PyYAML is used only when it is
already present, to read Hermes' model-length cache and config.

```bash
python -m unittest discover -s tests -v
hermes plugins doctor . --ci
```

Run the dashboard against another database (handy for demos or tests):

```bash
CONTEXT_LENS_DB=/path/to/state.db hermes dashboard --port 9123
```

## Performance

Benchmarked on a synthetic Hermes-format database: **500 sessions, 100,000 messages,
260 MB**, with Hermes' own indexes applied (they matter: without them the per-session
composition queries fall back to full scans).

| Operation | Time (Python 3.14, warm page cache) |
|---|---|
| `overview(days=30)` — 100k messages | **~1.2 s** |
| One session detail — 200 messages | **~1–2 ms** |
| SQL-only scan of all message content | ~0.53 s |
| 30k tool-call JSON parses | ~0.24 s |

The overview is dominated by SQLite reading message content for token estimates, not
by Python. A Rust/native rewrite would remove roughly the 0.7 s of Python/JSON work
while the ~0.5 s of database I/O remains — not worth the packaging cost for a plugin.
The next real scaling limit is the per-session composition query at thousands of
sessions; batching that is the optimization to make if it ever matters.

## Compatibility

- Hermes Agent **>= 0.22.0** (tested on 0.22.5 / 0.23.0).
- Uses documented plugin surfaces: `register_cli_command`, `register_command`,
  the dashboard `manifest.json` + `plugin_api.py` API.
- Python 3.10+.

## Privacy

Everything is local. The plugin has no network calls and no telemetry. The
JSON output and dashboard necessarily contain session titles, working
directory paths and command lines — treat exports accordingly.

## Credits

- Inspired by [`bowenliang123/dsh-context`](https://github.com/bowenliang123/dsh-context)
  (Apache-2.0), the context dashboard for DeepSeek Harness. This is an
  independent Hermes implementation, not a code port.
- Built for [Hermes Agent](https://github.com/NousResearch/hermes-agent) by
  Nous Research.

## License

MIT — see [LICENSE](LICENSE).
