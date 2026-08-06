# Baseline Commands

本文件记录当前 P0.5 基线命令与预期结果。

## One-command Baseline

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```

## Expanded Commands

### 1. PT083 non-strict

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --skip-code-reviews
```

Expected: PASS

### 2. PT083 strict

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --skip-code-reviews \
  --strict
```

Expected: PASS

PT083 is the current M-level migrated sample with approved requirement intake, testability gate, acceptance examples, case plan, case_plan_id-backed testcases, and current quality fingerprints, so strict validation should pass with code reviews explicitly skipped.

### 3. PT083 eval

```bash
/usr/bin/python3 scripts/run_evals.py --fixture PT083
```

Expected: PASS

### 4. WX-YGJ lightweight project shell

```bash
/usr/bin/python3 scripts/validate_project.py \
  --project-code WX-YGJ \
  --strict \
  --validate-work-items \
  --skip-code-reviews
```

Expected: PASS
