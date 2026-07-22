# Codex Adapter

## 测试设计决策层

Codex 接入本仓库时应遵守核心流程真源：仓库定义流程，不定义模型。正式用例不再建议直接从 `structured_prd` 生成，而应经过：

```text
structured_prd -> testability_gate -> acceptance_examples -> verification_responsibility_map -> case_plan -> testcases
```

P0 最小链路为：

```text
structured_prd -> testability_gate -> case_plan -> testcases
```

正式交付建议执行：

```bash
python3 scripts/validate_work_item.py --project-code <PROJECT_CODE> --work-item-id <WORK_ITEM_ID> --strict
```

该命令默认只读，不刷新 `quality_report.json`。需要刷新报告时显式加 `--write-report`。正式 testcase 必须在备注中包含 `来源 CasePlan：CP-xxx` 或等价 `case_plan_id=CP-xxx`。

正式 testcase 的步骤和预期结果应遵守 `rules/testcase_element_notation.md`：页面 / Tab 用 `[]`，按钮 / 操作入口用 `【】`，弹窗 / 抽屉 / 面板用 `《》`，字段 / 列表列用 `“”`，枚举值 / 输入值用 `{}`，状态 / 结果用 `<>`，提示语 / Toast 用 `「」`，接口 / 参数用反引号。需要检查时可加 `--check-element-notation`；非 strict 只 warning，strict 且显式启用时阻塞明显未标注问题。

正式 testcase 还应遵守 `rules/testcase_grouping_rules.md`：`testcases_main.md` 按 `# 页面：xxx` + `## 板块：yyy` 输出多张表；“所属模块 / 所属功能点”是表格内列，不是唯一分表依据。`__page_name / __section_name` 是生成阶段隐藏分组字段，strict 会逐步禁止缺页面、缺板块和弱兜底分组。

P1-1 后，M/L strict 推荐链路为：

```text
testability_gate -> acceptance_examples -> case_plan -> testcases
```

`acceptance_examples` 用 Given / When / Then 定义验收标准；`case_plan` 优先从 `source_example_ids` 派生。S 档轻量需求可通过 `--work-item-level S` 不强制 acceptance examples。

L 档复杂需求可通过 `--work-item-level L` 启用轻量责任划分门：`verification_responsibility_map` 必须非空，`case_plan.source_responsibility_ids` 必须指向存在且与 gate 规则一致的 `responsibility_id`。

code review 映证结果应反馈到 `design/` 层，不直接覆盖正式 testcase。

这份说明只解释：在 Codex 中，如何接入仓库已经定义好的统一流程。

它不重新定义 testcase、coverage、traceability 或 review 逻辑。

## 适用原则

- 使用当前 Codex 会话模型
- 仓库不要求你在命令里写死模型名
- 先遵守 `START_HERE.md` 和 `WORKFLOW_CONTRACT.md`

## 你该怎么开始

1. 阅读仓库根目录的 `START_HERE.md`
2. 阅读 `AGENTS.md`
3. 需要深入维护时再看 `WORKFLOW_CONTRACT.md`

## Codex 下的推荐用法

- 把当前聊天窗口当作运行时上下文
- 让 Codex 使用当前会话模型完成仓库流程角色
- 优先使用仓库里的统一脚本入口，而不是临时手写一套私有流程

## 最小流程

```bash
/usr/bin/python3 scripts/create_work_item.py --project-code WX-YYPT --work-item-id REQ-001
# 主流程先执行：skills/requirement-summary/ → inputs/requirement_summary.md + source_manifest.json
/usr/bin/python3 scripts/prepare_regeneration_run.py --project-code WX-YYPT --work-item-id REQ-001
/usr/bin/python3 scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001
```

Codex 可选 agent 配置见 `tool_adapters/codex/requirement-summary.agent.yaml`。

## Codex 特有能力

Codex 可能提供：

- 当前线程上下文
- 当前会话模型
- 桌面端工具能力
- 本地命令与文件协作能力

这些能力属于宿主适配层，不属于仓库流程真源。

## 你不需要做什么

- 不需要把 `gpt-5.4` 或其他模型名写进 prompt
- 不需要把 Codex 的私有行为写进 `prompts/`
- 不需要把 Codex 专属逻辑塞回 testcase 主链

## 真源口径

- `testcases_main.md` 是主 testcase 真源
- `testcases.md` 是兼容镜像
- `testpoints.md/json` 与正式用例同步生成，以 `case_plan.json` 为来源，不是真源
- `coverage_first_traceability.json` 是主 traceability 真源
- `traceability_adapter.json` 是兼容层

## 若需要实现 Codex 专属运行时桥接

请只在适配层处理：

- 当前线程模型读取
- 本地配置读取
- 凭证解析
- 运行时上下文传递

不要把这些逻辑重新写回核心流程契约。
