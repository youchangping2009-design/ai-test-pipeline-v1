# Human Action Required

当前存在 1 项需要人工确认的重生成基线问题。

Date: 2026-07-22
Task ID: PT083-DETERMINISTIC-REGEN
Blocker: PT083 当前正式 `coverage_matrix.entries` 为空；从修复后的 reasoning + structured PRD 可重建 67 条 coverage，并生成 45 条未规划候选用例，但现有 21 条 Case Plan 只保存正式 testcase ID，没有 `source_coverage_ids`，无法将候选稳定收敛到当前 18 条正式用例。
Why Codex cannot decide: 将 Case Plan 映射到新 Coverage 会改变正式重生成基线和候选用例集合，需要测试负责人确认哪些候选应进入主用例。
Options:
1. 保持当前 18 条正式用例真源和硬失败保护，后续专项评审 45 条候选。
2. 人工评审并为 21 条 Case Plan 补 `source_coverage_ids`，确认后切换到确定性重生成。
Recommended option: 先选 1，避免自动重跑用 0 条或未经评审的 45 条候选覆盖正式用例；单独安排 Coverage/Case Plan 映射评审。
Impact if unresolved: 正式交付和 strict 不受影响，但 PT083 无法仅靠规则生成器从上游资产确定性重建当前 18 条主用例。

Resolved:

- 2026-04-28 / P3-001：用户接受 compatibility-only 阶段，允许新增 `testcase_bundle.json` 作为从 `testcases_main.md` 派生的投影，不切换 testcase 真源。
- 2026-04-29 / Ad-hoc SC0963 testcase rerun：用户已清空 SC0963 旧产物并仅保留 input；本轮按当前 schema 重建 `image_evidence_inventory.json`、用例链路与派生产物，`validate_work_item --strict --work-item-level S --retention minimal --skip-code-reviews` 已通过，原 evidence/image_evidence 历史枚举兼容阻塞关闭。
- 2026-05-22 / Ad-hoc SC0972：用户已补充 `assets/projects/AD/work_items/SC0972/inputs/需求描述`，原“缺 PRD/截图无法生成正式用例”阻塞关闭。本轮已基于需求描述生成 19 条主用例并通过 M strict 校验。

只有出现真实需要用户或业务方决策的问题时，Codex 才应在本文件写入条目。

## Template

```text
Date:
Task ID:
Blocker:
Why Codex cannot decide:
Options:
Recommended option:
Impact if unresolved:
```
