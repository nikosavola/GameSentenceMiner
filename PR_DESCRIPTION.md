# Tidy up the workflows & pin a Node version

Low-risk CI cleanup — no behavior changes to the real release pipeline.

## What changed
- Deleted two fully commented-out / dead workflows (`release_mac_test.yml`, `test_electron_mac_homebrew.yml`).
- Added a `.nvmrc` and pointed setup-node at it to stop the Node-version drift (workflows currently mix `21`, `22.12.0`, and `engines >=18`).
- Removed the no-op `submodules: true` from checkout steps (there's no `.gitmodules` in the repo).

## Why
Dead/duplicated workflow config is confusing and the three different Node policies are a real footgun given CLAUDE.md warns against newer majors.

## Notes
- **Heads up:** CLAUDE.md says "Node 21" but the main release pipeline uses 22.12.0 — these disagree and a human should reconcile. I aligned to the release pipeline.
- This also bumps `package.json` `engines.node`, which overlaps with the deps-hygiene PR — pick one.
- Skipped the bigger `workflow_call` reusable-workflow extraction on purpose (too risky to do without CI to validate) — good follow-up.
