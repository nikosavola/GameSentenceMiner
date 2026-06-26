# Add CodeQL, pin actions to SHAs, Dependabot for Actions

Supply-chain hardening for the CI side.

## What changed
- New `.github/workflows/codeql.yml`: CodeQL over `javascript-typescript` + `python`, on PR/push to main + weekly cron, with minimal permissions.
- `dependabot.yml`: added a `github-actions` ecosystem entry (monthly, same grouping style as the rest) so pinned actions actually get update PRs.
- Pinned all third-party actions to full commit SHAs (with `# vX.Y.Z` comments) across the workflows — 19 refs total:
  - `softprops/action-gh-release` → `v2.6.2`
  - `dtolnay/rust-toolchain` (was `@stable`, a branch ref!) → stable HEAD
  - `Swatinem/rust-cache` → `v2.9.1`
  - `astral-sh/setup-uv` → `v5.4.2`

## Why
These workflows hold `contents: write` and the signing/PyPI secrets; a repointed tag would run in that context. SignPath was already SHA-pinned — now everything else matches.

## Notes
- First-party `actions/*` left on major tags (fine).
- SHAs resolved via the GitHub REST API. If this PR merges alongside the CI-checks PR, the new `ci_checks.yml`/`codeql.yml` actions will want pinning too.
