# Coverage Planning Skill

## 目标

根据 structured PRD 与 reasoning pack 生成标准 Coverage Matrix，明确哪些规则进入正式用例、审计或丢弃。

## 输入

- `structured_prd/structured_prd.json`
- `analysis/reasoning_pack.json`
- `docs/testcase_signal_policy.md`

## 输出

- `coverage/coverage_matrix.json`

## 执行入口

```bash
python3 scripts/generate_coverage_matrix.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

## 校验入口

```bash
python3 skills/coverage-planning/scripts/validate_coverage_matrix.py \
  --input <coverage_matrix.json> \
  --schema schemas/coverage_matrix.schema.json
```

## 控制要求

- 数据源过滤、排序和高优 fidelity 必须保持 critical。
- 列表元数据默认进入 audit，不直接膨胀正式用例。
- Coverage 必须区分 explicit rule 与 AI reasoning。
