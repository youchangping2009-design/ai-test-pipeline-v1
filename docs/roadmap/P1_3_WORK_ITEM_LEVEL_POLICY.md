# P1-3 Work Item Level Policy

本文件定义 S / M / L 工作项级别的执行策略。它只描述 validator 与 pipeline 入口策略，不切换 testcase 真源，不接入 `test_design_matrix` strict gate。

## Level Definitions

| Level | Intended Use | Strict Required Design Artifacts | Optional / Reserved Artifacts |
|---|---|---|---|
| S | 轻量需求，规则少、无跨端链路 | `testability_gate`, `case_plan`, testcase `case_plan_id` 追溯 | `acceptance_examples`, `verification_responsibility_map` |
| M | 常规需求，需要验收标准 | `testability_gate`, `acceptance_examples`, `case_plan`, testcase `case_plan_id` 追溯 | `verification_responsibility_map` |
| L | 复杂需求，跨端链路/API/风险责任明显 | `testability_gate`, `acceptance_examples`, `verification_responsibility_map`, `case_plan`, testcase `case_plan_id` 追溯 | `test_design_matrix` 仍为预留 |

## validate_work_item Policy

`validate_work_item.py --strict --work-item-level <S|M|L>` 的强制规则：

- S: 不强制 `acceptance_examples`，不强制 `verification_responsibility_map`。
- M: 强制 `acceptance_examples`，并要求 `case_plan.source_example_ids`。
- L: 强制 `acceptance_examples` 和 `verification_responsibility_map`，并要求 `case_plan.source_example_ids` 与 `case_plan.source_responsibility_ids`。

所有 strict level 都要求：

- `testability_gate` 存在且非空。
- `case_plan` 存在且非空。
- 正式 testcase 显式引用存在的 `case_plan_id`。
- `risk_note` / `api_guard` / `security_hardening` 不混入 `product_acceptance` 主用例。
- `soft_prompt` 不升级为 hard_block。
- `technical_background` 不生成正式业务用例。

## run_submission_pipeline Policy

`run_submission_pipeline.py --work-item-level <S|M|L> --stop-at <stage>` 当前是入口/任务包层策略，不替代 `validate_work_item.py --strict`。

Stop-at stages:

- `testability_gate`
- `acceptance_examples`
- `verification_responsibility_map`
- `test_design_matrix`
- `case_plan`
- `testcases`
- `code_review`

Level guidance:

- S 推荐停点：`testability_gate`, `case_plan`, `testcases`, `code_review`
- M 推荐停点：`testability_gate`, `acceptance_examples`, `case_plan`, `testcases`, `code_review`
- L 推荐停点：`testability_gate`, `acceptance_examples`, `verification_responsibility_map`, `test_design_matrix`, `case_plan`, `testcases`, `code_review`

`test_design_matrix` 当前只是 L 档预留停点；是否接入 strict gate 由后续 `P1-5-001` 决定。

## Baseline

任何 level policy 修改后必须运行：

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```
