# Optional Hermes dashboard patches

These changes belong to the **Hermes dashboard core**, not to the Context Lens plugin. The plugin works without them. Choose **one** patch — they overlap:

- **`hermes-0.23-dashboard-full.patch` (recommended)** — the locale/theme work below **plus** the attach-only chat attachment bar.
- **`hermes-0.23-dashboard-fa.patch`** — locale and terminal contrast only.

## Full dashboard patch

Adds everything in the locale/theme patch, and:

- An attach-only bar under the dashboard chat terminal: pick multiple files; they upload to the active profile's `uploads/` directory and appear as removable chips.
- Text typed in the normal TUI composer stays the prompt. Pressing **Enter** appends the `[User attached file: …]` markers and submits, so files and prompt reach the agent together.
- Images use the TUI's existing `/image` command; unsupported image types fall back to generic files.
- A dashboard-scoped upload route with a pre-parse body cap and regression tests.

## Locale/theme-only patch

- Adds a partial `fa` dashboard locale (`web/src/i18n/fa.ts`) with English fallback.
- Registers `fa` in the locale type, the i18n provider, and the endonym list.
- Adds `fa` to `RTL_LOCALES`, so the shell flips to RTL.
- Translates the main navigation labels (Files, MCP, Channels, Webhooks, Pairing, System).
- Sets the Nous Blue terminal background to `#0B1220` and its foreground to `#E6EDF7`, so the chat terminal is readable.

## Apply

Tested against Hermes **0.23.0**. Apply from a Hermes source checkout:

```bash
cd /path/to/hermes-agent
git apply /path/to/hermes-context-dashboard/patches/hermes-0.23-dashboard-full.patch
cd web && npm run build
```

Then select **فارسی** in the dashboard language picker and `nous-blue` in the theme picker. Restart the dashboard after the build.

If `hermes update` replaces the web source or build, re-apply the chosen patch and rebuild. The plugin's own tab needs no patch: it already follows the dashboard's global locale.
