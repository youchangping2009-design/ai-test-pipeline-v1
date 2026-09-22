# Oracle Scope 分层评分修复验证

日期：2026-09-22

## 修复内容

`scripts/score_oracle_delta.py` 新增 assertion 级 `oracle_scope`：

- `requirement`：已批准需求与正式验收契约。
- `implementation`：后置代码或新增测试暴露的实现行为。
- `risk`：运维开关、故障注入、并发和内部错误路径。

旧输入不填写时按 `requirement` 兼容；原 `oracle_coverage_rate` 保留，同时新增三类分层覆盖率与分布。

## 7 份盲测复算

| 样本 | 总体兼容分 | Requirement | Implementation | Risk | Testcase relevance |
|---|---:|---:|---:|---:|---:|
| Appsmith #42244 | 1.0 | 1.0 | 1.0 | N/A | 1.0 |
| Chatwoot #15768 | 1.0 | 1.0 | 1.0 | N/A | 1.0 |
| Saleor #19804 | 1.0 | 1.0 | 1.0 | N/A | 1.0 |
| Django #21801 | 1.0 | 1.0 | N/A | N/A | 1.0 |
| Celery #10668 | 0.9444 | 0.9444 | N/A | N/A | 1.0 |
| Temporal #11968 | 0.65 | 1.0 | 0.25 | 0.0 | 1.0 |
| Supabase #50569 | 0.6538 | 1.0 | 0.3571 | N/A | 1.0 |

## 结论

修复验证了此前 Temporal/Supabase 的低总体分不是批准需求覆盖不足，而是实现级和风险 Oracle 未进入盲生成输入。当前真实需求层只剩 Celery 同步载荷契约这一项部分覆盖，需要下一阶段从设计层补强。

本修复没有修改任何正式 testcase、Case Plan、Gate 或冻结哈希；只调整后置 Oracle 评分器、评分输入分类和评分结果。
