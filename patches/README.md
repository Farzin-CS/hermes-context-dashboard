# Optional Hermes dashboard patch

These changes belong to the **Hermes dashboard core**, not to the Context Lens plugin. The plugin works without them; apply this patch only if you want the global dashboard language picker to offer **فارسی** and want the Nous Blue terminal to use a dark background.

## What it does

- Adds a partial `fa` dashboard locale (`web/src/i18n/fa.ts`) with English fallback.
- Registers `fa` in the locale type, the i18n provider, and the endonym list.
- Adds `fa` to `RTL_LOCALES`, so the shell flips to RTL.
- Translates the main navigation labels (Files, MCP, Channels, Webhooks, Pairing, System).
- Sets the Nous Blue terminal background to `#0B1220` and its foreground to `#E6EDF7`, so the chat terminal is readable.

## Apply

Tested against Hermes **0.23.0**. Apply from a Hermes source checkout:

```bash
cd /path/to/hermes-agent
git apply /path/to/hermes-context-dashboard/patches/hermes-0.23-dashboard-fa.patch
cd web && npm run build
```

Then select **فارسی** in the dashboard language picker and `nous-blue` in the theme picker.

If `hermes update` replaces the web source or build, re-apply the patch and rebuild. The plugin's own tab needs no patch: it already follows the dashboard's global locale.
