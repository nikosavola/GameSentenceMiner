# Trim per-frame overhead in the OCR loop

Three hot-path wins that fire on every OCR frame.

## What changed
- `electron_config.py`: `Store.get()` was doing a full `copy.deepcopy` of the OCR config under a lock on *every* getter. Added an opt-in `copy=False` and a read-only scalar accessor, and switched the per-frame scalar getters (language, scan rate, two-pass, keep-newline, furigana sensitivity, advanced-mode) to it. Mutable-returning getters keep their deepcopy.
- `gsm_utils.py`: `do_text_replacements` no longer reads + JSON-parses the replacements file and recompiles regexes on every call — it caches by file mtime and precompiles the patterns.
- `ocr_runtime.py`: `ClipboardThread.are_images_identical` now reuses the existing corner-sample early-out instead of converting both images to full numpy arrays each poll.

## Why
These ran several times per frame; the deepcopy in particular was pure waste since the getters return scalars.

## Notes
- Pure perf change, behavior preserved (verified the replacement logic output by hand).
- Vendored `ocr_runtime.py` got a minimal 6-line diff, no reformat.
- Left the P2 items (polling-floor tuning, metadata rebuild) as follow-ups.
