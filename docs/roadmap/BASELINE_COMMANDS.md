# Baseline Commands

本文件记录当前 P0.5 基线命令与预期结果。

## One-command Baseline

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```

## Expanded Commands

### 1. Framework/sample independence guard

```bash
/usr/bin/python3 scripts/validate_framework_sample_independence.py
```

Expected: PASS

### 2. Harness unit tests

```bash
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py'
```

Expected: PASS

### 3. Generic regression fixtures

```bash
/usr/bin/python3 scripts/run_eval_suite.py --tier regression
```

Expected: PASS

### 4. Golden fixture snapshot

```bash
/usr/bin/python3 scripts/run_eval_suite.py --tier golden
```

Expected: PASS

基线只验证仓库通用规则、Harness 与自包含 fixture，不直接验证 `assets/projects/` 下任何业务工作项。具体工作项必须通过显式 `--project-code` 与 `--work-item-id` 单独验收。
