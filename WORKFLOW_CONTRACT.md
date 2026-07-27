# WORKFLOW CONTRACT

本文档定义 AI Test Pipeline 的正式流程契约。

目标：

- 让流程资产与模型解耦
- 让仓库定义规则，而不是定义模型或品牌
- 让不同宿主工具都消费同一套流程入口与产物契约

## 1. 角色契约

仓库内正式流程角色以 `AGENTS.md` 为准：

- `PRD Structurer`
- `Case Generator`
- `Case Reviewer`
- `Asset Formatter`

这些是流程角色，不是宿主工具角色。

任何宿主工具都应把这些角色视为仓库流程角色，而不是重命名成自己的私有流程。

## 2. 资产层契约

### 流程资产层

核心资产：

- `AGENTS.md`
- `START_HERE.md`
- `WORKFLOW_CONTRACT.md`
- `docs/`
- `schemas/`
- `prompts/`
- `scripts/`

原则：

- 这些内容应尽量保持跨工具通用
- 这些内容不应要求某一个固定模型
- 这些内容不应默认绑定某一个固定 provider

### 宿主适配层

适配目录：

- `tool_adapters/codex/`
- `tool_adapters/cursor/`
- `tool_adapters/claude/`

原则：

- 宿主差异只放在这里
- 适配层不能重写核心流程
- 适配层只能解释如何把宿主接到核心流程

### 运行时模型层

原则：

- 当前会话模型由宿主环境决定
- 仓库只定义“如何消费运行时上下文”
- 模型、endpoint、凭证、执行方式属于 runtime concern，不属于流程真源

## 3. 输入契约

统一输入目录：

- 项目级公共输入：`assets/projects/<PROJECT_CODE>/inputs/common/`
- 工作项级：`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/`

图片输入建议：

- `inputs/images/`

中间证据层：

- `image_evidence/image_evidence_inventory.json`
- `analysis/reasoning_pack.json`

原则：

- 原始输入优先保留
- 不允许只保留最终结果而丢失可追溯中间层
- 正式主流程必须先产出 `inputs/requirement_summary.md`，见 `skills/requirement-summary/`
- `inputs/source_manifest.json` 必须记录实际消费的需求来源、外部链接、本地材料和访问状态；它是来源清单，不替代原始输入或 `requirement_summary.md`

项目资产模型：

- 项目根只保留 `project_manifest.json`、公共输入、派生索引、质量汇总、知识和 `work_items/`
- 正式 evidence、structured PRD、测试设计、testcase、traceability 与 review 只存在于工作项
- 项目级 indexes/reports 必须从工作项真源再生，不得反写工作项

## 4. 产物契约

### Structured PRD

- `structured_prd/structured_prd.md` 是 authoring 真源
- `structured_prd/structured_prd.json` 是机器投影

### Testcase

- `testcases/case_plan.md` 是正式用例前的可评审计划
- `testcases/case_plan.json` 是 case_plan 机器投影
- `testcases/testcases_main.md` 是主 testcase 真源
- `testcases/testcases.md` 是兼容镜像，可按需再生
- `testcases/testcase_bundle.json` 是 compatibility-only 结构化投影，由 `testcases_main.md` 派生，不反写真源，可按需再生
- `testcases/testpoints.md` / `testpoints.json` 与 `testcases_main.md` 在 Case Generator 主流程同步生成；它以 `case_plan.json` 为来源，可引用主用例补充上下文，但不反写 `case_plan` 或替代 `testcases_main.md`
- `testcases/field_audit.json` 是 audit item 派生产物，可按需再生或清理
- `testcases/grouped_audit.json` 是 grouped audit 派生产物，可按需再生或清理
- 正式 testcase 的步骤和预期结果应遵守 `rules/testcase_element_notation.md`，让页面、按钮、弹窗、字段、值、状态、提示语和技术字段具备稳定语义
- 正式 testcase 的标题、前置条件、步骤和预期结果应遵守 `rules/testcase_human_readable_style.md`，优先使用人工可读、可执行、可判断的表达，机器字段和 coverage/schema 语言只保留在备注或结构化追溯产物中
- 正式 testcase 的页面与板块分组应遵守 `rules/testcase_grouping_rules.md`：`testcases_main.md` 按 `page_name + section_name` 分表，表格内继续保留“所属模块 / 所属功能点”

### Test Design Decision Layer

- `acceptance/testability_gate.md` / `.json` 负责判断 structured_prd 规则是否可测、跳过、待确认、风险项或非本期范围
- `acceptance/acceptance_examples.md` / `.json` 使用 Given / When / Then 表达验收标准
- `design/verification_responsibility_map.md` / `.json` 负责 B端、C端、API、服务端强校验与风险加固的责任划分
- `design/test_design_matrix.md` / `.json` 是 L 档工作项的测试设计矩阵
- `design/design_feedback.md` / `.json` 承接 code review 映证反馈；反馈进入设计层，不直接覆盖 testcase

### Traceability

