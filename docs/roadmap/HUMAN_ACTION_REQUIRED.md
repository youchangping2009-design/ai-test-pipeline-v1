# Human Action Required

当前存在 1 项需要人工或框架维护者处理的问题。

Date: 2026-08-06
Task ID: HARNESS-REVIEW-NOT-APPLICABLE
Blocker: 无代码分支的对比重跑可通过 `validate_work_item --strict --skip-code-reviews` 合法完成工作项strict，但Harness `review` 阶段没有 `not_applicable/skip` disposition，只按 `review_record.md` 与质量报告文件存在建立checkpoint；当前迁移后的 PT083 review record 仍明确为“待评审”。
Why autonomous agent cannot decide: 自动把待评审模板标为review succeeded会伪造流程状态；补写评审人、评审时间或code review request也与本次无代码事实冲突。新增review disposition需要框架契约和CLI设计。
Options:
1. 为Harness review阶段增加可审计的 `not_applicable` 状态、reason和CLI参数，并让strict_gate接受明确N/A；同时提供安全的checkpoint normalize入口或确保命中已成功stop-at时仍暂停。
2. 保持当前run停在Traceability，使用工作项CLI的 `--skip-code-reviews` 结果作为本次无代码收口证明。
Recommended option: 短期选2；后续实现1，并同时设计requirement_summary人工审批状态，避免继续依赖PROGRESS记录表达关键人工门。
Impact if unresolved: 当前 PT083 正式产物与工作项 strict 有效，但 run 无法在不伪造 review 的前提下进入 Harness strict_gate 终态。后续同类无代码重跑仍需保留 paused run 和独立 strict 结果两套状态。

Resolved:

- 2026-08-06 / PT083-DETERMINISTIC-REGEN：旧 PT083 18 条 L 档样本已按用户授权删除；当前 PT083 为迁移后的 M 档样本，具备 82 条 Coverage、75 条 Case Plan 和 75 条正式用例，原空 Coverage 阻塞不再适用。
- 以下 PT084/PT085/PT086 项均为迁移前历史基准记录，不再表示当前目录或可执行 run。
- 2026-08-06 / PT086-PROJECT-VIEW-FINGERPRINT：PT086最终收口已使用正式`refresh_project_views.py --project-code WX-YGJ`刷新项目派生视图；项目strict显示4个工作项全部ready、`stale_quality_report_count=0`，PT086 M strict和完整`run_quality_baseline.py` 5/5（含95项单测）均通过。未手改指纹、未改变业务语义，也未用项目索引刷新伪造Harness Review/Strict Gate。
- 2026-08-06 / REQUIREMENT-APPROVAL-MANIFEST-FINGERPRINT：Requirement Intake checkpoint 已改用正式 canonical approval binding；非绑定 manifest 变化只规范化旧 checkpoint，不撤销 approved receipt。summary、source manifest、raw input 与 requirement version 漂移继续使全部 checkpoint 失效并生成新的 pending approval ID；聚焦测试同时覆盖 audit、recover 和旧 manifest 兼容。
- 2026-08-06 / PT086-REQUIREMENT-SUMMARY-APPROVAL：用户已明确确认 PT086 与 PT084/PT085 完全同图符合预期、无需求增量且仅用于基准重跑，并批准当前 requirement summary。正式 CLI 已以 reviewer `ycp` 批准 `RUN-PT086-REQ-20260806`；Testcase阶段首次resume因manifest元数据纳入Requirement fingerprint触发重验，但summary/source/raw三类绑定值均未变化，已通过正式CLI重放同一既有批准并留下注释。同一run已完成到Traceability并暂停，当前需求审批本身无新增人工阻塞；误触发框架缺陷现已由canonical checkpoint修复。
- 2026-08-06 / PT085-TESTCASE-BUNDLE-STAGE-BOUNDARY：Harness `testcases` 阶段不再校验尚未刷新的兼容 Bundle；原 `validate_testcase_bundle.py` 已移动到 `traceability` 阶段，数量、Case Plan 映射和最终 strict 检查均保留。PT085已刷新75条Bundle、46条Coverage-First和46条Adapter，Bundle Validator与Traceability Validator均通过；原 run `RUN-20260806T063753Z` 已成功暂停在Traceability，review/strict_gate仍pending。
- 2026-08-06 / PT085-CASE-PLAN-STAGE-BOUNDARY：Harness `case_plan` 阶段不再传入未来 `testcases_main.md`；同一反向追溯 Validator 已移动到 `testcases` 阶段，未降低 `generated_testcase_ids` 和正式 testcase 映射检查。原 run `RUN-20260806T063753Z` 已成功恢复并暂停在 Case Plan，testcases 仍为 pending。
- 2026-04-28 / P3-001：用户接受 compatibility-only 阶段，允许新增 `testcase_bundle.json` 作为从 `testcases_main.md` 派生的投影，不切换 testcase 真源。
- 2026-04-29 / Ad-hoc SC0963 testcase rerun：用户已清空 SC0963 旧产物并仅保留 input；本轮按当前 schema 重建 `image_evidence_inventory.json`、用例链路与派生产物，`validate_work_item --strict --work-item-level S --retention minimal --skip-code-reviews` 已通过，原 evidence/image_evidence 历史枚举兼容阻塞关闭。
- 2026-05-22 / Ad-hoc SC0972：用户已补充 `assets/projects/AD/work_items/SC0972/inputs/需求描述`，原“缺 PRD/截图无法生成正式用例”阻塞关闭。本轮已基于需求描述生成 19 条主用例并通过 M strict 校验。
- 2026-08-06 / PT084-COVERAGE-TRACEABILITY：逐条复核11个缺口后，基于来源证据将错误的 C 端“云机版本Tab必填”修正为 audit item，为其余10项补齐 Gate/Acceptance/Case Plan/testcase；另修复1条被旧宽映射掩盖的宣传内容“云机类型必填”。官方生成器已确定性产出46条有效主追溯记录，主失真率降为0，Harness traceability、M strict（跳过后续 code review）和质量基线通过。

只有出现真实需要用户或业务方决策的问题时，当前 Agent 才应在本文件写入条目。

## Template

```text
Date:
Task ID:
Blocker:
Why autonomous agent cannot decide:
Options:
Recommended option:
Impact if unresolved:
```
