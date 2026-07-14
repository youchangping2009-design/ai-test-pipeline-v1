# Test Design

Use this stage for large work items that need explicit responsibility splitting before case planning.

Purpose:

- Split verification responsibility across B-side write checks, B-side display, C-side consumption, API guards, server validation, and risk hardening.
- Keep code review feedback in the design layer instead of rewriting test cases directly.
- Provide inputs to `testcases/case_plan.json`.

Primary artifacts:

- `design/verification_responsibility_map.md`
- `design/verification_responsibility_map.json`
- `design/test_design_matrix.md`
- `design/test_design_matrix.json`

Validation:

```bash
python3 skills/test-design/scripts/validate_responsibility_map.py \
  --input assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/design/verification_responsibility_map.json \
  --case-plan assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/testcases/case_plan.json
```
