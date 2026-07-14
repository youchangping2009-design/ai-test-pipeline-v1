# CASE_GROUPING Fixture

该 fixture 用于最小回归 testcase grouping 规则：

- 不同页面输出不同 `# 页面` 分组。
- 同一页面下不同业务板块输出不同 `## 板块` 表格。
- B端配置页用例和C端消费页用例分到不同 `page_name`。
- 风险/API兜底用例归入独立的“接口兜底风险”板块。
- 不依赖“添加弹窗”作为通用兜底。

运行：

```bash
/usr/bin/python3 scripts/run_evals.py --fixture CASE_GROUPING
```
