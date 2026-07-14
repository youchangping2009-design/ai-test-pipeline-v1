# P2-001 Repair Loop

## Status

Done.

## What Changed

- Added `scripts/run_repair_loop.py`.
- Updated `docs/autonomous_execution.md` with the repair loop entry.

## Policy

- Repair is command-driven and host/model/provider agnostic.
- Validation supports expected pass and expected fail.
- Repair attempts are capped at 2.
- If the expected outcome is still not reached, the script can write `docs/roadmap/HUMAN_ACTION_REQUIRED.md`.
- The loop does not weaken validators or strict gates.

## Validation

```bash
/usr/bin/python3 scripts/run_repair_loop.py \
  --task-id P2-001-SMOKE \
  --command-json '["/usr/bin/python3","--version"]' \
  --expect pass
```

```bash
/usr/bin/python3 scripts/run_repair_loop.py \
  --task-id P2-001-EXPECTED-FAIL \
  --command-json '["/usr/bin/python3","-c","import sys; sys.exit(1)"]' \
  --expect fail
```

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```
