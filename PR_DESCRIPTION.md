# Index `game_lines` on timestamp & game_id

Probably the single biggest perf win in this batch.

## What changed
- Added `CREATE INDEX IF NOT EXISTS` for `idx_game_lines_timestamp` and `idx_game_lines_game_id` to the **unconditional** DB init path (in the sync-tracking migration, right after the existing sync-changes index).

## Why
These indexes only existed inside the tokenization setup, which is gated behind `_is_tokenization_enabled()`. With tokenization off, every stats/goals/heatmap request that filters by timestamp or game_id was doing a full table scan. On a large DB that's O(N) per request → now O(log N + k).

## Notes
- `IF NOT EXISTS` + matching index names means it coexists harmlessly with the tokenization path; that copy was left in place.
- Tiny diff (+10 lines), idempotent.
