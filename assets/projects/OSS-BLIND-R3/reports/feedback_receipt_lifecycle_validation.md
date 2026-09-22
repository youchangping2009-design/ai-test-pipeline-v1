# Feedback Application Receipt 生命周期验证

日期：2026-09-22

## 结论

新工作项的 applied design feedback 已强制要求回灌凭证；历史工作项保留显式兼容状态，不需要也不允许补造历史变更哈希。

## 实现

- 新建工作项默认启用 `pipeline_policy.feedback_application_receipt_required=true`。
- manifest 同时声明 `design/feedback_application.json`，schema 在策略启用时校验该声明。
- Harness Review 与统一工作项校验始终运行 feedback application validator。
- 强制策略下，存在 applied feedback 且 receipt 缺失时失败。
- receipt 存在时校验 feedback 完整性、目标设计层、before/after SHA-256 格式及当前 after hash。
- Review fingerprint 纳入 manifest 与 receipt，策略或凭证变化不能复用旧 checkpoint 输入指纹。

## 兼容验证

| 样本 | Policy | Receipt | 结果 |
|---|---|---|---|
| Celery #10668 | required | 2 applications / 4 artifacts | verified |
| Appsmith #42244 | legacy missing | none | legacy_compatible |
| Chatwoot #15768 | legacy missing | none | legacy_compatible |
| Saleor #19804 | legacy missing | none | legacy_compatible |

历史三份样本没有生成补录凭证，因此没有伪造当时未记录的 before hash。

## 验证结果

- 聚焦单测：29/29 PASS，包括强制策略缺 receipt、legacy compatibility、非法路径、陈旧 after hash、非十六进制 hash。
- Celery strict：PASS。
- Celery Oracle Review：PASS，requirement coverage=1.0，testcase relevance=1.0。
- 全量质量基线：5/5 PASS，152 项单测通过。

## 剩余边界

当前 before hash 仍需人工在修改前留存。下一阶段应提供两阶段 prepare/record 命令，让工具先捕获设计层 baseline，再在修改完成后生成 receipt。
