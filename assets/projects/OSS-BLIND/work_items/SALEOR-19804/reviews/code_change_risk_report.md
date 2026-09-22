# Saleor #19804 盲测 Oracle 对照报告

生成时间：2026-09-21
工作项：OSS-BLIND/SALEOR-19804
Oracle：[saleor/saleor#19804](https://github.com/saleor/saleor/pull/19804)，head `785e65384379a3ba8bf3d0231dfe6014eedab03a`

## 结论摘要

- 建议带风险开始测试。盲测用例准确命中核心一行修复：标签反向关系由 `set(instances)` 改为 `add(*instances)`，覆盖相同、重叠、不同标签跨批次成员保留。
- 上游新增测试还验证标签名大小写归一、重复输入去重且只新增一个规范化标签，当前资产完全遗漏。
- scorer 同时识别到跨批次用例预期过于抽象，未写出上游参数矩阵和精确成员集合。

## 代码与测试证据

| 位置 | Oracle 行为 | 盲测承接 | 结论 |
|---|---|---|---|
| `gift_card_bulk_create.py` `assign_gift_card_tags` | 使用 `add(*instances)` 追加当前批次，不替换历史成员 | CP-001、CP-003、CP-004 | 命中 |
| 参数化回归测试 | 相同、完全相同多标签、部分重叠、完全不同四组跨批次集合 | CP-003 | 语义命中，oracle 过于抽象 |
| `test_create_gift_cards_normalizes_tag_names` | 大小写变体和重复标签被归一；仅新增一个小写标签 | 无 | 缺失 |
| GraphQL 响应断言 | `errors` 为空、`count` 正确、每张新卡标签集合正确 | CP-002、CP-004、CP-005 | 命中 |

## 问题清单

| 编号 | 严重级别 | 类型 | 问题 | 建议 |
|---|---|---|---|---|
| R1 | Medium-High | case_gap | 未覆盖标签名大小写归一、重复输入去重和标签表只新增一个规范化记录。 | 在 Structured PRD/Gate 明确归一规则，再生成原子 Case Plan。 |
| R2 | Medium | weak_case | CP-003 只写“相同、部分重叠、完全不同”，没有给出输入矩阵、批次数量及每个标签精确成员集合。 | 将四组参数与集合等式写入 Acceptance/Case Plan。 |

## AI 本地验证记录

| 验证ID | 级别 | 方法 | 实际结果 | 结论 |
|---|---|---|---|---|
| V-001 | L0 | 固化 8 个盲测产物 SHA-256 | 生成前资产已冻结，oracle 未参与生成 | confirmed_pass |
| V-002 | L1 | GitHub Files API 检查 2 个 changed files、1 行实现改动和 2 组新增测试 | 核心关系语义命中，确认 R1-R2 | confirmed_gap |
| V-003 | L2 | 上游 pytest 执行 | 当前无 Saleor 源码 checkout，未在本地执行 | blocked |

## 人工验证重点

1. P0：先后两批使用相同、重叠、不同标签集合，逐标签查询并断言成员 ID 等于两批输入并集。
2. P0：同一请求输入已有标签的大小写变体和重复值，确认响应标签集合去重、数据库仅新增一个规范化标签。
3. P1：较大批次执行后核对请求耗时与 SQL 数量；具体阈值仍需产品/研发确认。

## 测试产物影响建议

R1-R2 已写入 `design/design_feedback.json`；应先修改设计层并重生成，不能直接覆盖 testcase。

## 反馈实施复测

R1-R2 已全部从设计层应用：标签归一、记录去重、关系去重拆为原子计划，跨批次 oracle 固定为四批输入和精确成员集合。重生成后 9 条用例，oracle coverage/relevance 为 `1.0/1.0`。
