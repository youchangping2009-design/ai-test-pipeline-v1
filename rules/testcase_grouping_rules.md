# Testcase Grouping Rules

本文档定义正式 testcase 的页面 / 板块 / 模块 / 功能点分层规则。

## 分层模型

推荐链路：

```text
structured_prd.modules[]
  -> module_name
  -> features[].page_name
  -> features[].section_name
  -> features[].feature_name
  -> coverage_matrix.entries[]
  -> testcase row
  -> markdown table group
```

字段含义：

- `module_name` 表示业务模块或功能域，对应 `testcases_main.md` 表格内的“所属模块”列。
- `feature_name` 表示具体功能点，对应 `testcases_main.md` 表格内的“所属功能点”列。
- `page_name` 表示页面、Tab、一级页面容器或明确页面入口，用于 Markdown 一级分组：`# 页面：xxx`。
- `section_name` 表示页面下的业务板块、弹窗、区域、配置区、列表区、表单区、链路区或补充生成板块，用于 Markdown 二级分组：`## 板块：yyy`。
- `__page_name` / `__section_name` 是 testcase row 的隐藏分组字段，只用于渲染和校验，不输出为正式表格列。

## 为什么按页面 + 板块分表

“所属模块 / 所属功能点”描述业务归属，不一定等于用户看到的页面结构。同一个业务模块可能跨 B 端配置页、C 端消费页、接口校验和异步任务；同一个页面也可能包含多个业务板块。最终 `testcases_main.md` 必须按 `page_name + section_name` 分表，表格内继续保留“所属模块 / 所属功能点”列，方便阅读、评审和自动化映射。

禁止把“所属模块”作为唯一分表依据。

## page_name 来源优先级

1. `structured_prd.modules[].features[].page_name`
2. `coverage_matrix.entries[].page_name`
3. 从 evidence / structured_prd 页面骨架推导出的页面名
4. 非 strict 可 warning 并使用“未识别页面”
5. strict 禁止空 page_name、`TODO`、`默认页面`、`未识别页面`、`示例页面`

页面名应使用业务可读名称，例如：后台商品配置页、商品列表页、购买页、宣传内容配置页、权益配置页、活动配置页、广告位配置页。

对于产品描述型需求，如果 PRD 先给出业务域 / 管理入口，再列出子页面或功能模块，应优先保留这层业务层级：

- `page_name` 使用业务域或管理入口，例如“页游落地页管理”。
- `section_name` 使用子页面 + 功能模块，例如“页游落地页列表-筛选条件”“页游落地页列表-操作按钮”“新建页游单游戏落地页”“新建页游多游戏聚合页”。
- 不应把这类需求统一分到“规则用例表”；“规则用例表”不是业务可读板块名。

## section_name 来源优先级

1. `structured_prd.modules[].features[].section_name`
2. `coverage_matrix.entries[].section_name`
3. `supplemental_case()` 显式传入的业务板块名
4. 根据 `feature_name` / `coverage_type` / `case_type` 推导出的业务板块
5. 非 strict 可 warning 并使用“未识别板块”
6. strict 禁止空 section_name、`TODO`、`默认板块`、`其他`、`未分类`、`示例板块`、`未识别板块`

页面内真实板块示例：基础信息、商品区配置、宣传内容、特殊区配置、价格配置、权益配置、筛选区、列表区、操作区。

弹窗 / 抽屉示例：新增弹窗、编辑弹窗、删除确认弹窗、宣传内容配置弹窗。

补充测试板块示例：字段异常与边界、容量限制、数据源组合约束、真实CRUD链路、展示规则配置、跨板块主流程、B端到C端消费链路、接口兜底风险、异步任务验证。

## 禁止弱兜底

- 不允许所有缺失 `section_name` 的用例统一兜底为“添加弹窗”。
- “添加弹窗”只能用于明确新增 / 添加场景，不能作为通用 fallback。
- 不允许不同页面的用例混入同一张表。
- 不允许同一页面下明显不同业务区域混入同一板块。
- 不允许生成“默认板块”“其他”“未分类”这类弱分组进入 strict。
- 页面 / 板块命名应使用业务可读名称，不使用技术变量名。

## 生成规则

用例生成时必须先确定 `page_name`，再确定 `section_name`，再确定 `module_name / feature_name`，最后生成 `case_plan / testcase`。

- 正式 testcase 不应缺页面 / 板块上下文。
- 跨板块主流程可以生成，但 `section_name` 必须是“跨板块主流程”或更具体业务链路名。
- B 端配置影响 C 端时，C 端用例的 `page_name` 应为 C 端页面，不应继续挂在 B 端配置页下。
- 风险 / API 兜底用例不得混入正常产品验收页面板块，应单独归入“接口兜底风险”或 `risk_note`。

## 校验

`skills/case-generation/scripts/validate_testcase_grouping.py` 校验 `testcases_main.md` 的页面 / 板块分组。非 strict 只输出 warning；strict 下弱页面、弱板块和缺失分组会失败。
