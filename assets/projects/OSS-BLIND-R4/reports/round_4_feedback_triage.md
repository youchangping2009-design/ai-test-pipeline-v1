# OSS-BLIND-R4 Oracle Feedback Triage

日期：2026-09-22

## 结论

Oracle Review 的 6 条反馈已完成来源分流，尚未修改任何正式设计产物：

- 1 条为已批准需求在设计链中的漏传：Grafana 非 watch 序列化路径的请求 context。应从 Testability Gate 重新进入 Acceptance 与 Case Plan，不能直接补 testcase。
- 4 条为 Oracle-only 实现风险：Grafana 的错误/JSON 异常、版本策略、并发安全，以及 Rails 的零 tagging logger 边界。只补入 Gate 风险层，不自动生成正式业务用例。
- 1 条为待确认语义：Kubernetes 范围字段指向空字符串时是否抑制 Warning。只保留 needs_confirmation，不生成正式用例。
- Home Assistant 没有新增反馈，保持冻结资产不变。

## 分流明细

| 样本 | Feedback | 来源分类 | 下一步目标 | 是否进入正式用例主链 | 理由 |
|---|---|---|---|---|---|
| Grafana | DF-001 | oracle_only | Testability Gate `risk_note_only` | 否 | 错误类型、空结果、非法 JSON 和 decode target 细节在获批摘要中均为未决契约 |
| Grafana | DF-002 | approved_requirement_gap | Testability Gate -> Acceptance -> Case Plan | 是 | 获批摘要与 Reasoning `ER-002` 已明确 Serializer 接收请求 context，但 Structured PRD 之后只保留了 watch 路径 |
| Grafana | DF-003 | oracle_only | Testability Gate `risk_note_only` | 否 | 持久化版本 cap、跨组拒绝和删除豁免在摘要中明确为待确认项 |
| Grafana | DF-004 | oracle_only | Testability Gate `risk_note_only` | 否 | 并发安全来自实现接口注释，摘要将其保留为开放问题 |
| Rails | DF-001 | oracle_only | Testability Gate `risk_note_only` | 否 | 零 tagging logger 的递归终止行为来自实现，批准需求只要求多 tagging 与混合组合 |
| Kubernetes | DF-001 | needs_confirmation | Testability Gate `needs_confirmation` | 否 | 实现按指针 nil 判定，但公开需求未定义空字符串是否合法或是否经过默认化/校验 |

## 处置顺序

1. 通过 `feedback-action prepare` 分别冻结 6 条反馈当前指向的 Testability Gate。
2. 通过白名单 `propose_feedback_design_artifacts` 写入 Gate：DF-002 形成可测正式决策，其余 5 条保持 risk-only 或 needs-confirmation。
3. 通过 `record_feedback_application` 生成 before/after SHA-256 凭证，并将反馈置为 applied。
4. 只对 Grafana DF-002 沿正常顺序重生成 Acceptance、Case Plan、testcase 与派生资产；其他反馈不得进入正式 testcase。
5. 重新计算 Oracle delta，复验冻结漂移只来自有凭证的设计回灌，再执行 Review 与 Strict Gate。

## 对流水线的判断

本轮没有发现跨样本污染或正式用例范围失控。Grafana DF-002 暴露的是一处阶段传递缺口：Reasoning 已保留明确需求，但 Structured PRD 未将该原子语义继续传递。后续复测应检查该遗漏是否属于通用 Structured PRD 生成问题；在获得跨样本证据前，本轮不修改框架生成逻辑。

## 边界

- 本阶段只修改 review 层的 feedback 路由并新增分流报告。
- 未修改 Testability Gate、Acceptance Examples、Case Plan、正式 testcase 或任何业务代码。
- 未把 implementation/risk assertion 计作正式需求缺口。
