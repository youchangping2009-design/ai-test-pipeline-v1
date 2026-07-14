# Work Queue

本文件是 Codex 自驱动任务队列。状态可取：

- `todo`
- `in_progress`
- `done`
- `blocked`

Codex 每次应先读取 `NEXT_ACTION.md`。当 NEXT_ACTION 为空、已完成或阻塞时，从本文件选择最高优先级 `todo` 任务。

| Priority | Task ID | Status | Title | Scope | Exit Criteria |
|---|---|---|---|---|---|
| P1 | P1-1-001 | done | acceptance_examples strict validation | 强化 acceptance_examples schema/validator，并接入 M/L strict | M/L strict 下缺失或弱 acceptance_examples 会失败 |
| P1 | P1-1-002 | done | case_plan traces acceptance_examples | case_plan 优先追溯 source_example_ids | M/L strict 下 case_plan 缺 source_example_ids 会失败 |
| P1 | P1-1-003 | done | PT083 eval acceptance_examples assertions | PT083 eval 增加 acceptance_examples required assertions | eval 能检查 hard_block/soft_display/linkage 验收示例 |
| P1 | P1-2-001 | done | verification_responsibility_map deep validation | 深化责任划分规则，但不切 testcase 真源 | L strict 可稳定检查 B端/C端/API/风险责任 |
| P1 | P1-3-001 | done | work_item_level execution policy | 明确 S/M/L 在 pipeline 和 validator 中的执行策略 | 不同 level 的强制产物和 stop-at 行为清晰 |
| P1 | P1-4-001 | done | eval fixture expansion | 扩展 golden fixtures | 至少覆盖提示类、风险/API 类、跨端链路类 |
| P1 | P1-5-001 | done | test_design_matrix L-level integration | L 档接入 test_design_matrix，但保持模板兼容 | L strict 能识别空/弱 test_design_matrix |
| P1 | P1-6-001 | done | design_feedback from code review confirmation | code review 映证结果进入 design_feedback | 不直接覆盖 testcase，反馈到 design 层 |
| P2 | P2-001 | done | repair loop | 增加有限 repair loop | 最多 2 轮 repair，不降低规则强度 |
| P2 | P2-002 | done | eval fixture expansion | 扩展 eval 到多项目样例 | eval 能覆盖更多需求形态 |
| P3 | P3-001 | done | testcase_bundle.json compatibility-only projection | 新增 testcase_bundle.json 派生投影，不切换真源 | bundle 可从 testcases_main.md 生成并校验一致 |

## Selection Rules

1. 同优先级按文件顺序选择。
2. 被标记为 `blocked` 的任务不得继续推进，除非阻塞已解除。
3. 每轮只推进一个任务。
4. 若执行中发现任务范围过大，应拆分任务并更新队列。
