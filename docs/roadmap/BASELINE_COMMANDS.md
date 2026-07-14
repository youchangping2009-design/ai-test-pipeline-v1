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

PT083 has been regenerated with testability gate, acceptance examples, responsibility map, test design matrix, case plan, and case_plan_id-backed testcases, so strict validation should now pass.

### 3. PT083 eval

```bash
/usr/bin/python3 scripts/run_evals.py --fixture PT083
```

Expected: PASS
