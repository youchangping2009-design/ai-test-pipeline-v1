# Acceptance Examples

Use this stage after `testability_gate` for medium and large work items.

Purpose:

- Convert testable product rules into Given / When / Then examples.
- Make the expected oracle explicit before creating case plans.
- Prevent inferred or soft prompt content from becoming confirmed hard-block expectations.

Primary artifacts:

- `acceptance/acceptance_examples.md`
- `acceptance/acceptance_examples.json`

Validation:

```bash
python3 skills/acceptance-example/scripts/validate_acceptance_examples.py \
  --input assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/acceptance/acceptance_examples.json \
  --testability-gate assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/acceptance/testability_gate.json
```
