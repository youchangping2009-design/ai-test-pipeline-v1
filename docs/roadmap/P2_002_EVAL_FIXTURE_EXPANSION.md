# P2-002 Eval Fixture Expansion

## Status

Done.

## What Changed

- Added `scripts/run_evals.py --all`.
- Added `evals/fixtures/README.md` as the fixture index.

## Fixtures Covered

- `PT083`
- `PROMPT_ONLY`
- `LINKAGE_ONLY`
- `RISK_API_ONLY`

## Validation

```bash
/usr/bin/python3 scripts/run_evals.py --fixture PT083
```

```bash
/usr/bin/python3 scripts/run_evals.py --all
```

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```
