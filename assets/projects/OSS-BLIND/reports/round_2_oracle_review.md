# OSS-BLIND Round 2 Oracle Review

日期：2026-09-21

## 总结论

三份盲测资产均命中 PR 的核心修复方向，但尚不适合直接进入 strict gate。Review 共确认 8 条设计反馈：6 条 coverage/精度缺口、1 条原子性问题、1 条范围过伸。

| 样本 | 核心改动命中 | 已确认主要缺口 | 范围误判 | 建议 |
|---|---:|---:|---:|---|
| Appsmith #42244 | 是 | 3 | 0 | 建议开始测试，补精确 oracle |
| Chatwoot #15768 | 是 | 2 | 1 | 建议带风险开始测试 |
| Saleor #19804 | 是 | 2 | 0 | 建议带风险开始测试 |

确定性 oracle-delta 评分：Appsmith oracle 覆盖率 `0.8333`、用例相关率 `1.0`；Chatwoot 为 `0.6875`、`0.8571`；Saleor 为 `0.5833`、`1.0`。`partial` 按 0.5 计分，分数只描述冻结资产与当前 oracle 的差距，不作为正式需求覆盖率。

## 主要发现

1. 需求驱动盲测能够稳定覆盖公开描述中的核心业务行为：协议拦截、falsy 值保留、严格类型匹配、跨批次关系追加。
2. 代码新增测试中的实现级边界不会自然从 PR 描述产生：Chatwoot 的空数组/空对象与 `days_before=0`，Saleor 的标签大小写归一/去重，Appsmith 的精确错误文案与 JDBC 属性键值。
3. 来源分层仍有缺陷：Chatwoot 关联 issue 的 context-only 数量徽标问题进入了 main Coverage、Gate、Case Plan 和正式 testcase。
4. 原子化仍可能在 Structured PRD 的复合规则处失效：Appsmith CP-004 把多个失败分支合并成一条用例。
5. 当前 scorer 能识别 Saleor 的抽象 oracle，但没有识别上述代码对照缺口和 Chatwoot 范围过伸；因此内部质量分不能替代外部 oracle 评测。

## 建议的流水线改进顺序

1. 在需求归一化与 Structured PRD 中持久化来源角色：`primary_requirement`、`context_only`、`oracle_only`，禁止 `context_only` 默认进入 main Coverage。
2. 在 Rule -> Gate/Case Plan 之间增加复合断言拆分检查，避免一个规则包含多个独立失败分支。
3. 增加 oracle-delta 评测产物，将“盲测遗漏”“范围过伸”“已有测试重合”独立计分，不把代码测试直接回灌正式 testcase。
4. 扩展 scorer：识别枚举/矩阵缺项、精确错误文案缺失以及集合型空值边界，不只检查文案泛化。

## 边界

- 评审前已用 SHA-256 冻结三份工作项从需求摘要到主追溯的 8 类资产。
- Oracle 来自三个公开 PR 的固定 head SHA 与 changed-files patch。
- 本轮未修改正式 testcase、Case Plan、Gate、Acceptance 或 Coverage；反馈仅写入 `design_feedback` 与 `reviews`。
- 未在本地执行上游项目单测，因为三个业务仓库未 checkout；对应验证保持 L2 blocked，不声称运行通过。

## 设计反馈回灌复测

8 条设计反馈已从 Structured PRD、Testability Gate、Acceptance Examples 和 Case Plan 回灌，并由生成器刷新正式用例及追溯产物；没有直接编辑 `testcases_main.md`。

| 样本 | 冻结用例数 | 重生成用例数 | Oracle coverage | Testcase relevance | 质量信号 |
|---|---:|---:|---:|---:|---|
| Appsmith #42244 | 6 | 7 | 1.0 | 1.0 | weak/generalized/semantic/duplicate 均为 0 |
| Chatwoot #15768 | 7 | 9 | 1.0 | 1.0 | context-only 用例已移除，四类质量信号均为 0 |
| Saleor #19804 | 6 | 9 | 1.0 | 1.0 | 归一去重拆为原子计划，四类质量信号均为 0 |

原始 `blind_asset_freeze.json` 保持不变，用于证明需求摘要未变、其余设计与用例资产来自反馈回灌后的新版本。详细差异见 `reports/round_2_feedback_regeneration.md`。
