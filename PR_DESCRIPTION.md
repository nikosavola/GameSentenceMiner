# Fix a few concrete Python safety bugs

Targeted correctness/locking fixes — not the big exception-triage sweep.

## What changed
- `gsm_utils.py`: two bare `except:` clauses → `except Exception` + debug log, so `KeyboardInterrupt`/`SystemExit` propagate for clean shutdown.
- `db.py`: mutable default arg `clean_columns: list = []` → `None` sentinel.
- `db.py`: `fetchall()`/`fetchone()` now take `self._lock` like the rest of the class did (they were the odd ones out).
- `configuration.py`: the module-global `config_instance` was being swapped with no lock while other threads read it via `get_config()`. Added an `RLock` and guarded the reads + the swap, keeping the slow file I/O *outside* the critical section to avoid deadlocks.

## Why
The config swap race and the unlocked reads are real thread-safety holes given the asyncio + Qt + worker-thread setup.

## Notes
- Deliberately did **not** tackle the ~195 silent `except Exception: pass` swallows here — that's a separate, larger triage.
- Also removed a stray commented-out duplicate inside one config getter.
