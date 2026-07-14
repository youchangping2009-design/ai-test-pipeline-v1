# Testability Gate

Use this stage after `structured_prd.json` and before acceptance examples / case plan generation.

Purpose:

- Decide whether each structured PRD rule is testable.
- Prevent technical background, soft prompts, risk-only notes, pending confirmations, and out-of-scope items from becoming hard business test cases.
- Preserve traceability from structured rules to later design artifacts.

Primary artifacts:

- `acceptance/testability_gate.md`
- `acceptance/testability_gate.json`

Validation:

```bash
python3 skills/testability-gate/scripts/validate_testability_gate.py \
  --input assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/acceptance/testability_gate.json \
  --structured-prd assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.json
```
