# Design Feedback

| feedback_id | source_review_stage | source_confirmation_file | source_case_plan_ids | feedback_type | target_layer | title | finding | recommended_action | must_not_directly_overwrite_testcase | status |
|---|---|---|---|---|---|---|---|---|---|---|
| DF-001 | manual_review | reviews/review_record.md | CP-002, CP-004 | case_gap | testability_gate | 补充标签名称归一与去重 | 大小写归一和重复输入去重完全缺失。 | 补充规则后生成原子计划。 | true | applied |
| DF-002 | manual_review | reviews/review_record.md | CP-003 | case_gap | acceptance_examples | 具体化跨批次标签集合判定 | 缺少具体参数矩阵和成员 ID 集合。 | 用四组输入及集合等式具体化 oracle。 | true | applied |
