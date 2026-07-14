# Claude Adapter

## 测试设计决策层

Claude 作为宿主工具接入时，仍消费仓库统一流程，不绑定固定模型或 provider。正式用例应从 `case_plan` 派生：

```text
structured_prd -> testability_gate -> acceptance_examples -> verification_responsibility_map -> case_plan -> testcases
```

P0 可先执行：

```text
structured_prd -> testability_gate -> case_plan -> testcases
```

`soft_prompt` 不得升级为 hard_block，`technical_background` 不得生成正式业务测试用例。code review 映证结果反馈到 `design/` 层，不直接覆盖 testcase。

严格校验默认只读：

```bash
python3 scripts/validate_work_item.py --project-code <PROJECT_CODE> --work-item-id <WORK_ITEM_ID> --strict
```

刷新 `quality_report.json` 需显式加 `--write-report`。正式 testcase 必须显式引用 `case_plan_id`。

正式 testcase 的步骤和预期结果应遵守 `rules/testcase_element_notation.md`。页面 / Tab 用 `[]`，按钮 / 操作入口用 `【】`，弹窗 / 抽屉 / 面板用 `《》`，字段 / 列表列用 `“”`，枚举值 / 输入值用 `{}`，状态 / 结果用 `<>`，提示语 / Toast 用 `「」`，接口 / 参数用反引号。需要检查时可加 `--check-element-notation`；非 strict 只 warning，strict 且显式启用时才阻塞。

正式 testcase 还应遵守 `rules/testcase_grouping_rules.md`。最终 `testcases_main.md` 按“页面 + 板块”分表，表格内继续保留“所属模块 / 所属功能点”；`__page_name / __section_name` 只是生成阶段隐藏分组字段。strict 会逐步禁止缺页面、缺板块和弱兜底分组。

复杂需求可使用 `--work-item-level L` 启用责任划分校验：`verification_responsibility_map` 必须非空，`case_plan.source_responsibility_ids` 必须指向存在且与 gate 规则一致的 responsibility。

这份说明只解释：在 Claude 类宿主环境中，如何接入仓库已经定义好的统一流程。

## 适用原则

- 使用当前 Claude 会话模型
- 仓库不要求你在流程文档里写死 Claude 型号
- 宿主差异只在适配层解释，不进入核心流程资产

## 你该怎么开始

1. 阅读 `START_HERE.md`
2. 阅读 `AGENTS.md`
3. 需要维护流程时阅读 `WORKFLOW_CONTRACT.md`

## Claude 下的推荐用法

- 把 Claude 会话当作运行时模型上下文
- 继续使用仓库统一脚本和统一产物路径
- 把 Claude 特有的提示、工作区约束或项目指令，留在宿主适配层管理

## 最小流程

```bash
/usr/bin/python3 scripts/create_work_item.py --project-code WX-YYPT --work-item-id REQ-001
/usr/bin/python3 scripts/prepare_regeneration_run.py --project-code WX-YYPT --work-item-id REQ-001
/usr/bin/python3 scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001
```

## Claude 适配边界

Claude 适配层可以处理：

- 当前会话模型
- 当前宿主如何传入上下文
- 当前宿主如何组织项目指令

Claude 适配层不应改写：

- 核心 prompt 的品牌中立性
- testcase / traceability 真源口径
- review gate 与 scorer 的仓库口径

## 真源口径

- `testcases_main.md` 是主 testcase 真源
- `testcases.md` 是兼容镜像
- `testpoints.md/json` 是从 `case_plan.json` 派生的评审视图，不是真源
- `coverage_first_traceability.json` 是主 traceability 真源
- `traceability_adapter.json` 是兼容层
