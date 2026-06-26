# Run TS tests, type-check, and ruff in CI

Adds the CI coverage that was missing — the whole TypeScript test suite was running nowhere.

## What changed
- New `.github/workflows/ci_checks.yml` (PRs + pushes to main/develop, with concurrency + cancel-in-progress):
  - **ts** job: `npm ci` → `npm run test:ts` (vitest) → `tsc --noEmit`.
  - **lint-py** job: ruff `format --check` + `check` over `GameSentenceMiner tests scripts`.
- Removed the commented-out formatting step from `test_python.yml` (ruff now lives centrally in the new workflow, no duplication).

## Why
38 `*.test.ts` files — including the message-bus / process-manager core — never ran on any PR, and ruff was only enforced via an opt-in local pre-commit hook.

## Notes
- Node 22.12.0 + `cache: npm` to match the existing build workflows; actions left on major tags (SHA-pinning is its own PR).
- Couldn't run the workflow here (no node_modules locally); YAML validated.
