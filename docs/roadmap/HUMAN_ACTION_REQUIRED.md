# Human Action Required

当前无阻塞问题。

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
