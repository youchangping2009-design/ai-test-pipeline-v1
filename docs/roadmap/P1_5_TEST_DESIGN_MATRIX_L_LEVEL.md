# P1-5 Test Design Matrix L-Level Integration

## Status

Done.

## What Changed

- Added `schemas/test_design_matrix.schema.json`.
- Added `skills/test-design/scripts/validate_test_design_matrix.py`.
- Connected `design/test_design_matrix.json` to `validate_work_item.py --strict --work-item-level L`.
- Updated `PT083` with a real `design/test_design_matrix.json` and `.md`.

## L Strict Rules

- `test_design_matrix.items` must be non-empty.
- Matrix items must not contain TODO / TEMPLATE / 待补充 / 示例 placeholder values.
- Matrix items must reference existing `gate_id`, `example_id`, `responsibility_id`, and `case_plan_id`.
- Matrix source relationships must align with the referenced upstream artifacts.
- Every `should_generate_case=true` case_plan must be covered by the matrix.

## Validation

```bash
/usr/bin/python3 skills/test-design/scripts/validate_test_design_matrix.py \
  --input assets/projects/WX-YGJ/work_items/PT083/design/test_design_matrix.json \
  --testability-gate assets/projects/WX-YGJ/work_items/PT083/acceptance/testability_gate.json \
  --acceptance-examples assets/projects/WX-YGJ/work_items/PT083/acceptance/acceptance_examples.json \
  --responsibility-map assets/projects/WX-YGJ/work_items/PT083/design/verification_responsibility_map.json \
  --case-plan assets/projects/WX-YGJ/work_items/PT083/testcases/case_plan.json
```

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --skip-code-reviews \
  --strict \
  --work-item-level L
```

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```
