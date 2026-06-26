# Add ESLint + start typing the IPC boundary

Gives the TypeScript side a linter (it had none) and establishes a pattern for typing renderer→main payloads.

## What changed
- New `eslint.config.mjs` (flat config) for `electron-src`: `@eslint/js` + `typescript-eslint` recommended, with `no-explicit-any` set to **warn** so it doesn't block CI on day one. Added a `lint` script and the devDeps (lockfile regenerates in CI).
- `main.ts`: throttled the global error dialogs — a repeating `unhandledRejection` was spamming blocking modals. Now only the first error in a 60s window shows a dialog; the rest are logged.
- Demonstrated the IPC typing pattern: new `shared/ipc_types.ts` with `SaveSettingsPayload`, wired into the `saveSettings` handler (`any` → `unknown` + typed shape, existing runtime guards kept).

## Why
Python has ruff enforced; TS had nothing, and the ~185 `any`s cluster right at the untrusted renderer boundary.

## Notes
- Scoped on purpose: didn't try to fix all 185 `any`s — they're warn-level findings now.
- `typescript-eslint` v8 may warn about TS 6 not being officially supported yet; it still runs. Couldn't run eslint here (no node_modules).
