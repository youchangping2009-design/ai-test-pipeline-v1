# Design Feedback

| feedback_id | source_review_stage | source_confirmation_file | source_case_plan_ids | feedback_type | target_layer | title | finding | recommended_action | must_not_directly_overwrite_testcase | status |
|---|---|---|---|---|---|---|---|---|---|---|
| DF-001 | manual_review | reviews/review_record.md | CP-001 | case_gap | acceptance_examples | 补充非法 JDBC URL 的精确错误文案 | 当前只断言连接创建错误。 | 保留固定错误文案后重生成。 | true | applied |
| DF-002 | manual_review | reviews/review_record.md | CP-005 | case_gap | case_plan | 明确 token 到 JDBC 属性的映射 | 当前未明确 `UID=token` 与 `PWD`。 | 增加属性捕获断言。 | true | applied |
| DF-003 | manual_review | reviews/review_record.md | CP-004 | case_gap | case_plan | 拆分连接失败分支 | 三类失败结果被合并。 | 拆分前缀拒绝与 driver null 分支。 | true | applied |
