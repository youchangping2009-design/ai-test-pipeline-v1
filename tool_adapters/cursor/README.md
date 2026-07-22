# Cursor Adapter

## 测试设计决策层

Cursor 只作为宿主适配层，不重写仓库流程真源。正式 testcase 应从 `testcases/case_plan.json` / `case_plan.md` 派生，不应绕过 case_plan 直接从 `structured_prd` 生成。

推荐链路：

```text
structured_prd -> testability_gate -> acceptance_examples -> verification_responsibility_map -> case_plan -> testcases
```

轻量工作项可省略 P1 产物，但正式交付至少保留：

- `acceptance/testability_gate.json`
- `testcases/case_plan.json`

严格校验：

```bash
python3 scripts/validate_work_item.py --project-code <PROJECT_CODE> --work-item-id <WORK_ITEM_ID> --strict
```

默认校验只读，不刷新 `quality_report.json`；刷新报告需显式加 `--write-report`。正式 testcase 必须显式引用 `case_plan_id`。

正式 testcase 的步骤和预期结果应遵守 `rules/testcase_element_notation.md`。页面 / Tab 用 `[]`，按钮 / 操作入口用 `【】`，弹窗 / 抽屉 / 面板用 `《》`，字段 / 列表列用 `“”`，枚举值 / 输入值用 `{}`，状态 / 结果用 `<>`，提示语 / Toast 用 `「」`，接口 / 参数用反引号。需要检查时可加 `--check-element-notation`；旧工作项默认兼容。

正式 testcase 还应遵守 `rules/testcase_grouping_rules.md`。最终 `testcases_main.md` 按“页面 + 板块”分表，表格内继续保留“所属模块 / 所属功能点”；`__page_name / __section_name` 只是生成阶段隐藏分组字段。strict 会逐步禁止缺页面、缺板块、默认板块、其他、未分类等弱兜底。

复杂需求可使用 `--work-item-level L` 启用责任划分校验：`verification_responsibility_map` 必须非空，`case_plan.source_responsibility_ids` 必须指向存在且与 gate 规则一致的 responsibility。

这份说明只解释：在 Cursor 中，如何接入仓库已经定义好的统一流程。

## 适用原则

- Cursor 是宿主工具，不是流程真源
- `.cursor/` 中的规则和 subagents 只是 Cursor 适配资产
- 核心流程仍以 `START_HERE.md`、`WORKFLOW_CONTRACT.md`、`scripts/`、`schemas/` 为准

## 你该怎么开始

1. 先看根目录 `START_HERE.md`
2. 再看 `AGENTS.md`
3. 需要理解流程契约时再看 `WORKFLOW_CONTRACT.md`

## Cursor 下的推荐用法

- 使用当前 Cursor 会话模型
- 让 `.cursor/` 只承担宿主提示、规则补充和子代理组织
- 真正的流程输入、产物真源和校验命令仍来自仓库统一入口

## Cursor 现有资产

当前仓库仍保留：

- `.cursor/rules/`
- `.cursor/subagents/`
- `.cursor/mcp.json`

这些内容应视为 Cursor 适配实现，而不是流程真源。

## 最小流程

```bash
/usr/bin/python3 scripts/create_work_item.py --project-code WX-YYPT --work-item-id REQ-001
/usr/bin/python3 scripts/prepare_regeneration_run.py --project-code WX-YYPT --work-item-id REQ-001
/usr/bin/python3 scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001
```

## 你不需要做什么

- 不需要把 Cursor 规则文件当成仓库唯一规则来源
- 不需要把当前模型名写进 `prompts/`
- 不需要因为 Cursor 存在 `.cursor/` 就绕过仓库统一脚本入口

## 真源口径

- `testcases_main.md` 是主 testcase 真源
- `testcases.md` 是兼容镜像
- `testpoints.md/json` 与正式用例同步生成，以 `case_plan.json` 为来源，不是真源
- `coverage_first_traceability.json` 是主 traceability 真源
- `traceability_adapter.json` 是兼容层

## Cursor 适配边界

Cursor 适配层可以处理：

- 编辑器规则加载
- 子代理组织
- MCP 连接方式
- 当前会话模型使用

Cursor 适配层不应改写：

- 流程角色
- testcase 真源
- traceability 真源
- review gate 口径
