# Changelog

All notable changes to Context Dashboard are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-11-12

### Added — dashboard session workspace (`patches/hermes-0.23-dashboard-full.patch`)

- **Resizable shell.** The main sidebar and the chat session panel both have a
  drag handle (pointer + keyboard + Home/End), persist their width per browser,
  and reset on double-click. Logical edges follow the document direction, so both
  handles stay on the correct side in Persian/Arabic.
- **Multi-session tabs.** The Chat tab keeps an open-conversation strip: switch,
  close (× or middle click), and start a new chat. Tabs persist across reloads
  and stay in sync with `?resume=` deep links, the Sessions page, and the rail.
- **Session rail.** Search, pinned section, calendar groups (Today / Yesterday /
  Previous 7 days / Earlier), unread dots, inline rename, and a right-click /
  overflow menu: Resume, Open in new tab, Rename, Pin/Unpin, Mark read/unread,
  Copy ID, Export, Archive, Delete. The Sessions page gets the same groups and
  context menu.
- **Chat bubbles.** Session transcripts render as message bubbles (user aligned
  to the reading edge, assistant alongside), with a compact collapsible row for
  tool results and tool-call chips.
- **Per-block RTL.** Each markdown block resolves its own direction
  (`unicode-bidi: plaintext` + `dir="auto"`); Persian/Arabic paragraphs, lists
  and quotes align right, while code, paths, JSON and the surrounding dashboard
  stay LTR. Inline and fenced code are explicitly LTR. This applies to the
  Sessions page, the new Messages view in Chat, and every other Markdown surface.
- **Messages view in Chat.** A read-only bubble transcript of the live session
  (refreshes while open, follows the tail) for reading RTL-heavy replies without
  giving up the terminal. The PTY stays mounted; "Reply in terminal" returns.
- **Full-body Persian.** The `fa` locale now covers the Sessions page stats,
  prune/import dialogs, rename/export labels, the new workspace strings, and
  relative timestamps ("۲ دقیقه پیش", "دیروز").

### Changed

- **Empty sessions clean themselves up.** A background sweep runs two minutes
  after dashboard boot and every 15 minutes thereafter. It uses the same
  transaction as the old button (skips active and archived rows, and sessions
  whose soft-archived transcript is the only copy), so drafts created by a
  fresh PTY never accumulate. The "Delete empty (N)" button is now an
  informational hint instead.
- Pinned/unread sidebar state is read from the store and exposed through the
  dashboard session API (`patchSession`).

### Fixed

- The chat side panel's width no longer collapses to a fixed 15rem column on
  desktop; its collapse toggle is unchanged.
- Session timestamps follow the active locale instead of always rendering
  English relative time.

## [0.2.0] — 2026-11-09

### Added

- Context Lens dashboard tab, `/lens` chat command, and `hermes context-lens`
  CLI: composition, trend, skills/tools/commands, file activity, fleet, context
  events.
- Optional Hermes dashboard patch: Persian locale, terminal contrast, chat
  attachments, Sessions history default, working empty-session delete, Large
  theme variants, reasoning picker/mobile fixes.

## [0.1.0] — 2026-11-09

- Initial release: context composition analyzer, session fleet, benchmarks.
