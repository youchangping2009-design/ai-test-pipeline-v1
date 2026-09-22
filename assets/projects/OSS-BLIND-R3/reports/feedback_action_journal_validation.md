# Feedback Action Journal And Audit Validation

## Scope

本阶段为反馈 Action Runtime 增加动作级过程证据、幂等恢复和确定性审计，不修改业务代码、盲测正式资产或 Oracle 结论。

## Controls

- 每个动作分别写入不可覆盖的 `<action_id>.intent.json` 与 `<action_id>.result.json`。
- request SHA-256 绑定 intent、result 与完整 Action；不同请求不能复用 Action ID。
- 已完成动作幂等复用 result；intent 后中断可通过原 Action 恢复。
- 确定性失败同样写入 result，避免被误判为进程崩溃；修复后必须使用新 Action ID。
- 审计要求成功动作按 prepare、至少一次 propose、唯一 record 顺序闭环，并核对 receipt 与 applied 状态。
- 新工作项默认启用 `feedback_action_journal_required=true`；旧工作项无日志时保持 legacy compatibility。
- Review fingerprint 包含 journal，日志变化会触发 Review 重验。

## Validation

```bash
/usr/bin/python3 -m unittest \
  tests.test_feedback_action_runtime \
  tests.test_manage_feedback_application \
  tests.test_feedback_application_validation \
  tests.test_oracle_review_validation \
  tests.test_harness_runtime \
  tests.test_requirement_approval
```

结果：66/66 通过。覆盖幂等结果复用、Action ID 冲突、intent 后恢复、失败动作终态、未完成 intent、结果绑定篡改、强制策略与 legacy compatibility。

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py audit-feedback-actions \
  --project-code OSS-BLIND-R3 --work-item-id CELERY-10668
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code OSS-BLIND-R3 --work-item-id CELERY-10668 \
  --skip-code-reviews --strict
/usr/bin/python3 scripts/run_quality_baseline.py
```

结果：Celery 历史日志状态为 `legacy_compatible`，strict 通过；全量质量基线 5/5、170 项单元测试通过。

## Remaining Risk

当前日志绑定工作项、feedback、Action ID 与请求内容，但尚未绑定具体 Harness run、执行主体或 provider 身份。这不影响路径隔离、状态迁移和审计正确性，可作为后续责任追踪增强。
