# P1-6 Design Feedback From Code Review Confirmation

## Status

Done.

## What Changed

- Added `schemas/design_feedback.schema.json`.
- Added `skills/test-design/templates/design_feedback.template.json`.
- Added `skills/test-design/templates/design_feedback.template.md`.
- Added `skills/test-design/scripts/validate_design_feedback.py`.
- Added `design/design_feedback.*` to `scripts/create_work_item.py`.
- Added optional `design_feedback` validation in `scripts/validate_work_item.py` when the file exists.

## Policy

Code review confirmation feedback must enter the design layer first. It must not directly overwrite `testcases/testcases_main.md`.

Allowed target layers:

- `testability_gate`
- `acceptance_examples`
- `verification_responsibility_map`
- `test_design_matrix`
- `case_plan`

## Compatibility

`design_feedback.feedback_items` may be empty for initialized work items. Once feedback items are present, each item is validated for required fields, source `case_plan_id` references, design-layer target, and `must_not_directly_overwrite_testcase=true`.

## Validation

```bash
/usr/bin/python3 skills/test-design/scripts/validate_design_feedback.py \
  --input skills/test-design/templates/design_feedback.template.json \
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
