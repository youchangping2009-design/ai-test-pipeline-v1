# START HERE（Windows / PowerShell）

本文档是根目录 `START_HERE.md` 的 **Windows 命令行适配版**：将其中 `/usr/bin/python3` 与 bash 续行，改为在 **PowerShell** 下可直接复制执行的写法。

- 正文与真源口径与 `START_HERE.md` 一致；若两处有出入，以 `START_HERE.md` 为准。
- 默认使用 `python`。若本机只有 Python Launcher，可将 `python` 换成 `py -3`。
- 请在仓库根目录执行下列命令（例如 `D:\project\AI\ai-test-pipeline-v1`）。

---

这是 AI Test Pipeline 的统一入口页。

这个仓库定义的是流程、协议、校验口径和产物真源，不定义你必须使用哪个模型、哪个 provider、哪个宿主工具。

无论你在 Codex、Cursor、Claude 还是其他本地工具中工作，都先看 `START_HERE.md` 或本文件，再进入对应适配说明。

## 先记住 4 条

1. 仓库定义流程，不定义模型。
2. 当前宿主工具决定当前会话模型；仓库只消费运行时上下文。
3. `testcases_main.md` 是主 testcase 真源，`testcases.md` 只是兼容镜像。
4. `coverage_first_traceability.json` 是主 traceability 真源，`traceability_adapter.json` 是兼容层。
5. 正式用例不再建议直接从 `structured_prd` 生成；应先经过 `testability_gate` 与 `case_plan`。
6. 正式用例步骤和预期中的关键元素应遵守 `rules/testcase_element_notation.md`。

## 三层结构

### A. 流程资产层

核心目录：

- `AGENTS.md`
- `START_HERE.md`
- `WORKFLOW_CONTRACT.md`
- `docs/`
- `schemas/`
- `prompts/`
- `scripts/`

作用：

- 定义流程角色
- 定义输入输出协议
- 定义真源与兼容层
- 定义校验入口
- 定义重跑与回归脚本

### B. 宿主适配层

入口目录：

- `tool_adapters/codex/`
- `tool_adapters/cursor/`
- `tool_adapters/claude/`

作用：

- 告诉不同工具的用户如何接入同一套流程
- 只描述宿主差异，不重写仓库流程

### C. 运行时模型层

原则：

- 仓库不写死模型名
- 仓库不写死 provider
- 当前会话 / 本地运行环境决定模型、凭证和调用方式

## 先看什么

### 普通测试同学

按这个顺序：

1. `AGENTS.md`
2. `START_HERE.md`
3. `docs/operating_sop.md`
4. 你所在宿主的 `tool_adapters/<host>/README.md`

你主要关心：

- 如何初始化项目 / 工作项
- 输入资料放哪里
- 主产物看哪里
- 怎么执行统一校验

### 核心维护人

按这个顺序：

1. `AGENTS.md`
2. `WORKFLOW_CONTRACT.md`
3. `docs/workflow.md`
4. `schemas/`
5. `scripts/`

你主要关心：

- 角色边界
- 输入输出契约
- 真源与兼容层
- 统一校验和回归入口

### 平台维护人

按这个顺序：

1. `WORKFLOW_CONTRACT.md`
2. `tool_adapters/`
3. `scripts/`

你主要关心：

- 如何让不同宿主接入同一流程
- 如何传递运行时上下文
- 如何避免把宿主逻辑塞回核心层

## 当前真源口径

### PRD

- `structured_prd/structured_prd.md` 是 authoring 真源
- `structured_prd/structured_prd.json` 是机器投影

### Testcase

