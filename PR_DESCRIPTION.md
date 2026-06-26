# Fix the PyPI publish workflows

Three fixes to the PyPI publishing flow.

## What changed
- Fixed a broken bash branch in `pypi_dev.yml` — there was a Python-style `else:` (trailing colon) inside an `if/else`, so the dev/rc version gate never worked. Rewrote it to mirror the clean `pypi_release.yml` (stdlib `tomllib`, proper heredocs) and dropped the 3rd-party `toml` install.
- Switched both workflows to PyPI **Trusted Publishing** (OIDC, `id-token: write`, `pypa/gh-action-pypi-publish`) and removed the long-lived `PYPI_API_TOKEN`.
- Added `concurrency` blocks to both so two quick pushes can't race two publishes.

## Why
The broken gate + a long-lived token were the two real risks; OIDC is the recommended path (the workflow comments already said so).

## Notes
- **Manual step before merge:** register the GitHub repo as a Trusted Publisher on PyPI, otherwise the publish step will fail once the token is gone.