- `traceability/coverage_first_traceability.json` 是主真源
- `traceability/traceability_adapter.json` 是兼容层，可按需再生
- `traceability/traceability_matrix.json` 仅保留 legacy 对照角色，minimal retention 下可清理

### Review / Export

- `reviews/quality_report.json` 是质量报告真源
- `reviews/review_record.md` 是阅读友好型评审记录
- `feishu_ready.md` 是阅读友好型导出产物

## 5. 真源与兼容层契约

核心原则：

1. 真源先于兼容层
2. 兼容层不得反写真源
3. 兼容层只能服务旧消费方过渡

正式口径：

- `testcases_main.md` 决定主 testcase 世界
- `case_plan.json` 决定正式用例生成前的测试设计计划
- 正式 testcase 必须能追溯到 `case_plan_id`
- `testcases.md` 只为旧消费方、旧导出链路和阅读习惯提供兼容
- `testcase_bundle.json` 当前只作为结构化投影，必须保持 `projection_only=true` 且 `truth_source=testcases/testcases_main.md`
- `coverage_first_traceability.json` 决定主 traceability 世界
- `traceability_adapter.json` 只为旧消费方提供投影
- `traceability_matrix.json` 不再决定主门禁

## 5.1 产物保留策略

仓库支持两类保留策略：

- `full`：保留真源、兼容镜像、legacy 对照、审计 JSON、导出物和生成过程包，适合调试、迁移和问题复盘。
- `minimal`：长期保留输入归一化结果、结构化 PRD、测试设计决策层、case_plan、`testpoints.*`、`testcases_main.md`、主 traceability、review 结论和必要质量报告；兼容投影与过程产物可按需再生。

minimal 下可清理：

- `.generation/latest`
- `.generation/archive`
- `testcases/testcases.md`
- `testcases/testcase_bundle.json`
- `testcases/field_audit.json`
- `testcases/grouped_audit.json`
- `traceability/traceability_adapter.json`
- `traceability/traceability_matrix.json`
- `feishu_ready.md`
- `reviews/missing_rules.json`
- `reviews/missing_fidelity_points.json`
- `reviews/fidelity_hit_locations.json`
- `reviews/weak_cases.json`
- `reviews/generalized_cases.json`
- `reviews/duplicate_case_report.json`

清理入口：

```bash
/usr/bin/python3 scripts/cleanup_derived_artifacts.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --mode minimal
```

校验入口：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --retention minimal
```

`validate_work_item.py --retention auto` 会在 legacy traceability 已清理且主 traceability 存在时自动采用 minimal 主链校验。

## 6. 运行时契约

仓库只要求运行时提供以下信息，不要求固定来源：

- 当前模型名，可为空
- 当前 endpoint / base_url，可为空
- 当前凭证，可为空
- 当前执行器入口

工作项复杂度必须持久化为 `manifest.json.work_item_level`。有效档位解析顺序为：

```text
命令行 --work-item-level 显式覆盖 > manifest.json.work_item_level > 默认 M
```

重生成任务包应记录本轮有效档位，执行后的校验必须复用该档位，避免生成与校验档位不一致。

解析优先级由宿主适配层决定，核心流程不规定品牌。

允许的运行时来源包括但不限于：

- 当前会话上下文
- 本地配置文件
- 环境变量
- 宿主适配层提供的 runtime context
- 本地命令执行器

## 7. 脚本契约

核心脚本的职责：

- 处理流程资产
- 生成任务包
- 校验产物
- 构建兼容层
- 导出阅读友好产物

核心脚本不应承担：

- 宿主品牌绑定
- 固定模型选择
- 固定 provider 选择

若脚本存在历史兼容参数，例如 `provider=openai|command|existing`，应视为兼容实现入口，而不是正式流程真源。

Validator 目录规则：

- 只校验单个 Skill 阶段产物的 validator 放在 `skills/<skill>/scripts/`。
- 跨阶段映射、兼容投影、工作项聚合门禁保留在根 `scripts/`。
- 已公开使用的旧根目录命令可保留轻量兼容 wrapper，但仓库内部新引用必须使用 Skill 路径。

## 8. Prompt 契约

`prompts/` 必须满足：

- 模型无关
- 宿主无关
- provider 无关
- 优先描述角色、输入、输出、约束

不应出现：

- 固定品牌模型名
- 固定宿主行为假设
- 固定 provider 要求

## 8.1 测试设计决策层契约

structured_prd 到 testcase 的推荐链路为：

```text
structured_prd
  -> testability_gate
  -> acceptance_examples
  -> verification_responsibility_map
  -> case_plan
  -> testcases
