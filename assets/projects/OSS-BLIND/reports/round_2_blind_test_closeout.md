# OSS-BLIND 第二轮公开盲测收口报告

日期：2026-09-21

## 结论

第二轮公开盲测已经完成并闭环。三份样本均完成需求隔离生成、资产冻结、后置 Oracle Review、设计层反馈回灌、正式用例重生成、追溯刷新、Harness Strict Gate 和运行审计。

当前结论是：流水线已适合继续扩展新的公开文本型 PR 盲测样本，但不能把本轮结果解释为“首轮生成已无缺口”。首轮能够稳定命中核心改动，实施级边界仍依赖后置 Oracle Review 识别；回修后的 1.0 表示反馈闭环完整，不表示盲测首轮即达到 1.0。

## 首轮与回修后指标

| 样本 | 首轮 Oracle coverage | 首轮 testcase relevance | 回修后 Oracle coverage | 回修后 testcase relevance | 正式用例变化 |
|---|---:|---:|---:|---:|---:|
| Appsmith #42244 | 0.8333 | 1.0 | 1.0 | 1.0 | 6 → 7 |
| Chatwoot #15768 | 0.6875 | 0.8571 | 1.0 | 1.0 | 7 → 9 |
| Saleor #19804 | 0.5833 | 1.0 | 1.0 | 1.0 | 6 → 9 |

回修后共有 25 条正式用例，三份主追溯 `false_traceability_rate=0.0`；weak、generalized、semantic mismatch、duplicate 均为 0。

## 本轮识别并修复的通用问题

1. Reasoning 生成器存在 PT083 领域模板污染，向无关需求注入 banner、瓷片、金刚区语义。
2. 已确认规则没有稳定进入 main Coverage，生成器过度依赖字段形态和旧领域关键词。
3. `context_only` 来源可能被提升为主验收，造成范围过伸。
4. 复合规则没有按独立断言拆分，形成多失败分支合并用例。
5. Case Plan direct renderer 对 API 场景使用错误的 UI 保存模板，且验证侧标签不准确。
6. 纯文本来源仍被空图片 Evidence 占位阻断 Strict Gate。
7. Harness 恢复到既有 checkpoint 时可能错误完成下游状态；strict 开发自测派生要求未正确接通。

以上问题均已在通用流程、生成器、设计层或 Harness 层修复，没有通过直接手改最终 testcase 绕过主链。

## 扩测准入判断

可以进入下一轮公开盲测，建议继续选择 3–5 个文本型 PR，并保持以下准入条件：

- 生成输入只包含公开需求描述及明确的 primary requirement；代码 diff 和已有测试必须在资产冻结后解封。
- 首轮指标与回修后指标分别报告，不用回修结果替代首轮能力。
- 新样本至少覆盖一种本轮未覆盖的需求形态，例如数据库迁移、权限状态机、异步任务或前后端联动。
- 继续执行 `source_scope`、原子断言、Case Plan 追溯、Coverage-First Traceability 和 Strict Gate。
- 若连续样本再次出现同类缺口，应修通用源头，不为单一样本增加专用关键词模板。

## 完成证据

- Appsmith、Chatwoot、Saleor 三个 Harness run 均为 `completed`。
- 三个 `strict_gate` 均为 `succeeded/exit=0`，三个 run audit 均为 PASS、0 error。
- OSS-BLIND 项目 Strict：3 个工作项、25 条 testcase、0 个开放风险。
- 全量质量基线：5/5，通过 134 项单元测试。

## 剩余边界

- 样本数只有 3 个，尚不足以证明对所有项目类型具有稳定泛化能力。
- 本轮 Oracle 是静态读取公开 PR diff 与测试断言；三个上游业务仓库没有本地 checkout，因此未执行其真实构建和单元测试。
- 回修后的 1.0 是对当前固定 Oracle 集合的覆盖，不代表未知实现边界已经全部覆盖。
