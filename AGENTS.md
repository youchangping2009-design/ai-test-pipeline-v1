# AGENTS

## Codex Autonomous Execution Protocol

Codex 在本仓库中工作时，必须优先遵守本协议。本协议用于让 Codex 通过仓库内的规则、队列、下一步任务和验收命令自驱动推进，不依赖用户在 ChatGPT 与 Codex 之间搬运上下文。

### Startup Read Order

每次开始任务前，Codex 必须先读取：

1. `START_HERE.md`
2. `WORKFLOW_CONTRACT.md`
3. `docs/roadmap/NEXT_ACTION.md`
4. `docs/roadmap/WORK_QUEUE.md`
5. `docs/roadmap/DECISION_LOG.md`

必要时再读取：

- `docs/autonomous_execution.md`
- `docs/workflow.md`
- `docs/operating_sop.md`
- 任务涉及的 `schemas/`、`skills/`、`scripts/`

### Task Selection

1. 每次任务开始前，先读取 `docs/roadmap/NEXT_ACTION.md`。
2. 如果 `NEXT_ACTION.md` 中任务未完成，优先执行该任务。
3. 如果 `NEXT_ACTION.md` 为空、已完成或阻塞，从 `docs/roadmap/WORK_QUEUE.md` 选择最高优先级 `todo` 任务。
4. 执行前必须输出简短计划。
5. 修改前必须确认不涉及业务代码。
6. 每轮只执行一个阶段，不跨阶段顺手大改。

### Execution Guardrails

1. 不允许修改业务代码。
2. 不允许绕过 strict gate。
3. 不允许降低规则强度来通过校验。
4. 不允许把 `risk_note` / `api_guard` 混入 `product_acceptance` 主用例。
5. 不允许把 `soft_prompt` 升级为 `hard_block`。
6. 不允许把 `technical_background` 生成正式业务用例。
7. 不允许无 `case_plan_id` 的正式 testcase 进入 strict。
8. 不允许切换 testcase 真源，除非 roadmap 明确进入 P3。
9. 不允许删除旧流程兼容逻辑。
10. code review 映证结果应反馈到 design 层，不直接覆盖 testcase。

### Validation And Repair

1. 修改后必须运行任务对应校验；默认至少运行：

   ```bash
   /usr/bin/python3 scripts/run_quality_baseline.py
   ```

2. 校验失败时允许自动 repair，但最多 2 轮。
3. repair 必须基于失败信息做最小修复，不得通过降低规则强度绕过失败。
4. 2 轮 repair 后仍失败时，不继续盲改，写入 `docs/roadmap/HUMAN_ACTION_REQUIRED.md`。

### Completion Record

完成任务后，Codex 必须：

1. 更新 `docs/roadmap/NEXT_ACTION.md` 的任务状态或下一步建议。
2. 如产生新的关键决策，更新 `docs/roadmap/DECISION_LOG.md`。
3. 如存在真实阻塞，更新 `docs/roadmap/HUMAN_ACTION_REQUIRED.md`。
4. 在最终回复中说明新增/修改文件、校验命令与结果、剩余风险。

本仓库中的 AI Agent 分工如下：

## 1. PRD Structurer
负责将原始 PRD、截图、补充描述转为结构化 PRD。

需求接入与归一化是正式主流程第一阶段。所有工作项都应使用 `skills/requirement-summary/` 产出 `inputs/requirement_summary.md`，并用 `inputs/source_manifest.json` 记录实际消费的来源及访问状态，再进入 `prd-structuring`。需求整理只归一化输入，不替代 `structured_prd`、`testability_gate` 或 `case_plan`。

## 2. Case Generator
负责基于测试设计决策层产出标准测试用例。正式用例不再建议直接从 structured_prd 临时生成，而应从 `testcases/case_plan.json` / `case_plan.md` 派生。

## 3. Case Reviewer
负责检查覆盖率、逻辑完整性、字段约束、异常场景、边界场景。

## 4. Asset Formatter
负责输出格式整理，适配飞书、Markdown、JSON 等目标格式。

以上 4 个角色都是仓库定义的流程角色，不绑定具体宿主工具，也不绑定具体模型。

## 基本要求

- 不遗漏 PRD 信息
- 所有产出可追溯
- 所有规则以仓库内 schema / rules / templates 为准
- 不直接修改业务代码
- 仓库定义流程，不定义模型；当前模型由当前宿主会话决定

## 总控约束

你在这个仓库中工作时，始终遵守以下规则：

