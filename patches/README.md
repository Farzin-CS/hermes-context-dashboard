# Optional Hermes dashboard patches

These changes belong to the **Hermes dashboard core**, not to the Context Lens plugin. The plugin works without them. Choose **one** patch — they overlap:

- **`hermes-0.23-dashboard-full.patch` (recommended)** — everything below: locale/theme, the attach-only chat attachment bar, the session/theme/chat UI fixes, and the working empty-session sweep.
- **`hermes-0.23-dashboard-fa.patch`** — locale and terminal contrast only.

## Full dashboard patch

### Chat attachments

- An attach-only bar under the dashboard chat terminal: pick multiple files; they upload to the active profile's `uploads/` directory and appear as removable chips.
- Text typed in the normal TUI composer stays the prompt. Pressing **Enter** appends the `[User attached file: …]` markers and submits, so files and prompt reach the agent together.
- Images use the TUI's existing `/image` command; unsupported image types fall back to generic files.
- A dashboard-scoped upload route with a pre-parse body cap and regression tests.

### Session workspace

- **Multi-session tabs** above Chat: switch, close (× or middle click), or start a
  new conversation. Tabs persist in `localStorage` and stay in sync with
  `?resume=` deep links and the session rail.
- **Resizable panes**: the main sidebar and the chat session panel each get a
  pointer/keyboard divider (`role="separator"`, Arrow/Home/End, double-click to
  reset). Widths persist per browser; the logical edge follows the document
  direction, so RTL mirrors both handles.
- **Session rail**: search, pinned section, Today / Yesterday / Previous 7 days /
  Earlier groups, unread dots, inline rename, and a right-click / overflow menu
  (Resume, Open in new tab, Rename, Pin/Unpin, Read/unread, Copy ID, Export,
  Archive, Delete). The same groups and menu run on the Sessions page.
- **Messages view in Chat**: a read-only bubble transcript of the live session,
  refreshing every 3 s, with a jump-to-latest action and "Reply in terminal".
  The PTY stays mounted underneath, so switching views never drops the chat.
- **Per-block RTL**: every markdown block carries `dir="auto"` and
  `unicode-bidi: plaintext`; lists and quotes resolve their box direction from
  content, inline/fenced code is pinned LTR, and the dashboard shell is never
  flipped. Persian/Arabic paragraphs align right while English prose, paths and
  JSON stay LTR in the same message.
- **Persian body text**: `fa` now covers the Sessions page stats, prune/import
  dialogs, rename/export labels, the workspace strings, and relative timestamps.

### Sessions page

- The Overview tab is gone; the page opens straight into **History** (the session list with filters, search, bulk selection and delete).
- Rows are grouped by calendar day with a pinned section, unread markers and a
  context menu, and expanded transcripts render as chat bubbles.
- **Empty sessions now clean themselves up.** A background sweep runs two minutes
  after dashboard boot and every 15 minutes thereafter, using the same shared
  store transaction as single deletes (active and archived rows are skipped, as
  are sessions whose soft-archived rows are the only transcript copy). The
  "Delete empty (N)" button is replaced by an informational hint.

### Themes

- Every built-in theme now ships a **Large** variant — same palette, fonts and terminal colours, `18px` root size, `1.65` line-height and `spacious` density: Hermes Teal, Nous Blue, Midnight, Ember, Mono, Cyberpunk, Rosé.
- `largeVariant()` in `web/src/themes/presets.ts` generates them, and `_BUILTIN_DASHBOARD_THEMES` in `hermes_cli/web_server_dashboard.py` accepts the new names so the choice persists.

### Chat page

- The reasoning picker renders a portaled, viewport-clamped menu that flips above the trigger when there is no room below. Previously it used the shared `Select`, whose `absolute` listbox was clipped by the chat sidebar's scroll container, so the options never appeared.
- The terminal block reserves a strip under the xterm grid, so the floating **copy last response** button no longer sits on the TUI's last line.

### Mobile

- Chat: the attachment hint is hidden under `sm` (connection state stays), the model/tools drawer is wider, and the terminal keeps the reserved copy-button strip.
- Sessions: the stats strip becomes a 3-column grid, and the compact pagination hides on phones (the full pagination under the list remains).

## Locale/theme-only patch

- Adds a partial `fa` dashboard locale (`web/src/i18n/fa.ts`) with English fallback.
- Registers `fa` in the locale type, the i18n provider, and the endonym list.
- Adds `fa` to `RTL_LOCALES`, so the shell flips to RTL.
- Translates the main navigation labels (Files, MCP, Channels, Webhooks, Pairing, System).
- Sets the Nous Blue terminal background to `#0B1220` and its foreground to `#E6EDF7`, so the chat terminal is readable.

## Apply

Tested against Hermes **0.23.1** (patch applies cleanly on 0.23.x). Apply from a Hermes source checkout:

```bash
cd /path/to/hermes-agent
git apply /path/to/hermes-context-dashboard/patches/hermes-0.23-dashboard-full.patch
cd web && npm run build
```

Then select **فارسی** in the dashboard language picker and `nous-blue` in the theme picker. Restart the dashboard after the build.

If `hermes update` replaces the web source or build, re-apply the chosen patch and rebuild. The plugin's own tab needs no patch: it already follows the dashboard's global locale.
