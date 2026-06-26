# Kill N+1 queries in the stats/db web layer

Pushes filtering into SQL instead of loading whole tables into Python.

## What changed
- `calculate_game_milestones`: swapped `GamesTable.all()` (pulls base64 image blobs) for `all_without_images()`, and replaced the per-game `get_start_date()` loop with one grouped `MIN(timestamp) ... GROUP BY game_id` (new `get_start_dates()` helper).
- `build_game_display_name_mapping`: replaced an O(games × lines) re-scan with a single `all_without_images()` map.
- DB-browser regex search: `game_filter` + date range now go into SQL before fetching (mirroring the adjacent LIKE branch); the regex itself stays in Python.
- Goals metric extraction: date filter pushed into SQL (new timestamp-bounded query) instead of loading a game's full history and filtering in a loop.

## Why
These compound with the missing `game_lines` indexes — the worst offenders loaded the entire table per request.

## Notes
- Careful to keep output byte-identical (same rows/order/counts); the image blob is still fetched for just the one or two games actually displayed.
- Pre-existing ruff warnings outside the edited regions were left alone.
