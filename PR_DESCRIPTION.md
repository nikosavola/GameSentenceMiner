# Dependency hygiene

Small, safe dependency-metadata cleanups + flagging the risky ones.

## What changed
- `package.json`: `engines.node` `>=18` → `>=21 <23`. The `>=18` range allowed Node versions CLAUDE.md says break the build; the new range admits both Node 21 (CLAUDE.md / legacy workflows) and 22 (current release pipeline) while excluding 23+.
- `pyproject.toml`: added inline comments flagging `keyboard~=0.13.5` as unmaintained (last release 2020, runs with admin) and a pynput migration candidate; and marking `numpy==2.2.6` / `tokenizers==0.22.1` as intentional hard pins pending ABI verification.

## Why
The Node range was a real footgun; the rest is documentation so the next person knows what's deliberate vs. stale.

## Notes
- **Heads up:** CLAUDE.md (Node 21) and the release pipeline (22.12.0) disagree — someone should reconcile. This `engines.node` edit overlaps with the workflow-cleanup PR; pick one.
- Left `keyboard`, numpy, tokenizers, and the GitHub-sourced `pypresence` as-is (no blind changes); didn't touch the lockfiles (generated in CI).
