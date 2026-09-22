# Design Feedback

| feedback_id | source_review_stage | source_confirmation_file | source_case_plan_ids | feedback_type | target_layer | title | finding | recommended_action | must_not_directly_overwrite_testcase | status |
|---|---|---|---|---|---|---|---|---|---|---|
| DF-001 | manual_review | reviews/review_record.md | CP-002 | case_gap | case_plan | 补充集合型空值校验 | 空数组与空对象未覆盖。 | 补充集合型空值并区分校验层与请求层。 | true | applied |
| DF-002 | manual_review | reviews/review_record.md | CP-002 | case_gap | testability_gate | 保留 days_before 的零值边界 | `days_before=0` 回归边界缺失。 | 新增日期运算符独立规则和计划。 | true | applied |
| DF-003 | manual_review | reviews/review_record.md | CP-006 | invalid_case | testability_gate | 移出本 PR 的数量徽标验收 | 数量徽标属于关联问题背景，并非本 PR 直接范围。 | 标记 out_of_scope 或迁移独立工作项。 | true | applied |