- `testcases/case_plan.md` 是正式用例前的人工评审计划
- `testcases/case_plan.json` 是 case_plan 机器投影
- `testcases/testcases_main.md` 是主 testcase 真源
- `testcases/testcases.md` 是兼容镜像
- `testcases/testcase_bundle.json` 是从 `testcases_main.md` 派生的 compatibility-only 结构化投影，不是真源
- `testcases/field_audit.json` 与 `testcases/grouped_audit.json` 是审计产物
- `testcases_main.md` 按 `# 页面：xxx` + `## 板块：yyy` 分表；“所属模块 / 所属功能点”是表格内列，不是唯一分表依据
- testcase row 的 `__page_name / __section_name` 是隐藏分组字段，用于渲染和校验；规则见 `rules/testcase_grouping_rules.md`

### Test Design

- `acceptance/testability_gate.md` / `.json` 是 structured_prd 到测试设计的第一道门
- `acceptance/acceptance_examples.md` / `.json` 用 Given / When / Then 定义验收标准
- `design/verification_responsibility_map.md` / `.json` 明确 B端 / C端 / API / 风险责任
- `design/test_design_matrix.md` / `.json` 是 L 档工作项的测试设计矩阵
- `design/design_feedback.md` / `.json` 承接 code review 映证反馈，不直接覆盖 testcase

### Traceability

- `traceability/coverage_first_traceability.json` 是主 traceability 真源
- `traceability/traceability_adapter.json` 是兼容层
- `traceability/traceability_matrix.json` 仅作为 legacy 对照

### Review

- `reviews/quality_report.json` 是质量报告真源
- `reviews/review_record.md`、`feishu_ready.md` 是阅读友好型派生产物

## 最小使用方式

### 1. 初始化项目

```powershell
python scripts/init_project.py --project-code WX-YYPT
```

（可选：同时写上名称与业务线，便于 README 占位。）

```powershell
python scripts/init_project.py --project-code WX-YYPT --project-name "测试项目" --business-line "广告业务"
```

### 2. 初始化工作项

```powershell
python scripts/create_work_item.py `
  --project-code WX-YYPT `
  --work-item-id REQ-001
```

单行等价：

```powershell
python scripts/create_work_item.py --project-code WX-YYPT --work-item-id REQ-001
```

### 3. 放入输入资料

放到：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/`

若输入主要是图片，再放到：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/images/`

### 4. 生成任务包

```powershell
python scripts/prepare_regeneration_run.py `
  --project-code WX-YYPT `
  --work-item-id REQ-001
```

单行等价：

```powershell
python scripts/prepare_regeneration_run.py --project-code WX-YYPT --work-item-id REQ-001
```

### 5. 用当前宿主工具执行同一流程

这一步不要求你在仓库里写死模型名。

请根据你所在工具查看：

- `tool_adapters/codex/README.md`
- `tool_adapters/cursor/README.md`
- `tool_adapters/claude/README.md`

### 6. 执行统一校验

```powershell
python scripts/validate_work_item.py `
  --project-code WX-YYPT `
  --work-item-id REQ-001
```

单行等价：

```powershell
python scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001
```

正式交付 / CI 建议启用严格模式：

```powershell
python scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001 --strict
```

当前 PT083 正式工作项已作为 strict 正向样例：

```powershell
python scripts/validate_work_item.py --project-code WX-YGJ --work-item-id PT083 --skip-code-reviews --strict
```

如需检查正式用例元素标注，可显式启用：

```powershell
python scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001 --check-element-notation
```

非 strict 下标注问题只输出 warning；strict 且显式启用时，明显未标注问题会失败。旧工作项默认保持兼容。

`validate_work_item.py` 默认只读，不刷新 `reviews/quality_report.json`。如确需重新生成质量报告，必须显式增加 `--write-report`：

```powershell
python scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001 --write-report
```

## 产物保留策略

工作项支持 minimal retention，用于减少过程产物和派生投影的长期堆积。长期必须保留的是真源和评审源，例如：