1. 目标不是“写得像文档”，而是“让规则可执行”
2. 优先保真，不要为了抽象优雅而丢失字段级规则
3. 对于后台配置页类需求，字段/条件/约束/数据源优先于页面/模块/流程抽象
4. 新结构优先，小心保持向后兼容
5. 每次只做一个阶段，不跨阶段顺手大改
6. 任何改动都尽量补最小验证
7. 若发现 structured_prd.md -> structured_prd.json 编译会丢规则，优先修这里
8. 生成测试用例时，优先从 fields[] 与 rules[] 展开，不要用自然语言总结替代规则执行
9. 避免生成泛化用例标题，例如“检查字段矩阵完整性”“验证页面配置正确”
10. 用例应尽量做到单规则单断言，再补少量主流程组合场景
11. 对于无法自动确定的规则，宁可显式标记缺失，也不要自行脑补
12. 所有改动保持小步、可审查、可回滚
13. structured_prd 到正式用例之间必须经过测试设计决策层：`testability_gate -> acceptance_examples -> verification_responsibility_map -> case_plan`
14. P0 正式交付至少要求 `testability_gate` 与 `case_plan`；`acceptance_examples` 与 `verification_responsibility_map` 可按工作项复杂度启用
15. code review 映证结论应反馈到 design 层，不直接覆盖正式 testcase
16. 正式测试用例中的关键页面、按钮、弹窗、字段、值、状态、提示语和技术字段应遵守 `rules/testcase_element_notation.md`
17. 正式测试用例必须遵守 `rules/testcase_grouping_rules.md`：最终 `testcases_main.md` 按“页面 + 板块”分表，表格内继续保留“所属模块 / 所属功能点”列。
18. 正式测试用例的标题、前置条件、测试步骤和预期结果应遵守 `rules/testcase_human_readable_style.md`，优先写成人工可读、可执行、可判断的表达。
19. `inputs/requirement_summary.md` 与 `inputs/source_manifest.json` 是主流程正式产物，strict 必须校验；它们不得替代原始输入，`prd-structuring` 必须优先消费归一化结果。
20. `testcases/testpoints.md` / `testpoints.json` 与 `testcases_main.md` 必须在 Case Generator 主流程中同步生成。测试点以 `case_plan.json` 为来源，可引用主用例补充页面/板块上下文，但不得替代 `case_plan` 或 `testcases_main.md`。
21. 工作项复杂度必须持久化到 `manifest.json.work_item_level`；执行优先级为命令行显式覆盖 > manifest > 默认 M，生成与校验必须使用同一有效档位。
22. `reasoning_pack` 必须显式消费 `requirement_summary.md` 与 `source_manifest.json`；纯文本需求不得因缺少 image evidence 被阻塞。
23. `should_generate_case=true` 的 Case Plan 必须提供 `source_coverage_ids` 或稳定的 `generated_testcase_ids`，否则不得进入正式用例生成。
24. bundle 后处理必须刷新 testcase bundle、testpoints、开发自测、traceability 与 quality report；旧质量报告指纹与当前主产物不一致时必须失败。

# Case Generation Rules

1. 生成测试用例时，优先执行 case_plan，不要绕过 case_plan 直接总结 structured_prd。
2. 对配置页需求，优先按字段和规则展开，不要优先按页面描述归纳。
3. 禁止使用“字段矩阵完整性”“字段条件联动”“页面配置正确”作为主要测试用例标题。
4. 每条测试用例尽量只验证一个规则，做到单规则单断言。
5. 字段规则至少覆盖：
   - 基础属性
   - 必填
   - 边界值
   - 异常值
   - 条件展示
   - 条件必填
   - 条件只读/可编辑
   - 数据源过滤/展示格式/排序
6. 组合主流程只能作为补充，不能替代原子规则层。
7. 对无法确认的规则，显式标记缺失，不要脑补。
8. 生成结果必须保持现有 testcase 表结构兼容。
9. 正式 testcase 必须能追溯到 `case_plan_id`，可通过 `case_plan.generated_testcase_ids` 或 testcase 备注中的 `来源 CasePlan：CP-xxx` 表达。
10. `soft_prompt` 只能生成提示展示/页面展示类计划，不得自动升级为保存失败、提交失败、强拦截类用例。
11. `technical_background` 不得生成正式业务测试用例。
12. 测试步骤和预期结果中的关键元素必须尽量使用统一标注：页面/Tab 用 `[]`，按钮/入口用 `【】`，弹窗/抽屉/面板用 `《》`，字段/列表列用 `“”`，枚举值/输入值用 `{}`，状态/结果用 `<>`，提示语/Toast 用 `「」`，接口/参数/技术字段用反引号。
13. 生成用例时先确定 `page_name`，再确定 `section_name`，再确定 `module_name / feature_name`；禁止生成没有页面/板块上下文的正式用例。
14. B端配置影响C端时，C端用例的 `page_name` 应为C端页面；风险/API兜底用例不得混入正常产品验收页面板块。
15. 若需求文字未描述“必填/必选/不能为空/必须选择/必传”等强制要求，且原型图未出现必填星号 `*` 或等价标识，则字段默认按非必填处理；不得仅因控件为单选/多选/筛选项就生成“为空保存失败 / 必填拦截 / 不可提交”类用例。
16. 用例正文不得用“语义等价 / 结构化规则一致 / 字段展示正确 / 功能正常”等抽象词替代具体可观察结果；业务字段使用中文引号标注，接口、参数、技术字段才使用反引号。
