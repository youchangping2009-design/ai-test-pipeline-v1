# Celery Design Feedback 回灌验证

日期：2026-09-22

## 结论

Celery #10668 的唯一 requirement gap 已从 Case Plan 源头修复，并通过正式生成器重建下游资产。没有直接编辑正式 testcase。

## 通用修复

1. 新增 `design/feedback_application.json` 回灌凭证，记录 feedback、目标设计层和变更前后 SHA-256。
2. 新增确定性 validator，拒绝目标层越界、直接修改正式 testcase、陈旧 after hash 和 applied feedback 漏凭证。
3. Review checkpoint 与统一工作项校验在凭证存在时执行该 validator，并将凭证纳入 Review fingerprint。
4. `case_plan_direct` 使用 Acceptance Example 的 Given/When 作为执行上下文，使用 Case Plan assertion 作为正式预期真源。

## Celery 样本结果

- AE-005、AE-006、AE-008 与 CP-005、CP-006、CP-008 分层增加同步载荷仅包含任务 ID、不得传播远端 monotonic 时间戳的断言，避免验收上下文与 Case Plan 冲突。
- 11 条正式 testcase 由生成器重建；关联的 3 条用例已承接新断言。
- requirement Oracle coverage：`0.9444 -> 1.0`。
- implementation Oracle coverage：`0.5`；oldest-first 顺序没有批准需求依据，继续作为实现层部分覆盖项。
- overall compatibility coverage：`0.95`；testcase relevance：`1.0`。
- Coverage-First Traceability：11 条，invalid=0，false traceability rate=0。

## 验证

- 聚焦单测：19/19 PASS。
- Celery Harness Review：attempt=4，PASS。
- Celery Strict Gate：attempt=2，PASS。
- 全量质量基线：5/5 PASS，149 项单测通过。

## 剩余边界

当前 receipt 对新产物采取“存在即强校验”的兼容策略。将其提升为所有新 `applied` feedback 的强制门禁前，需要为历史已 applied 样本定义迁移方式，不能伪造当时未记录的变更前哈希。
