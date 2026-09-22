# P1-2 Responsibility Validation

本文件记录 `verification_responsibility_map` 深度校验的最小口径。

## Scope

P1-2-001 只深化责任划分校验，不切换 testcase 真源，不接入 `test_design_matrix` strict gate。

## Required Behavior

- responsibility 的 `source_rule_id` 必须能回到 `testability_gate.source_rule_id`。
- `soft_prompt` 必须落在 B端页面展示 / 提示验证，不得升级为写侧、API、风险或 C端消费链路责任。
- `technical_background` 不得生成验证责任。
- `linkage` 必须要求 C端消费链路验证，并在责任侧或方法中体现 C端 / 消费 / 链路。
- `risk_hardening`、`risk_only`、`risk_note_only` 必须进入 API 兜底或风险项责任，不得要求 C端主消费链路。
- hard_block / 必填 / 不可保存类规则优先落在写侧。
- `consumer_verification_required=true` 时，case_plan 必须存在 linkage 类计划。

## Positive Check

```bash
/usr/bin/python3 skills/test-design/scripts/validate_responsibility_map.py \
  --input evals/fixtures/LINKAGE_ONLY/expected/responsibility_map.expected.json \
  --testability-gate evals/fixtures/LINKAGE_ONLY/expected/testability_gate.expected.json \
  --case-plan evals/fixtures/LINKAGE_ONLY/expected/case_plan.expected.json
```

Expected: PASS

## Negative Checks

These temporary checks must fail:

- `soft_prompt` responsibility is marked as B端写侧 / API / risk.
- `technical_background` appears in responsibility map.
- `linkage` responsibility does not set `consumer_verification_required=true`.
- `risk_hardening` responsibility lacks both `api_guard_required` and `risk_note_required`.
- `consumer_verification_required=true` without linkage case_plan.

## Baseline

After changing responsibility rules, run:

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```
