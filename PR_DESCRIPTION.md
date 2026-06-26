# Harden Electron windows & external-link handling

Closes a few Electron RCE-shaped footguns around opening URLs and Node-integrated windows.

## What changed
- `open-external-link` (`front.ts`) now parses the URL and only hands `http(s)` to `shell.openExternal` — `file:`, `javascript:`, and custom protocol handlers get logged and dropped.
- Same `new URL().protocol` check applied to the main window's `setWindowOpenHandler` (`main.ts`), replacing a loose `startsWith('http')`.
- Removed the overlay-settings code path that opened arbitrary `window.open()` targets into a fresh `nodeIntegration:true` / `contextIsolation:false` window (the actual RCE vector). Popups are now denied; external `http(s)` links go to the OS browser.
- Kept the overlay main window's `webSecurity:false` / `nodeIntegration:true` (Yomitan + the Node preload genuinely need it) but added a `SECURITY:` comment plus `will-navigate` / `setWindowOpenHandler` guards so it can't be navigated away from bundled `file://` content.

## Why
The settings/overlay pages render dictionary content; an injected `window.open` could otherwise get full Node access on the user's machine.

## Notes
- Verified all existing `window.open` / `open-external-link` callers use `https` docs links, so nothing legit breaks.
- Left the overlay window on its current flags rather than forcing `getSecureWebPreferences()` — it really does need them; the navigation guards are the safer middle ground.
