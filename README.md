# fnp

## macOS permissions

A few features need permissions granted manually in System Settings →
Privacy & Security. macOS does not apply a newly granted permission to a
process that is already running — quit and restart it after granting.

- **Screen Recording** — required for `system_control.screenshot_all_displays()`
  (used by the "Screenshot" button in `telegram_bot.py`). Without it,
  `CGWindowListCreateImage` does not error out — it silently captures only
  the desktop background/wallpaper, with no window content. Grant it to
  whatever process runs the script (Terminal, or the specific `python3`
  binary if run some other way).
- **Camera** — required for `camera_photo.py` (via `imagesnap`). Without
  it, capture fails for every camera.

## External dependencies (not installed via pip)

- **[Processing](https://processing.org/)** — required by `controller.py`
  to run the wall's Processing sketch. After installing the app, run
  Tools → "Install processing-java" from inside the Processing IDE once,
  to make the `processing-java` command line tool available.
- **[BetterDisplay](https://betterdisplay.pro/)** — required by
  `display_brightness.py`. Enable "Enable CLI access" in its settings.
- **imagesnap** — required by `camera_photo.py`. Install with:
  `brew install imagesnap`

## Python dependencies

```
pip3 install --user --break-system-packages -r requirements.txt
```

(`--break-system-packages` is needed because the macOS system Python is
managed by Homebrew and blocks direct installs otherwise.)

## Secrets

`telegram_bot.py` reads from a git-ignored `secrets/` folder, which must
be created manually:

- `secrets/telegram-token.txt` — the bot's token, a single line.
- `secrets/telegram-chat-id.txt` — the chat id to notify on startup, a
  single line. Find it by messaging the bot once and checking
  `update.effective_chat.id`, or with a bot like `@userinfobot`.
