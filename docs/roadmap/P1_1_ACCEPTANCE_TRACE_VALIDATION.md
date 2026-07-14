# P1-1 Acceptance Trace Validation

本文件记录 P1-1 acceptance examples 到 case_plan 的追溯校验口径。

## Scope

P1-1-002 只确认 case_plan 对 acceptance examples 的追溯，不切换 testcase 真源，不推进 responsibility_map 深度规则。

## Required Behavior

- M/L strict 下，`case_plan.should_generate_case=true` 的计划必须填写 `source_example_ids`。
- `source_example_ids` 必须能在 `acceptance/acceptance_examples.json` 中找到。
- `case_plan.source_gate_ids` 必须与 `source_example_ids` 对应 example 的 `source_gate_ids` 有交集。
- `oracle_strength=soft_display` 的 example 只能派生 `prompt_display` / `ui_display` 类型计划。
- `oracle_strength=hard_block` 的 example 只能派生 `save_block` / `field_constraint`，且 `validation_path=product_acceptance`。
- S 档 strict 兼容轻量链路，不强制 acceptance examples。

## Positive Check

```bash
/usr/bin/python3 skills/case-generation/scripts/validate_case_plan.py \
  --input assets/projects/WX-YGJ/work_items/PT083/testcases/case_plan.json \
  --testability-gate assets/projects/WX-YGJ/work_items/PT083/acceptance/testability_gate.json \
  --acceptance-examples assets/projects/WX-YGJ/work_items/PT083/acceptance/acceptance_examples.json \
  --testcases assets/projects/WX-YGJ/work_items/PT083/testcases/testcases_main.md \
  --require-examples
```

Expected: PASS

## Negative Checks

These checks can be created with temporary JSON files under `/tmp`; they must fail:

- Remove `case_plan.source_example_ids`.
- Reference a missing example such as `AE-999`.
- Point `source_gate_ids` to a gate unrelated to the referenced example.

## Baseline

After any P1-1 trace change, run:

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```