- `inputs/`
- `manifest.json`
- `structured_prd/`
- `acceptance/`
- `design/`（复杂需求或有代码映证反馈时）
- `testcases/case_plan.*`
- `testcases/testcases_main.md`
- `evidence/`
- `image_evidence/`（图片型需求）
- `traceability/coverage_first_traceability.json`
- `reviews/review_record.md`
- `reviews/quality_report.json`

可清理再生的派生产物包括：

- `.generation/latest`
- `.generation/archive`
- `testcases/testcases.md`
- `testcases/testcase_bundle.json`
- `testcases/field_audit.json`
- `testcases/grouped_audit.json`
- `traceability/traceability_adapter.json`
- `traceability/traceability_matrix.json`
- `feishu_ready.md`
- `reviews/missing_*.json`
- `reviews/fidelity_*.json`
- `reviews/weak_cases.json`
- `reviews/generalized_cases.json`
- `reviews/duplicate_case_report.json`

清理命令：

```powershell
python scripts/cleanup_derived_artifacts.py `
  --project-code WX-YYPT `
  --work-item-id REQ-001 `
  --mode minimal
```

单行等价：

```powershell
python scripts/cleanup_derived_artifacts.py --project-code WX-YYPT --work-item-id REQ-001 --mode minimal
```

minimal 校验：

```powershell
python scripts/validate_work_item.py --project-code WX-YYPT --work-item-id REQ-001 --retention minimal
```

strict 模式会阻止：

- 空模板 `testability_gate`
- 空模板 `case_plan`
- 仍含 TODO / TEMPLATE / 待补充 / 示例值的弱产物
- 无真实 testcase
- testcase 未显式引用 `case_plan_id`
- 引用不存在的 `case_plan_id`
- risk_note / api_guard / security_hardening 混入主验收用例
- code review 映证结果直接覆盖 `testcases_main.md`

P1-2 后，M/L strict 推荐链路为：

```text
testability_gate -> acceptance_examples -> case_plan -> testcases
```

其中 `acceptance_examples` 负责定义 Given / When / Then 和 oracle；`case_plan` 优先从 acceptance examples 派生。S 档轻量需求可以显式使用 `--work-item-level S`，不强制 acceptance examples。

L 档 strict 额外要求：

- `design/verification_responsibility_map.json` 非空且不能停留在模板占位值
- `design/test_design_matrix.json` 非空且不能停留在模板占位值
- `case_plan.source_responsibility_ids` 必须指向存在的 `responsibility_id`
- responsibility 的 `source_rule_id` 必须能回到 `testability_gate.source_rule_id`
- `case_plan.source_responsibility_ids` 必须与 `source_gate_ids` 对应规则一致
- `consumer_verification_required=true` 的规则必须在 case_plan 中存在 linkage 类计划
- 生成正式用例的 `case_plan_id` 必须被 `test_design_matrix.items` 覆盖

S/M/L 当前执行策略：

- S: `testability_gate -> case_plan -> testcases`
- M: `testability_gate -> acceptance_examples -> case_plan -> testcases`
- L: `testability_gate -> acceptance_examples -> verification_responsibility_map -> test_design_matrix -> case_plan -> testcases`

## 不该做什么

- 不要把模型名写进仓库流程说明
- 不要把宿主专属行为写进核心 prompt
- 不要把 `testcases.md` 当主真源继续传播
- 不要把 `traceability_matrix.json` 当主门禁真源继续传播
- 不要让正式 testcase 绕过 `case_plan`
- 正式 testcase 必须在备注中显式引用 `来源 CasePlan：CP-xxx`，或使用等价 `case_plan_id=CP-xxx` 标记
- 不要把 `soft_prompt` 自动升级为 hard_block
- 不要把 `technical_background` 生成业务测试用例

## 下一步

- 想理解仓库契约，看 `WORKFLOW_CONTRACT.md`
- 想直接上手，看 `docs/operating_sop.md`
- 想接你当前的宿主工具，看 `tool_adapters/`
- Linux / macOS 命令写法仍以 `START_HERE.md` 为准
