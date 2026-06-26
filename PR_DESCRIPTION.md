# Drop `shell=True` and add request timeouts

Tightens up subprocess calls and network requests that could hang or mis-quote input.

## What changed
- `gsm_utils.py`: external-tool launch no longer uses the `shell=True` f-string branch — always uses the argv list form that already existed below it.
- `oneocr_dl.py`: dropped `shell=True` from the PowerShell call (cmd was already a list); added timeouts to the rg-adguard POST and both streaming downloads.
- `replay_handler.py`: the TTS fallback now URL-encodes the mined text before interpolation and has a timeout, so a slow TTS server can't wedge the audio pipeline.
- Added explicit timeouts to the Anki-Connect notification POSTs and the PyPI update check.

## Why
A timeout-less request on the audio/notify path blocks the calling thread indefinitely, and unescaped text in the TTS URL could corrupt the request.

## Notes
- Brought these up to the standard already used in `anki.py` / `util/clients/*`.
- Didn't touch the vendored `owocr/` fork.
- 3 pre-existing ruff warnings on untouched lines were left alone to keep the diff scoped.
