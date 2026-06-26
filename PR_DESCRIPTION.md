# Tests for the VAD trimming pipeline

Fills the biggest gap in the core media pipeline coverage.

## What changed
- Extended `tests/test_vad.py` with 17 new tests covering the previously-untested `VADProcessor` surface:
  - `process_audio` (the detect → validate → render chain, plus the reject path)
  - `_validate_detection` (empty/None rejects, short-audio gate, the trailing-segment end-time fix)
  - `_render_decision` (reject result, trim path with offset math, negative-offset clamping, cut-and-splice delegation)
  - `extract_audio_and_combine_segments` (segment-combination math, merge-gap logic, the no-valid-segment `RuntimeError`)

## Why
`test_vad.py` only covered WAV loading + raw detection — none of the logic that actually produces the card audio. These are pure-ish functions, so they test well with synthetic inputs.

## Notes
- ⚠️ **Tests were written but not run** — there's no `.venv` in the environment I worked in. They mirror the existing file's mocking patterns and are grounded in the real signatures, but please run `pytest tests/test_vad.py` before trusting them.
- Skipped the model-heavy Whisper segment-filtering loop and `VADSystem` orchestration to avoid guessed assertions.
