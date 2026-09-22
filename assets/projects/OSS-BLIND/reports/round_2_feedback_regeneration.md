# OSS-BLIND Round 2 Feedback Regeneration

日期：2026-09-21

## 结论

首轮公开盲测确认的 8 条设计反馈已全部从设计层应用，并通过 Case Generator 重生成正式用例。三份样本的 oracle coverage 与 testcase relevance 均提升为 `1.0`；没有直接手工改写正式 testcase。

## 变化摘要

| 样本 | Structured PRD / Gate 调整 | Case Plan / Testcase 变化 | 冻结前后 |
|---|---|---|---|
| Appsmith #42244 | 固化 JDBC 错误文案、`UID/PWD` 映射；driver 拒绝与空连接拆为原子断言 | 6 -> 7 | 需求摘要哈希不变，其余 7 类冻结资产产生预期变化 |
| Chatwoot #15768 | 新增空数组、空对象、`days_before=0`；数量徽标改为 `context_only/out_of_scope` | 7 -> 9；移除原范围过伸 CP-006 | 需求摘要哈希不变，其余 7 类冻结资产产生预期变化 |
| Saleor #19804 | 新增标签归一与去重三条原子断言；具体化四批成员集合 | 6 -> 9 | 需求摘要哈希不变，其余 7 类冻结资产产生预期变化 |

## 质量与追溯

| 样本 | Main Coverage | Gate | Acceptance | Case Plan | Testcase | false traceability | Oracle coverage / relevance |
|---|---:|---:|---:|---:|---:|---:|---:|
| Appsmith #42244 | 7 | 14 | 7 | 7 | 7 | 0.0 | 1.0 / 1.0 |
| Chatwoot #15768 | 9 | 20 | 9 | 9 | 9 | 0.0 | 1.0 / 1.0 |
| Saleor #19804 | 9 | 19 | 9 | 9 | 9 | 0.0 | 1.0 / 1.0 |

三份质量报告中的 weak、generalized、semantic mismatch、duplicate 均为 0。所有 `design_feedback` 状态均为 `applied`。

## 门禁修复

strict 复测发现纯文本需求仍因空 `image_evidence` 被阻塞，与现有 Grounding 规则冲突。现改为：来源清单存在可用图片来源或 inventory 实际包含图片时继续强校验；纯文本来源跳过图片非空校验。图片型工作项的门禁强度不变。

另修复 Design Feedback Validator：仅允许 `status=applied` 且 `feedback_type=invalid_case` 的反馈保留已删除 Case Plan 的历史引用；其他反馈仍要求引用现存计划。

## Harness Strict Gate 收口

- 三个既有 run 均已恢复到 `strict_gate` 并最终 `completed`；strict gate 均为第 2 次尝试成功。
- 首次失败的唯一真实阻断是纯文本来源仍执行图片 inventory 非空校验；traceability 与 testcase 在该次日志中实际均为 PASS。
- 修复后 OSS-BLIND 项目视图为 3/3 ready、25 条 testcase、0 个开放风险、0 个过期质量报告。
- 全量质量基线 5/5 通过，包含 134 项单元测试。

## 边界

- 原始盲测冻结清单未重写，仍作为首轮资产基线。
- 本轮只验证 AI Test Pipeline 资产生成与静态 oracle 映射；三个上游业务仓库的单元测试仍未在本地执行。
- 本轮三个 Harness strict gate 已完成；未执行三个上游业务仓库的本地构建或单元测试。