```

普通小需求可走轻量链路：

```text
structured_prd -> testability_gate -> case_plan -> testcases
```

M/L strict 工作项推荐链路：

```text
structured_prd -> testability_gate -> acceptance_examples -> case_plan -> testcases
```

L 档 strict 额外启用责任划分门与测试设计矩阵：

```text
structured_prd -> testability_gate -> acceptance_examples -> verification_responsibility_map -> test_design_matrix -> case_plan -> testcases
```

约束：

1. `technical_background` 不得生成正式业务用例。
2. `soft_prompt` 只能生成提示展示/页面展示类计划，不得升级为 hard_block。
3. `risk_note` / `api_guard` 不得混入 `product_acceptance` 主用例池。
4. code review 映证结果反馈到 design 层，不直接覆盖 testcase。
5. 正式 testcase 必须显式引用 `case_plan_id`，当前兼容写法为 testcase 备注中的 `来源 CasePlan：CP-xxx` 或 `case_plan_id=CP-xxx`。
6. `validate_work_item.py` 默认只读；刷新 `reviews/quality_report.json` 必须显式传 `--write-report`。
7. M/L strict 下，`case_plan.source_example_ids` 必须指向存在的 `acceptance_examples.example_id`，且 example 的 source gates 必须与 case_plan 的 source gates 对齐。
8. S 档 strict 可兼容仅 `testability_gate -> case_plan` 的轻量链路。
9. L strict 下，`verification_responsibility_map.responsibilities` 不能为空，`case_plan.source_responsibility_ids` 必须指向存在的 responsibility。
10. L strict 下，responsibility 的 `source_rule_id` 必须来自 `testability_gate`，且 case_plan 引用的 responsibility 必须与自身 `source_gate_ids` 对应规则一致。
11. S/M/L 执行策略只控制当前阶段强制产物：S 强制 testability/case_plan；M 额外强制 acceptance_examples；L 额外强制 verification_responsibility_map 与 test_design_matrix。
12. L strict 下，`test_design_matrix.items` 不能为空，矩阵项必须引用存在的 gate/example/responsibility/case_plan，且所有生成正式用例的 case_plan 必须被矩阵覆盖。
13. code review confirmation 产生的修订建议应写入 `design/design_feedback.json`，目标层只能是测试设计决策层产物，不得直接覆盖 `testcases_main.md`。
14. 元素标注规范是正式 testcase 可读性、可评审性和自动化映射的一部分；非 strict 可 warning，strict 可在显式启用后作为质量门。
15. testcase grouping 规范是正式 testcase 可读性和可追溯性的一部分；`page_name / section_name` 应从 structured_prd、coverage、case_plan 到 testcase 持续保留，strict 会逐步禁止缺页面、缺板块和弱兜底分组。
16. 人工可读表达风格是正式 testcase 面向人工执行的一部分；不得用“语义等价 / 结构化规则一致 / 字段展示正确 / 功能正常”等抽象词替代可观察结果，也不得把业务字段写成技术字段。
17. strict 主流程必须存在非模板 `inputs/requirement_summary.md` 和至少一条真实来源的 `inputs/source_manifest.json`。
18. Case Generator 必须在同一轮同步生成 `testpoints.*` 与 `testcases_main.md`；strict 下测试点必须覆盖全部 case_plan，生成正式用例的测试点必须保留页面与板块上下文。
19. `manifest.json.work_item_level` 是工作项长期档位配置；CLI 只做本轮显式覆盖，重跑 bundle 与统一校验必须复用同一有效档位。
20. reasoning 层必须显式读取 requirement summary 和 source manifest；image evidence 是图片型需求的增强输入，不是纯文本需求的前置阻塞。
21. S/M/L bundle 必须携带对应测试设计资产；测试设计阶段在任务包中独立于 Case Generator。
22. Case Plan 必须提供 coverage 或稳定 testcase 映射；存在活跃计划但 coverage 为空或无候选匹配时，生成器必须失败，禁止空结果覆盖主用例。
23. quality report 必须记录 structured PRD、coverage、testcase 与主 traceability 指纹；默认只读校验发现指纹变化时要求显式刷新。

## 9. Skill 契约

`skills/` 必须满足：

- 解释如何执行仓库流程角色
- 遵循当前真源口径
- 不把旧兼容层误写成主真源
- 阶段内部 validator 与 Skill 共址；Reasoning Analysis、Coverage Planning 等正式阶段必须拥有对应 Skill 入口

## 10. 宿主适配契约

每个宿主适配 README 至少要说明：

1. 如何进入仓库
2. 如何读取 `START_HERE.md`
3. 如何让当前会话模型参与流程
4. 如何执行统一脚本入口
5. 哪些内容只是宿主差异，不是流程真源

## 11. 团队使用契约

### 普通测试同学

- 先看 `START_HERE.md`
- 只按统一输入目录、统一脚本、统一真源口径使用
- 不要求理解底层实现

### 核心维护人

- 维护 `docs/`、`schemas/`、`prompts/`、核心 `scripts/`
- 避免把宿主逻辑塞进核心层

### 平台维护人

- 维护 `tool_adapters/`
- 让不同宿主都能接入统一流程
- 不擅自改 testcase / coverage / traceability 核心算法

## 12. 验收标准

这份契约成立时，仓库应满足：

1. 仓库本身不要求某一个固定模型
2. 核心 prompt 不写死某一个品牌模型
3. 宿主用户都能通过 `START_HERE.md` 和 `tool_adapters/` 接入
4. 团队成员不需要理解全部底层实现，也能稳定使用
