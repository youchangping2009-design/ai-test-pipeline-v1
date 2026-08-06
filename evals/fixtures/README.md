# Eval Fixtures

当前 fixture 覆盖：

| Fixture | Purpose |
|---|---|
| `PT083` | 当前 PT083 M 档 golden regression，覆盖 technical_background、soft_prompt、写侧/读侧责任、0元链路、goodsRegion API/risk 分池 |
| `PROMPT_ONLY` | 提示类需求，只应生成 soft_display / prompt_display |
| `LINKAGE_ONLY` | 跨端链路需求，必须生成 linkage case_plan |
| `RISK_API_ONLY` | 风险/API 类需求，应进入 risk_note / api_guard，不进入 product_acceptance 主验收 |
| `ELEMENT_NOTATION` | 测试用例元素标注轻量样例，覆盖页面、按钮、弹窗、字段、值、状态、提示语、接口字段，以及明显误用反例 |
| `CASE_GROUPING` | testcase grouping 最小回归样例，覆盖不同页面分组、同页不同板块分表、B端/C端页面拆分、接口兜底风险独立板块 |

运行单个 fixture：

```bash
/usr/bin/python3 scripts/run_evals.py --fixture PT083
```

运行全部 fixture（兼容入口）：

```bash
/usr/bin/python3 scripts/run_evals.py --all
```

正式分级入口：

```bash
/usr/bin/python3 scripts/run_eval_suite.py --tier smoke
/usr/bin/python3 scripts/run_eval_suite.py --tier regression
/usr/bin/python3 scripts/run_eval_suite.py --tier golden
```

- `smoke`：3 个快速代表 fixture，适合本地高频反馈。
- `regression`：全部 6 个 fixture、57 个可量化检查，适合每个 PR。
- `golden`：regression + 全量单元测试 + PT083 M strict，并与提交到仓库的 fixture 指纹和指标 baseline 比较。

`ELEMENT_NOTATION` 与 `CASE_GROUPING` 各包含一个预期失败的负向检查。负向样例若意外通过，整个 tier 失败。

只有在规则或 fixture 变更已经评审、且本轮全部检查通过时，才可显式刷新 golden baseline：

```bash
/usr/bin/python3 scripts/run_eval_suite.py --tier golden --update-baseline
```
