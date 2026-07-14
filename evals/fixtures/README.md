# Eval Fixtures

当前 fixture 覆盖：

| Fixture | Purpose |
|---|---|
| `PT083` | 历史 golden regression，覆盖 technical_background、soft_prompt、写侧/读侧责任、0元链路、goodsRegion API/risk 分池 |
| `PROMPT_ONLY` | 提示类需求，只应生成 soft_display / prompt_display |
| `LINKAGE_ONLY` | 跨端链路需求，必须生成 linkage case_plan |
| `RISK_API_ONLY` | 风险/API 类需求，应进入 risk_note / api_guard，不进入 product_acceptance 主验收 |
| `ELEMENT_NOTATION` | 测试用例元素标注轻量样例，覆盖页面、按钮、弹窗、字段、值、状态、提示语、接口字段，以及明显误用反例 |
| `CASE_GROUPING` | testcase grouping 最小回归样例，覆盖不同页面分组、同页不同板块分表、B端/C端页面拆分、接口兜底风险独立板块 |

运行单个 fixture：

```bash
/usr/bin/python3 scripts/run_evals.py --fixture PT083
```

运行全部 fixture：

```bash
/usr/bin/python3 scripts/run_evals.py --all
```

元素标注 fixture 当前用于 lint 样例验证，可执行：

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_element_lint.py \
  --input evals/fixtures/ELEMENT_NOTATION/positive.testcases.md \
  --strict

/usr/bin/python3 skills/case-generation/scripts/testcase_element_lint.py \
  --input evals/fixtures/ELEMENT_NOTATION/negative.testcases.md \
  --strict
```

第二条命令预期失败。
