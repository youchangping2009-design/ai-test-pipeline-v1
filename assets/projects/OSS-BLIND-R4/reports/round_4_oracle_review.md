# OSS-BLIND-R4 Oracle Review

日期：2026-09-22

## 总结论

四份冻结资产均覆盖公开 PR 的核心需求方向，43 条正式 testcase 全部为 direct match 或 requirement regression，相关率均为 `1.0`。Oracle 静态对照形成 6 条待处理设计反馈：Grafana 4 条、Rails 1 条、Kubernetes 1 条；Home Assistant 无新增缺口。

| 样本 | 固定 head | 冻结用例 | Oracle 覆盖率 | 需求层覆盖率 | 用例相关率 | 开放反馈 |
|---|---|---:|---:|---:|---:|---:|
| Grafana #133083 | `9aeaf1e7` | 14 | 0.375 | 0.8333 | 1.0 | 4 |
| Home Assistant #182800 | `e1734829` | 6 | 1.0 | 1.0 | 1.0 | 0 |
| Rails #58429 | `edd687c7` | 10 | 0.8333 | 1.0 | 1.0 | 1 |
| Kubernetes #141831 | `42d2a3f1` | 13 | 0.875 | 1.0 | 1.0 | 1 |

四个样本合计 28 个 Oracle assertion，按 `covered=1`、`partial=0.5`、`missing=0` 加权，总体微平均覆盖率为 `0.75`（21/28）。低分主要来自 Grafana 暴露出的实现级契约，不代表 43 条已生成用例存在范围污染。

## 主要发现

1. 四份样本的正式用例均保持需求相关，未出现 PT083 或其他样本语义泄漏。
2. Home Assistant 的核心行为和合理回归完整命中，无需回灌。
3. Grafana 需求主链基本覆盖，但 context 在非 watch 路径的断言不完整；错误传播、版本策略和并发安全属于需分层处理的实现级风险。
4. Rails 的核心四类新增回归均命中，仅缺少零 tagging logger 的能力边界。
5. Kubernetes 的公开 Warning 契约完整覆盖，但空字符串指针是否视为有效范围字段需要需求/类型约束确认。

## 边界

- Oracle 解封前已冻结每个工作项 8 类主资产及 SHA-256。
- Oracle 只来自四个公开 PR 的固定 head、changed-files patch、已有测试和 PR 公开验证说明。
- 本阶段没有修改 Coverage、Gate、Acceptance、Case Plan 或正式 testcase；6 条结论只写入 design feedback。
- 未 checkout 四个上游业务仓库，未执行上游测试；结论为 L0/L1 静态映证，不是 L2 运行时证明。

## 下一阶段建议

先对 6 条 feedback 做来源分流：需求可确认项进入 Acceptance/Case Plan，纯实现风险留在 Testability Gate/验证责任，Kubernetes 空字符串语义在确认前不得直接生成正式用例。完成反馈回灌凭证后，再从设计层重生成并执行 Strict Gate。
