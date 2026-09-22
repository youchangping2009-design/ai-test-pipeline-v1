# Decision Log

本文件只记录已经确定的关键决策，不记录执行流水账。

写法：

- `Confirmed Decisions` 只就地修订长期有效口径。
- 带日期的决策只追加到文末，禁止插到 `Confirmed Decisions` 后面冒充最新。
- 不把阶段流水账、校验命令或 Completion Notes 写进本文件。

## Confirmed Decisions

- 非 strict 模式必须兼容旧流程。
- strict 模式用于正式交付 / CI / 强质量门。
- `validate_work_item.py` 默认只读，不刷新任何产物。
- 刷新 `reviews/quality_report.json` 必须显式传 `--write-report`。
- 正式 testcase 必须追溯到 `case_plan_id`。
- P0 / P0.5 已完成。
- 下一阶段先做 P1-1，不直接做完整 P1。
- code review 映证结果应反馈到 design 层，不直接覆盖 testcase。
- `risk_note` / `api_guard` 不得混入 `product_acceptance` 主用例。
- `soft_prompt` 不得升级为 `hard_block`。
- `technical_background` 不得生成正式业务用例。
- `testcases/testcases_main.md` 当前仍是主 testcase 真源。
- 不允许切换 testcase 真源，除非 roadmap 明确进入 P3。

## Decision Format

后续新增决策时使用：

```text
YYYY-MM-DD - Decision Title
Decision:
Reason:
Impact:
```

## 2026-04-28 - P1-1-001 Completed

Decision:
`acceptance_examples` strict validation 已作为 P1-1-001 完成。M/L strict 下必须校验 acceptance examples；S 档 strict 保持轻量兼容。

Reason:
现有 schema、validator、`validate_work_item.py` 分级策略和 PT083 eval 已能阻止空/弱 acceptance examples、缺 Given/When/Then、inferred 缺依据、soft_prompt 强拦截和 technical_background 生成验收示例。

Impact:
下一步进入 P1-1-002，聚焦 case_plan 对 `source_example_ids` 的追溯，不重复扩大 P1 范围。

## 2026-04-28 - P1-1-002 Completed

Decision:
`case_plan` 到 `acceptance_examples` 的追溯校验已作为 P1-1-002 完成。M/L strict 下，生成正式用例的 case_plan 必须填写并校验 `source_example_ids`。

Reason:
`validate_case_plan.py` 已能阻止缺失 `source_example_ids`、引用不存在的 AE，以及 `case_plan.source_gate_ids` 与 example 的 `source_gate_ids` 完全不相关的情况。

Impact:
下一步进入 P1-1-003，聚焦 PT083 eval 中 acceptance examples required assertions 覆盖。

## 2026-04-28 - P1-1-003 Completed

Decision:
PT083 eval 的 acceptance examples required assertions 已作为 P1-1-003 完成。

Reason:
`required_assertions.yml` 已覆盖特殊区 hard_block acceptance example、宣传图片 soft_display acceptance example、0元商品/免费体验 business_behavior/linkage acceptance example、SDK/720*1280 禁止生成 acceptance example、goodsRegion 禁止进入主验收 acceptance example。`run_evals.py` 会执行 required assertions，并调用 expected acceptance/case_plan validators。

Impact:
P1-1 阶段闭环完成。下一步进入 P1-2-001，聚焦 `verification_responsibility_map` 深度校验，但仍不得切换 testcase 真源。

## 2026-04-28 - P1-2-001 Completed

Decision:
`verification_responsibility_map` 深度校验已作为 P1-2-001 完成，范围限定为 L strict 责任划分最小强校验。

Reason:
责任图 validator 已能根据 `testability_gate` 分类阻止 soft_prompt 升级写侧/API/风险责任、technical_background 生成责任、linkage 缺 C端消费责任、risk/API 类缺 api_guard/risk_note，以及 consumer verification 缺 linkage case_plan。

Impact:
下一步进入 P1-3-001，聚焦 S/M/L work_item_level 执行策略，不推进 test_design_matrix 或 testcase 真源迁移。

## 2026-04-28 - P1-3-001 Completed

Decision:
S/M/L work_item_level 执行策略已作为 P1-3-001 明确。S strict 强制 `testability_gate + case_plan`，M strict 额外强制 `acceptance_examples`，L strict 额外强制 `verification_responsibility_map`。

Reason:
`validate_work_item.py` 已在日志中输出 level policy；`run_submission_pipeline.py` 的 `--stop-at` 已补齐 `verification_responsibility_map` 和 `test_design_matrix` 预留停点；文档已明确 `test_design_matrix` 尚未进入 strict gate。

Impact:
下一步进入 P1-4-001，聚焦 eval fixture expansion，避免 PT083 单样例过拟合。

## 2026-04-28 - P1-4-001 Completed

Decision:
eval fixture expansion 已作为 P1-4-001 完成，新增提示类、跨端链路类、风险/API 类三个最小 fixture。

Reason:
`PROMPT_ONLY`、`LINKAGE_ONLY`、`RISK_API_ONLY` 已复用 `scripts/run_evals.py`，并通过 forbidden patterns、required patterns、required assertions 与现有 validator 组合校验。

Impact:
下一步进入 P1-5-001，聚焦 L 档 `test_design_matrix` strict 接入；不得切换 testcase 真源。

## 2026-04-28 - P1-5-001 Completed

Decision:
L strict 已正式接入 `design/test_design_matrix.json`，但不改变 `testcases_main.md` 当前主 testcase 真源。

Reason:
`test_design_matrix` validator 能阻止空模板、占位弱矩阵、无效来源引用，并要求所有生成正式用例的 case_plan 被矩阵覆盖。

Impact:
下一步进入 P1-6-001，聚焦 code review 映证结果反馈到 design 层的 `design_feedback` 入口；不得直接覆盖 testcase。

## 2026-04-28 - P1-6-001 Completed

Decision:
code review 映证反馈进入 `design/design_feedback.json`，目标层限定为测试设计决策层产物，不直接覆盖 testcase。

Reason:
`design_feedback` validator 会阻止 target_layer 直接指向 testcase，并要求 `must_not_directly_overwrite_testcase=true`。空模板保留兼容性，非空项执行强校验。

Impact:
下一步进入 P2-001，聚焦有限 repair loop；不得绑定具体模型或通过降低规则强度绕过 strict gate。

## 2026-04-28 - P2-001 Completed

Decision:
仓库新增命令型有限 repair loop，支持 expected pass / expected fail，最多 2 轮 repair。

Reason:
repair loop 必须保持宿主无关与模型无关；脚本只负责任务编排、结果判定和人工阻塞记录，不自动降低规则强度。

Impact:
下一步进入 P2-002，聚焦 eval 多 fixture 运行入口与 fixture 索引。

## 2026-04-28 - P2-002 Completed

Decision:
eval 支持 `scripts/run_evals.py --all`，并维护 fixture 索引。

Reason:
当前已经存在 PT083、PROMPT_ONLY、LINKAGE_ONLY、RISK_API_ONLY 多个 fixture，需要一键回归入口防止只跑单一 golden 样例。

Impact:
下一步进入 P3-001。由于 P3 涉及 testcase 真源迁移，实际切换前必须获得人工确认。

## 2026-04-28 - P3-001 Evaluation Blocked

Decision:
`testcase_bundle.json` 真源迁移已完成评估，但实施被阻塞，等待人工确认。当前仍保持 `testcases/testcases_main.md` 为主 testcase 真源。

Reason:
切换 testcase 真源会影响 validators、exporters、regeneration bundle、traceability builder 和团队交付习惯；任何 Agent 都不应自行切换。

Impact:
P3-001 暂停实施。推荐下一步由用户确认是否先进入 compatibility-only 阶段。

## 2026-04-28 - P3-001 Compatibility-Only Accepted

Decision:
用户确认先做 compatibility-only 阶段。`testcases/testcase_bundle.json` 作为从 `testcases_main.md` 派生的结构化投影落地，不切换 testcase 真源。

Reason:
这样可以先验证结构化 bundle 的稳定性和一致性，避免直接影响现有导出、traceability、review 和团队交付习惯。

Impact:
`testcases_main.md` 仍是主 testcase 真源；bundle 必须保持 `projection_only=true`，并通过与 markdown 的逐条一致性校验。

## 2026-04-28 - Roadmap Queue Drained

Decision:
当前 `WORK_QUEUE.md` 中 P1/P2/P3 已登记任务均已完成，`NEXT_ACTION.md` 保持 P3-001 done 状态作为最近完成任务记录。

Reason:
用户要求在无人工判断问题时循环执行到所有步骤完成；当前无 `todo` 任务且 `HUMAN_ACTION_REQUIRED.md` 无阻塞。

Impact:
后续继续自驱动前，应先新增下一阶段任务到 `WORK_QUEUE.md` 或更新 `NEXT_ACTION.md`。

## 2026-04-28 - PT083 Regenerated Strict Baseline

Decision:
PT083 已按测试设计决策层重新生成，补齐 `testability_gate`、`acceptance_examples`、`verification_responsibility_map`、`test_design_matrix`、`case_plan` 与从 `testcases_main.md` 派生的 `testcase_bundle.json`，并将 baseline 中 PT083 strict 预期从失败调整为通过。

Reason:
PT083 不再是历史弱产物样例；它现在作为完整 L 档 strict 正向工作项，用于验证 structured_prd -> testability_gate -> acceptance_examples -> case_plan -> testcases 的生成链路。

Impact:
`scripts/run_quality_baseline.py` 中 PT083 非 strict、PT083 strict、PT083 eval 均应通过。正式 testcase 继续以 `testcases_main.md` 为真源，`testcase_bundle.json` 仅作为兼容投影。

## 2026-04-29 - PT083 Strict Fixture Cleanup

Decision:
移除重复工作项文件集 `PT083_STRICT_PASS`，不再把它作为 baseline 的独立 strict 正向样例。

Reason:
PT083 正式工作项已经补齐 L 档 strict 所需设计层与用例层产物，可直接承担 strict 正向样例；继续在 `work_items/` 下保留 `PT083_STRICT_PASS` 会造成“同一需求两个版本”的交付口径混淆。

Impact:
`scripts/run_quality_baseline.py` 仅保留 PT083 non-strict、PT083 strict 与 PT083 eval 三项基线；正式 testcase 继续以 `testcases_main.md` 为真源，`testcase_bundle.json` 仅作为兼容投影。

## 2026-04-29 - PT081 Rerun Stability Finding

Decision:
PT081 当前交付用例继续以 141 条补强后的 `testcases/testcases_main.md` 为真源，不接受纯 `coverage_matrix -> testcase` 重跑得到的 111 条结果作为交付基线。

Reason:
纯规则重跑的 testcase 输出 hash 稳定，但会稳定漏掉 30 条补强用例，其中包含 banner / 弹窗 / 瓷片区 / 金刚区 4 类后台配置的真实新增、编辑、删除链路，导致 testcase lint 与工作项校验失败。

Impact:
已恢复补强用例并重新通过 PT081 校验。后续若要实现 PT081 无人工补丁稳定重跑，需要把 30 条补强用例的来源沉淀到测试设计层或生成规则中，尤其是后台配置页真实 CRUD 链路规则。

## 2026-04-29 - Backend Config Generic Generation Rules

Decision:
后台配置页真实 CRUD、容量限制、展示频次、跨字段约束、数据源过滤+排序组合断言，作为通用生成规则进入 `coverage_testcase_generator.py` 和 testcase lint，不再以 PT081 人工补丁形式存在。

Reason:
PT081 证明纯 coverage 生成会稳定漏掉高信号行为用例；这些缺口不是单需求特性，而是配置页类需求的共性：字段校验不能替代真实新增、编辑、删除和前后台联动验证。

Impact:
清理 PT081 派生产物后纯重跑产出 153 条主用例，质量门与 `validate_work_item` 通过。PT081 新规则基线从旧 141 条提升为 153 条；后续类似后台配置页需求可复用该抽象规则。

## 2026-04-29 - PT083 Rerun Stability Finding

Decision:
PT083 当前正式用例保持 18 条 `testcases/testcases_main.md` 作为真源，本次 regeneration bundle existing-provider 回放后不产生用例内容变化。

Reason:
PT083 当前链路是 L 档设计层产物回放稳定性验证，仓库尚无独立 `case_plan -> testcase` 自动生成器；用 coverage 直出替代正式用例会绕过当前已确认的 case_plan 主链路。

Impact:
新旧 `testcases_main.md` 与 `testcase_bundle.json` hash 完全一致，`validate_work_item --strict --work-item-level L` 和 `run_quality_baseline.py` 均通过。补齐缺失的 `reviews/duplicate_case_report.json` 作为 regeneration 完整性派生产物。

## 2026-04-29 - Testcase Grouping Rules Formalized

Decision:
正式 testcase 的 Markdown 分表依据确认为 `page_name + section_name`，表格内继续保留“所属模块 / 所属功能点”。`module_name / feature_name` 表达业务归属，不作为唯一分表依据。

Reason:
不同页面、同页不同业务板块、B端配置到C端消费链路、风险/API兜底用例需要稳定拆表，避免所有用例混入一张大表或被弱兜底到“添加弹窗”。

Impact:
新增 `rules/testcase_grouping_rules.md`、coverage entry 可选 `section_name`、`validate_testcase_grouping.py` 与 `CASE_GROUPING` eval。`validate_work_item.py --strict` 接入 grouping 校验；非 strict 保持 warning 兼容旧工作项。`testcases_main.md` 仍是主 testcase 真源。

## 2026-04-29 - PT083 Artifact Cleanup Rerun

Decision:
PT083 本次清理重跑采用当前已确认的 regeneration bundle 回放路径，不用 coverage 直出替代正式 testcase。

Reason:
临时 coverage 直出会产生重复编号、弱页面分组，并且缺少 `来源 CasePlan` 追溯，不能满足当前 strict 主链。PT083 的正式用例仍应以设计层 `case_plan` 已确认的 `testcases_main.md` 为真源。

Impact:
清理 PT083 可再生历史产物 11 项后，重建兼容镜像、审计产物、traceability adapter、feishu 导出与 testcase bundle。主用例保持 18 条、4 个页面/板块表；`validate_work_item --strict --work-item-level L` 与 `run_quality_baseline.py` 通过。

## 2026-04-29 - SC0963 Coverage Testcase Generator Hardening

Decision:
`coverage_matrix -> testcase` 生成器必须在存在 `case_plan.json` 时输出可追溯 CasePlan 的候选用例；Flow 用例继承 coverage / structured_prd 的业务域页面，不再兜底到小程序首页类页面；中文页面/模块编号采用稳定编码并做全局去重。

Reason:
SC0963 旧候选暴露了 26 条产出、重复 `AD-GEN-GEN-MINI-FN-001`、Flow 落到 `小程序首页改版页`、高信号规则被降级为“基础属性一致”等问题，不能满足当前 strict 主链和用户期望的 `页面-功能模块` 分表。

Impact:
SC0963 修复后候选产出 33 条、覆盖 33/33 coverage、33/33 CasePlan、4 张表，Flow 归属 `页游落地页管理 / 页游落地页列表-操作按钮`。后续配置页/管理页类需求在 coverage 直出候选时将保留默认值、枚举、必填、图片规格、数据源过滤、状态/流程终态等断言，不再使用无语义 GEN/MINI 编号兜底。

## 2026-04-29 - Data Rule Testcase Generation

Decision:
`coverage_type=data_rule` 必须由 coverage testcase generator 生成正式数据校验用例，尤其是聚合、均分、注册口径、指标计算等可验算规则，不能因为不是字段控件类 coverage 而漏出主用例。

Reason:
SC0965 当前流程重跑时，20 个 coverage 中 `COV-EX-0015`（聚合落地页各版位注册数据按子落地页注册数据均分）未生成 testcase，导致 data_rule 规则无法进入 `case_plan -> testcase` 主链。

Impact:
`coverage_testcase_generator.py` 已增加通用 `data_rule` 分支。SC0965 重跑后主用例 20 条、coverage 20/20、CasePlan 20/20，`validate_work_item --strict --work-item-level S --retention minimal` 与 `run_quality_baseline.py` 通过。

## 2026-04-29 - Human Readable Testcase Copy

Decision:
正式 testcase 的标题、前置条件、测试步骤和预期结果面向人工阅读，不应直接暴露 `snake_case` 字段名或 coverage 机器表达；机器追溯应保留在备注、coverage、case_plan 和 bundle 等结构化产物中。

Reason:
SC0965 当前流程重跑后，虽然 coverage 与 CasePlan 追溯完整，但标题、步骤、预期中出现 `baidu_ad_type`、`ch_plan_type_filter` 等字段名，降低测试同学阅读与执行效率。SC0963 已证明当上游与生成器文案足够人话时，仍可保持完整追溯。

Impact:
`coverage_testcase_generator.py` 已增加人类可读标签解析与规则语义渲染，覆盖标题、前置条件、步骤、预期；`testcase_lint.py` 增加正文机器字段泄漏检查。SC0965 重跑后 20 条主用例无正文 `snake_case` 泄漏，SC0963 33 条抽检通过新增 lint。

## 2026-04-29 - Default Non-Required Fields

Decision:
若需求文字未描述“必填 / 必选 / 不能为空 / 必须填写 / 必须选择 / 必传”等强制语义，且原型图未出现必填星号 `*` 或等价标识，则字段默认按非必填处理。

Reason:
SC0965 的广告类型、游戏维度、计划类型等筛选项只描述了候选项、单选/多选、默认不选展示全部等规则，并未给出必填证据。仅因控件为单选/多选/筛选项就生成“为空不可提交 / 保存失败”会脑补强拦截，违背规则保真。

Impact:
AGENTS、结构化 prompt、用例生成 prompt、case-generation skill 与 testcase signal policy 已写入该口径。`coverage_testcase_generator.py` 只有在明确必填证据存在时才生成必填拦截断言。SC0965 清理可再生产物后重跑，筛选字段预期无必填断言，工作项校验与总基线通过。

## 2026-04-29 - Developer Self-Test Testcase Projection

Decision:
`testcases/dev_self_testcases.md` 作为从 `testcases/testcases_main.md` 派生的开发自测用例文件，筛选条件为标签列包含 `开发必测`；不新增 JSON 或 schema，不切换 testcase 真源。

Reason:
用户明确要求开发自测文件直接从主用例 Markdown 派生，且不需要其他内容。保持单一 Markdown 派生物可以让开发快速读取自测范围，同时避免引入新的真源或结构化产物维护成本。

Impact:
新增 `scripts/build_dev_self_testcases.py`，并接入 coverage testcase 生成与 regeneration post normalizer。`cleanup_derived_artifacts.py --mode minimal` 会将该文件视为可再生派生产物。正式 testcase 仍以 `testcases/testcases_main.md` 为主真源。

## 2026-04-29 - Tag Carrier And Responsibility Split

Decision:
测试用例标签继续使用既有封闭集合，不新增标签类型；但语义拆分为自动化执行载体与人工执行责任。`AI-API用例 / AI-UI用例` 表示适合沉淀的执行载体，`测试必测 / 开发必测` 表示人工执行责任。非核心且可被 AI-API / AI-UI 稳定覆盖的用例，可以不追加人工责任标签；核心流程或关键变更必须同时包含 `开发必测` 与 `测试必测`。

Reason:
旧规则把 `AI-API用例 / AI-UI用例 / 测试必测 / 开发必测` 混为“执行方式标签”，导致普通稳定 UI/API 用例默认堆叠人工责任标签，开发自测抽取范围也不够精准。拆分语义后，标签先表达适合沉淀的自动化载体，再按风险和角色责任追加人工必测。

Impact:
`skills/numbering-tagging/rules/tag_rule.yaml`、tagging skill、case-generation skill、prompt、lint 与 coverage testcase generator 已更新。`validate_work_item.py` 会在 `dev_self_testcases.md` 存在时校验它与 `testcases_main.md` 的 `开发必测` 过滤结果一致。SC0963 重跑后 33 条主用例、4 条开发自测；SC0965 重跑后 20 条主用例、2 条开发自测；PT083 strict baseline 已同步核心/关键用例双责任标签并通过基线。

## 2026-05-19 - Human Readable Testcase Style Rule

Decision:
正式 testcase 新增人工可读表达风格规则，标题、前置条件、测试步骤和预期结果应优先写成人工可读、可执行、可判断的表达；业务字段使用中文引号，接口/参数/技术字段才使用反引号。

Reason:
现有用例规则偏可追溯与可校验，但部分生成文案出现“语义等价 / 结构化规则一致 / 字段展示正确”等审计腔表达，降低测试同学直接执行和判断的效率。

Impact:
新增 `rules/testcase_human_readable_style.md`，并接入 AGENTS、START_HERE、WORKFLOW_CONTRACT、workflow、operating_sop 与用例生成 prompt。`coverage_testcase_generator.py` 的通用字段/值表达改为更符合元素标注和人工阅读的样式；不改变 testcase 真源、不降低 strict gate。

## 2026-07-13 - Requirement Source Intake And Testpoints Projection

Decision:
新增需求来源接入辅助层与测试点评审视图。`inputs/requirement_summary.md` 作为多源输入归一化文件，`inputs/source_manifest.json` 作为来源清单；`testcases/testpoints.md` / `testpoints.json` 作为从 `case_plan.json` 派生的人工评审视图。

Reason:
外部需求源、原型、飞书和截图需要可追溯的输入清单；测试同学也需要在正式 testcase 前查看“模块 / 功能点 / 测试维度 / 测试点”的评审视图。但这些能力不应替代现有测试设计决策层和正式用例真源。

Impact:
`requirement_summary.md` 和 `source_manifest.json` 只增强 inputs 前置归一化；`testpoints.*` 只从 `case_plan.json` 派生并保持 `projection_only=true`。`case_plan.json` 仍是正式用例前的计划真源，`testcases/testcases_main.md` 仍是主 testcase 真源，`coverage_first_traceability.json` 仍是主 traceability 真源。

## 2026-07-21 - Main Pipeline Intake, Testpoints And Persisted Level

Decision:
需求接入归一化与 testpoints 从可选视图提升为正式主流程阶段。所有工作项持久化 `manifest.json.work_item_level`；有效档位按“CLI 覆盖 > manifest > 默认 M”解析，并由重跑 bundle 传递给最终校验。

Reason:
可选需求摘要会导致 structured_prd 直接消费分散输入；按需 testpoints 会导致 Case Plan 与人工评审视图不同步；仅靠命令行指定 S/M/L 容易出现生成和校验档位不一致。

Impact:
新工作项初始化即包含 requirement summary、source manifest、testpoints 占位和主流程策略。strict 要求需求归一化真实有效、testpoints 覆盖 Case Plan；用例生成和 bundle 后处理会同步刷新 testpoints。`case_plan.json` 与 `testcases_main.md` 的真源地位不变。

## 2026-07-22 - Pipeline Consumer Closure

Decision:
修复主流程产物消费断点：reasoning 显式读取 requirement summary/source manifest 且支持纯文本；测试设计任务独立拆分并按 S/M/L 强制 bundle 产物；post-write 自动刷新 testcase bundle、审计评分和 quality report；已确认 CR findings 可转换为 design feedback；质量报告使用主产物指纹防止读取旧报告。

Reason:
此前部分产物只存在于 Skill/任务说明或 validator 中，确定性脚本未读取；部分兼容投影和质量报告也可能在重跑后保持旧版本。

Impact:
Case Plan 必须提供 coverage 或稳定 testcase 映射；存在活跃 Case Plan 但 coverage 为空或无候选匹配时，生成器硬失败，禁止空结果覆盖正式用例。PT083 当前 coverage 为空，因此保留既有正式用例作为真源，规则生成器不会静默替换。

## 2026-07-27 - Stage Validator Co-location

Decision:
单阶段 validator 与所属 Skill 共址；跨阶段映射、兼容投影和工作项总门禁继续保留在根 `scripts/`。Requirement Sources、Reasoning Pack、Coverage Matrix validator 已迁入对应 Skill。PT083 新路径、strict 与总基线通过后，旧 Requirement 根入口已删除；Reasoning/Coverage 暂保留兼容 wrapper。

Reason:
Validator 分散在根 scripts 和 Skill 目录会模糊阶段职责，也不利于 Skill 独立复用；但直接删除旧入口会破坏历史命令和外部 CI。

Impact:
仓库内部任务包、统一校验和 Skill 文档统一引用新路径。`scripts/validate_requirement_sources.py` 不再可用；Reasoning/Coverage 的旧根命令仍可用但不承载实现。

## 2026-07-27 - Lightweight Project Shell

Decision:
项目根切换为轻量壳，只保留 project manifest、公共输入、派生索引、项目质量汇总、人工确认知识和 work_items；正式测试资产真源全部下沉到工作项。删除旧项目级交付目录和 `validate_outputs.py`。

Reason:
项目级和工作项级同时保存 structured PRD、testcase、traceability、review 会形成双真源；随着工作项增长，复制正式产物也会造成仓库膨胀和状态不一致。

Impact:
新增 `refresh_project_views.py` 和 `validate_project.py`。项目 indexes/reports 只能从工作项真源再生，不得反写。WX-YGJ 项目级旧目录均为初始化占位，已清理；PT083 路径与正式产物不变。

## 2026-07-27 - Host-Neutral Core

Decision:
核心协议、Roadmap、repair 模板和运行时上下文保持宿主中立；具体工具名称只允许出现在 `tool_adapters/<host>/`、宿主私有目录或历史审计记录。核心运行时不再根据 Codex 环境变量自动选择 adapter。

Reason:
AGENTS 和自驱动协议曾以 Codex 为默认主语，任务包还只引用 Cursor adapter，造成“仓库定义流程但实际偏向特定宿主”的冲突。

Impact:
三份 adapter README 使用统一结构；删除无代码依赖的 Codex agent YAML 与 runtime bridge。所有宿主统一使用 `ATP_MODEL / ATP_API_KEY / ATP_BASE_URL / ATP_RUNTIME_CONTEXT_FILE` 等显式运行时配置。核心 prompts、skills、schemas 和生成任务包均不绑定宿主。

## 2026-08-05 - Harness Contracts And Deterministic Orchestrator

Decision:
先落地薄领域 Harness 的 P0/P1 基础：用 Run、Stage、Event、Diagnostic、Model Action、Approval 六类 Schema 冻结运行契约，并新增只读的确定性阶段 Orchestrator。首版只允许执行阶段注册表中的 Validator 或 artifact checkpoint，不接模型、不执行生成器、不开放任意 shell。

Reason:
现有仓库已有强验证 Harness，但缺少可恢复的阶段状态机、运行事件和失败诊断。直接接入模型循环会放大不可恢复写入和权限风险，因此先建立宿主中立、可验证、可暂停恢复的运行底座。

Impact:
`scripts/run_work_item_pipeline.py` 成为新 Harness 验证入口，支持 `start / status / resume / cancel`；运行过程写入 `.generation/runs/` 并可按 minimal retention 清理。成功 checkpoint 只有在输入指纹未变化时才复用，变化后该阶段及下游失效。最终结论继续由现有 `validate_work_item.py` strict gate 决定，testcase、Case Plan 和 traceability 真源均未切换。PT083 已完成 Case Plan 停止与恢复验证，正式产物未被修改。

## 2026-08-05 - Harness Structured Diagnostics

Decision:
将 Validator 文本输出归一化为 Harness Diagnostic，并区分“观察失败的阶段”和“负责修复的阶段”。聚合 Strict Gate 输出按稳定关键词路由到对应业务阶段；无法识别的失败使用统一兜底代码。

Reason:
仅保存退出码和日志路径不足以支持后续自动反馈循环，也无法稳定判断错误应回到 Case Plan、Testcase、Traceability 或其他阶段。诊断层必须先于模型 repair 落地，并且不能改变 Validator 原始结论。

Impact:
新增 `scripts/harness/diagnostics.py`，Diagnostic 增加 `observed_stage_id / command_index / exit_code`。失败历史按 stage 和 attempt 分文件保存，API Key 与 Authorization 摘要会脱敏。结构化诊断只解释失败，不触发修复、不降低 strict；Harness 单元测试已纳入统一质量基线。

## 2026-08-05 - Restricted Case Plan Agent Loop

Decision:
以 `testcases/case_plan.json` 作为首个 Agent Loop 垂直切片。模型只能通过 command adapter 返回白名单 Action，候选只写 staging；Harness 运行正式 Case Plan Validator，并将失败 Diagnostic 回注下一 turn。模型请求提交时必须停在 pending approval，禁止同一命令内直接提交。

Reason:
直接让模型写正式产物无法保证权限、回滚和并发安全；仅在启动时传入宽泛提交开关也无法绑定实际候选。两步审批可以让人工先检查 staging 与 diff，再用 approval ID 和 candidate hash 精确授权。

Impact:
新增 `agent-case-plan` 与 `approve-case-plan` 两个 Harness 操作。每个 Agent run 最多 8 turn、2 repair；审批绑定 candidate、上游和正式目标 hash，任一漂移拒绝提交。成功提交会备份旧 Case Plan 并记录下游 testcase、traceability、review、strict gate 失效，但不会自动刷新这些资产。PT083 staging 试点通过 Validator 并停在等待审批，正式 Case Plan 未变化。

## 2026-08-05 - Harness Governance And Observability

Decision:
为 Case Plan Agent Loop 增加可执行的 wall time、模型调用、token 和 cost 预算，并把模型 usage/runtime 作为可选 envelope 接入。配置 token/cost 门禁或 `require_usage` 后，适配器未报告 usage 必须停止，超预算 Action 不得分发。每个 run 生成 telemetry、终态摘要，并支持独立拒绝审批和重放审计。

Reason:
仅有 turn/repair 上限不能回答一次运行消耗了多少资源，也无法对适配器漏报成本、事件篡改或审批悬挂做治理。预算必须在 Action 分发前生效，观测数据不得由 Harness 猜测，审计必须能够从持久化状态独立复核。

Impact:
新增 `harness_telemetry`、`harness_audit_report` 契约，以及 `reject-case-plan`、`audit-run` 操作。审计覆盖 run state、连续 Event sequence、Action、Approval、Diagnostic、Telemetry 与终态一致性。PT083 观测试点记录 4 次调用、480 token、0.004 USD fixture cost；pending approval 被显式拒绝后 run 进入 cancelled，两次审计均通过，正式 Case Plan hash 未变化。

## 2026-08-05 - Restricted Harness Hook Dispatcher

Decision:
Harness Hook 采用仓库内可信脚本模型。配置只允许引用 `scripts/hooks/*.py`，Dispatcher 固定使用当前 Python argv、stdin 结构化事件、清理后的环境、超时与 stdout 上限执行。阶段前/后与 repair Hook 可阻塞编排；失败通知和审批 Hook 只能 warn。

Reason:
允许配置直接携带命令会重新开放任意 shell，Hook 失败若能覆盖 Validator 或审批结论也会破坏现有强门禁。可信脚本路径加事件级失败策略，可以提供扩展点，同时保持 Validator、审批和业务真源的权威边界。

Impact:
新增 Hook Config/Execution Schema、`scripts/harness/hook_dispatcher.py`、`scripts/run_hook_dispatcher.py` 与 execution 审计。Orchestrator 接入 pre/post/fail/repair，Case Plan Agent 与 Approval Service 接入 approval requested/resolved。默认 `strict-gate-stage-summary` post-hook 只记录摘要。PT083 L strict 14 阶段完成，Hook 1/1 成功，61 个事件审计通过，正式 Case Plan 未变化。Hook handler 仍是受信任仓库代码，不构成操作系统级沙箱。

## 2026-08-05 - Controlled Full-Pipeline Generation

Decision:
以现有 regeneration bundle 作为全链路候选交换格式。Harness 先复制仓库到隔离临时目录，在副本中执行 bundle、post normalizer 和 strict；通过后将完整正式资产候选写入 run staging，并用 candidate、目标快照和原始输入 fingerprint 绑定两步审批。正式发布使用 backup、同目录临时替换、transaction journal、发布后 strict 与自动回滚。

Reason:
现有 `execute_regeneration_bundle.py` 会先写正式资产再校验，失败时可能留下半完成结果，也无法在审批前查看最终 normalizer 产物。隔离副本可以复用全部现有生成和验证逻辑，同时避免为 staging 大规模改写各脚本的硬编码工作项路径。

Impact:
新增 generation candidate/publish transaction Schema、`ControlledGenerationWorkspace` 与 `ControlledGenerationService`，以及 `generate / approve-generation / reject-generation / recover-generation` CLI。Provider 支持 existing 和可信 command argv，不开放 shell。PT083 existing 与 command 两条链路都在隔离副本通过 L strict并停在审批，随后显式拒绝；两次 audit 均通过，正式 Case Plan/Testcase hash 未变化。多文件发布是带 journal 和恢复机制的逻辑原子事务，不宣称文件系统原生多文件原子性。

## 2026-08-05 - Tiered Eval And Regression Gate

Decision:
以检查成本和保护强度划分 smoke、regression、golden 三档。Smoke 运行快速代表 fixture；regression 运行全部登记 fixture；golden 在 regression 基础上运行全量 Harness 单元测试与 PT083 L strict，并将 suite version、量化检查数、预期失败数、命令数和逐 fixture SHA-256 与提交到仓库的 baseline 比较。Baseline 只能在全部检查通过后显式更新。

Reason:
原 `run_evals.py --all` 只有逐 fixture 文本结果，元素标注负向样例未纳入统一入口，也无法区分本地快速反馈、PR 回归和发布级 golden，规则或 fixture 变化更没有可审查的量化差异。分档可控制反馈成本；结构化报告和 hash baseline 可同时捕获 Validator 结果回退、负向样例意外通过、检查数下降与 golden 内容漂移。

Impact:
新增 `eval_suite_report` Schema、`evals/eval_suite.json`、golden baseline 和 `scripts/run_eval_suite.py`。Regression 当前覆盖 6 个 fixture、56 个检查和 2 个 expected-failure；golden 额外执行 2 个 live 命令。`run_quality_baseline.py` 改为执行 regression，GitHub Actions 在 PR/push 运行全量 Harness 单元测试与 regression，并在主分支/手工触发时运行 golden。Eval 报告写入根 `.generation/evals/`，不修改正式工作项资产；`run_evals.py` 继续兼容旧调用。

## 2026-08-05 - Multi-role Restricted Agent Runtime

Decision:
将四个核心角色建模为固定顺序的受限 Action 阶段：`prd_structurer -> case_generator -> case_reviewer -> asset_formatter`。每个角色复用同一 Model Action Schema，但拥有独立可读范围、精确可写路径、staging fingerprint 和 Validator。角色交接只发生在候选通过校验后；Formatter 完成后再将累计候选交给受控全链路生成执行隔离 normalizer/strict，并创建 hash 绑定发布审批。

Reason:
直接把 P3 Case Plan 单文件 Workspace 泛化为任意文件写入会扩大权限，也无法表达 Reviewer 不得改 testcase、Formatter 只能写派生资产等职责边界。让四角色直接依次写正式目录同样会在中间失败时留下半成品。角色专属白名单加 run 内累计 staging，可以保持职责分离；最终复用 P4-006 候选和发布事务，避免建立第二套发布安全模型。

Impact:
新增 `harness_role_runtime` Schema、`MultiRoleArtifactWorkspace`、`MultiRoleAgentRuntime` 与 `agent-roles / approve-roles / reject-roles` CLI。四角色共享最多每角色 8 turn/2 repair、wall/token/cost 预算、Hook、Telemetry、事件和 audit。Reviewer 仅写 reviews，Formatter 仅写 `feishu_ready.md`，Case Generator 不得修改 Case Plan。后续补强要求 Structurer 同步提交 `structured_prd.md` 与语义一致的 JSON 编译投影，并将 testpoints、Case Plan、testcase 交叉一致性检查前移到 Generator 角色门禁。补强后的 PT083 echo 试点使用 17 次模型调用、255 token、0.0017 USD fixture cost，四个角色 Validator 与隔离 L strict 通过后停在审批；显式拒绝后 audit 通过，正式资产未发布。

## 2026-08-05 - Harness-Loop End-to-End Closeout

Decision:
本地工作项并发锁改为 PID、唯一 token 和所有权校验；`--force-unlock` 只能移除已确认 PID 不存活的锁。发布恢复在回滚前预检全部备份并清理 transaction 临时文件，缺少任一备份时拒绝部分恢复。minimal retention 在实际删除前检查锁、run 终态、pending approval 和未完成事务，默认把发布备份及 transaction/candidate 元数据归档到 `.generation/backups/`。新增统一 closeout 入口和 Action/Approval/Generation 关联审计。

Reason:
仅用锁文件存在性无法阻止旧进程退出时误删后继锁；恢复时直接逐文件回滚会在备份缺失时留下新的半恢复状态；直接删除 `.generation/runs` 会同时丢失 pending 决策、事务恢复证据和实际位于 run 内的发布备份。端到端完成还需要一个可重复、结构化且能证明正式资产未变化的统一验收。

Impact:
新增 `harness_closeout_report` Schema、`scripts/run_harness_closeout.py`、`docs/harness_loop_closeout.md` 和 closeout 专项测试。全量 Harness 测试增至 57 项。PT083 最终 closeout run `RUN-P4009-CLOSEOUT-FINAL-20260805` 的确定性 Harness、run audit、golden 与质量基线全部通过，`.generation` 之外的聚合 hash 前后一致。历史 P4-003 两个悬挂审批已显式拒绝且未提交正式资产。当前锁只承诺单机互斥，多文件事务仍是 journal 驱动的逻辑原子发布；分布式锁、并行 subagent、长期 memory 与自动代码评审留待后续明确立项。

## 2026-08-05 - Case Plan Commit Recovery

Decision:
Case Plan 单文件审批提交增加独立 transaction journal。提交顺序固定为：备份与 `prepared` → `committing` → 原子替换正式目标 → `committed` journal → approval/run/event metadata。恢复以 committed journal 为分界：`prepared/committing` 回滚到原目标和 pending approval；`committed` 校验正式目标 hash 后幂等完成 metadata。

Reason:
旧实现先把 approval 写为 approved，再替换正式 Case Plan。进程在两步之间被强杀时会形成 approved approval、waiting run 和未提交目标的分裂状态；普通异常回滚无法覆盖 SIGKILL。单文件 journal 可以保留明确恢复点，并避免为 Case Plan 引入完整多文件发布事务。

Impact:
新增 `harness_case_plan_commit_transaction` Schema、`recover-case-plan` CLI、cleanup 阻断和 transaction 审计。恢复覆盖 prepared、committing、committed、重复执行、备份缺失、目标漂移、恢复后重试与未恢复前禁止拒绝。PT083 run `RUN-P4010-RECOVERY-20260805` 已演练 prepared transaction 回滚、pending approval 恢复、显式拒绝与 audit 通过，未提交正式 Case Plan。Agent/四角色中间 model turn 续跑仍留作后续任务。

## 2026-08-05 - Parallel Reviewer Runtime

Decision:
Case Reviewer 增加 opt-in 三路并行 Runtime。`agent-roles --parallel-reviewers` 固定并发 evidence、flow、testcase Reviewer；默认继续使用原单 Reviewer。只有 3/3 succeeded 才能由确定性聚合器生成 run-local review bundle 和 `reviews/review_record.md` staging，再执行现有 Review Gate 并继续 Formatter。

Reason:
单 Reviewer 无法同时隔离证据追溯、业务流程和 testcase 质量关注点；但让并发线程直接写共享 staging、事件或正式 reviews 会引入竞态和不可重放结果。三线程只缓冲模型 Action、findings 与事件，Coordinator 按固定 Reviewer 顺序串行持久化，可同时获得真实并发和连续确定的 event sequence。

Impact:
新增 Parallel Reviewer Action/Finding/Runtime/Bundle Schema、三类 Reviewer Skill、并发安全共享预算、稳定 finding ID/dedupe/conflict 聚合、per-reviewer telemetry 与 replay audit。任一路失败、超时、越权、非法 Action、预算不足或 staging 漂移时，不生成聚合 review、不进入 Formatter，仅创建无 continue 选项的 `manual_decision`，由 `reject-roles` 结束。当前能力仅限单机 Case Reviewer 子阶段，不承诺分布式锁、长期 memory、任意 shell、自动代码评审或 OS 沙箱。

## 2026-08-06 - Multi-role Crash Recovery

Decision:
为异常遗留为 `running` 的 multi-role run 增加 `recover-roles`。恢复只保留 run-local staging、Action、Finding、日志和诊断，把未完成角色标记为 skipped，并将 run 终态化为 cancelled；不续 model turn、不复用部分并行 Reviewer 结果，也不补跑 Reviewer。存在 pending approval 或发布事务时继续使用既有审批/事务恢复入口。

Reason:
四角色和并行 Reviewer 在进程被强杀时可能来不及写 waiting/terminal state，导致 cleanup 永久阻断。中间 observations 与 barrier 前 Reviewer 结果并未形成可靠 checkpoint，强行续跑会造成上下文、预算和 3/3 barrier 不一致。安全取消并以新 run 重跑是当前最小且可审计的恢复语义。

Impact:
新增 `harness_multi_role_recovery` Schema、`multi_role_run_recovered` 事件和 `recover-roles` CLI。Audit 会交叉校验 recovery record、事件、run/role 终态、pending approval 与证据路径；cleanup 对 running multi-role run 明确提示恢复入口。PT083 `RUN-P5002-PT083-PARALLEL-CRASH-20260806` 已在前两角色成功后于并行 Reviewer 阶段受控崩溃，恢复保留 partial 证据、跳过 Reviewer/Formatter、取消 run，audit 通过且正式 Case Plan/Testcase hash 未变化。Closeout 指纹明确排除 macOS `.DS_Store` 文件系统元数据，但继续覆盖全部流程正式资产。turn 级续跑不再视为本轮必需项；只有出现明确业务价值时才单独立项评估。

## 2026-08-06 - PT084 Required Coverage Evidence Boundary

Decision:
字段 `required=true` 只有在来源文字明确“必填/必传”或图片存在必填星号时才能进入 `main_testcase` 的空值保存阻断。PT084 的 C 端“云机版本Tab”仅作为页面展示与切换上下文，不是可为空提交的表单字段，因此 `COV-EX-0004` 保留稳定 ID 但调整为 audit item；商品添加表单的红色星号字段及《编辑宣传内容》的必传字段继续保持 main coverage，并通过独立 Gate/Acceptance/CasePlan/testcase 承接。

Reason:
旧 Structured PRD 将 C 端 Tab 建模为 `required=true`，自动产生了没有来源动作的“为空阻止保存”coverage；同时把多个 coverage 宽挂到组合用例会在结构校验通过时掩盖真实语义缺口。按来源证据逐字段判定并使用精确 `来源coverage` 标记，才能同时避免降低真实必填规则和制造虚假追溯。

Impact:
PT084 main coverage 从38调整为37、audit 从44调整为45；补齐11条独立测试链后，官方 Coverage-First 生成器确定性产出46条有效记录，主失真率为0。此决策不修改通用规则强度，不改变 soft prompt、technical background、risk 或 needs_confirmation 的隔离边界。

## 2026-08-06 - Harness Case Plan Stage Boundary

Decision:
确定性 Harness 的 `case_plan` 阶段只校验 Case Plan 及其当前上游设计产物，不传入尚未生成的 `testcases_main.md`。testcase 到 Case Plan 的反向追溯校验继续使用原 Validator，并在 `testcases` 阶段执行。

Reason:
PT084 与 PT085 均证明，Case Plan 本体有效时，初始化空 testcase 模板会错误阻断 Case Plan checkpoint。该反向映射只有在正式 testcase 生成后才具备可验证输入，提前执行属于阶段职责越界。

Impact:
Case Plan 可独立建立 checkpoint；`generated_testcase_ids` 的可执行映射要求仍在 Case Plan Validator 内，正式 testcase 的 Case Plan 引用、非法计划引用和风险/技术背景隔离检查未删除，只后移到 `testcases` 阶段。旧 Validator、兼容投影和 strict gate 保持不变。

## 2026-08-06 - Harness Testcase Bundle Stage Boundary

Decision:
确定性 Harness 的 `testcases` 阶段只校验正式 testcase、页面板块分组、同步 testpoints 和 Case Plan 反向映射。兼容投影 `testcase_bundle.json` 的一致性校验继续使用原 Validator，并移动到现有阶段模型中的 `traceability` 阶段。

Reason:
PT084 与 PT085 均证明，正式 testcase/testpoints 已有效生成但 Bundle 后处理尚未执行时，初始化空 Bundle 会以数量不一致错误阻断 Testcase checkpoint。Bundle 是从 `testcases_main.md` 派生的 compatibility-only 投影，不应成为主用例生成阶段的前置条件。

Impact:
Testcase 可在 Bundle 刷新前独立建立 checkpoint；Bundle 的 testcase 数量、Case Plan 映射、项目/工作项标识和内容一致性检查未删除或降级，只在后处理完成后的首个现有阶段执行。最终 `validate_work_item --strict` 仍保留全部 Bundle 与质量报告指纹门禁。

## 2026-08-06 - No-code Comparison Run Closeout

Decision:
无代码分支的需求对比重跑使用仓库正式支持的 `validate_work_item --strict --skip-code-reviews` 完成工作项门禁，不创建或伪造前后端 code review request、review 结论或 confirmation。若 Harness `review` 阶段只有文件存在checkpoint且没有显式skip语义，原run停在最后一个真实完成的Traceability checkpoint，不用待评审模板推进到strict_gate。

Reason:
PT085仅验证同一需求经过流程修改后的产物一致性，没有代码分支或前后端评审输入。`review_record.md` 当前仍明确为“待评审”，而Harness review阶段无Validator、无 `--skip-review`，继续resume会把文件存在错误等同于评审完成。工作项CLI已显式提供 `--skip-code-reviews`，这是当前合法的无代码收口路径。

Impact:
PT085工作项M strict和质量基线可以完成，但原run `RUN-20260806T063753Z` 合法保持paused at Traceability，review/strict_gate为pending；run audit仍须通过。后续应为Harness增加可审计的review disposition（例如 `not_applicable` + reason），并为requirement_summary人工审核增加正式approval状态；在契约落地前继续以人工确认记录和stop-at约束，不伪造receipt/reviewer。

## 2026-08-06 - Requirement Summary Human Approval Gate

Decision:
Requirement Sources 机器校验与 evidence 之间新增正式人工门。新工作项默认 `pipeline_policy.requirement_approval_required=true`；通过机器校验后 run/stage 必须进入 `waiting_approval`，只有内容绑定的 `inputs/requirement_approval.json` 为 approved 才能 resume。

Reason:
PT085 只能依赖 stop-at 和文字记录表达人工确认，pending 状态可被 resume 绕过，也没有 reviewer、内容 hash、原始输入 fingerprint、事件和崩溃恢复证据。正式 receipt 必须先于下游 checkpoint，并复用 Harness state/event/audit，不建立独立发布体系。

Impact:
Receipt 绑定 requirement summary、source manifest、原始输入聚合 fingerprint、requirement version 和 run。`approve-requirement / reject-requirement` 要求显式 reviewer/note，重复同动作幂等、冲突动作失败；`recover-requirement-approval` 幂等补全 receipt 已写但 event/state 未完成的窗口。任一绑定内容漂移会失效旧批准和下游 checkpoint。旧 manifest 缺字段保持兼容，显式 required 的 strict 硬失败；CI、cleanup 和 controlled generation 不得批准、删除、发布或伪造 receipt。

## 2026-08-06 - Canonical Requirement Approval Checkpoint

Decision:
`requirement_approval_required=true` 时，Requirement Intake checkpoint 指纹只使用正式 approval binding：run、requirement summary、source manifest、raw inputs fingerprint 与 requirement version。manifest 的运行期、状态、派生路径或质量策略字段不参与审批有效性；历史完整-manifest checkpoint 在 approved receipt 仍匹配时原位规范化。

Reason:
PT086 证明通用 `fingerprint_files()` 自动加入完整 manifest，会在需求内容未变化时重验 Requirement Intake，并由阶段成功后的无条件 request 撤销有效批准。审批 receipt、strict 与 audit 已经共同定义了更窄且可解释的 canonical binding，checkpoint 必须与该契约一致。

Impact:
非绑定 manifest 变化不再进入 `waiting_approval`，也不需要 `recover` 或重复人工决议。summary、source manifest、raw input 或 requirement version 漂移仍由 resume guard 先行失效全部 checkpoint 并创建新 pending receipt；新 approval ID 绑定完整 canonical fingerprint，避免来源或版本漂移复用旧 resolved 事件。旧 manifest 缺 policy 字段仍走原通用指纹路径，兼容行为不变。

## 2026-08-06 - PT086 Benchmark Accounting And Trace Cardinality

Decision:
PT086最终基准按阶段记录authoring/生成、validator、resume/checkpoint与audit纯执行墙钟，人工等待、审批CLI和框架缺陷调试开销分开披露。Coverage-First Traceability以唯一main Coverage为主计数单位；同一Coverage映射多个Testcase不增加覆盖项数量。

Reason:
PT084的约59分钟、PT085的84–86分钟和PT086的细分纯执行时间并非完全相同口径，直接计算倍数会制造伪精度。PT084/PT085的46条Traceability来自37个唯一main Coverage加9个重复多Testcase映射，PT086的37条一Coverage一记录在`invalid=0`时不能解释为覆盖下降。

Impact:
run数量与采用相同事件定义的validator command数量可直接比较；耗时只有在人工等待、repair和调试边界一致时才能直接比较。PT086保留1 run、24条Harness validator command、21次stage attempt和10个唯一完成阶段的原始统计；产物稳定性继续以82 Coverage、62 Gate、75 Acceptance/Case/Testcase/Testpoint/Bundle、25开发自测、37个唯一main Coverage及`invalid=0`为准。

## 2026-08-06 - PT083 Current Sample Migration

Decision:
用户明确授权删除旧 PT083/PT084/PT085，并将已批准 PT086 的需求语义与正式测试资产迁移为当前 PT083 M 档样本。旧 PT086 Harness run 先正式取消并审计，再按 minimal retention 清理；迁移后的 PT083 使用新 run 和正式 approval CLI 重新审批，不搬运或改写旧审批 hash。

Reason:
Harness run、日志和事件是可清理过程产物，直接把 PT086 run/string 改成 PT083 会伪造执行历史并破坏 approval binding。重新建立 PT083 run 可让 work item、路径、receipt、event 和 audit 保持一致，同时保留 82/62/75/25/37 的正式资产口径。

Impact:
当前 CI、golden live strict、CLI 示例、默认 closeout 和项目索引统一指向 PT083 M 档。本文及 Roadmap 中早于本决策的 PT083 L 档和 PT084/PT085/PT086 对比均视为历史基准，不再代表当前目录或默认命令；历史数字不机械改写。

## 2026-08-06 - Safe Cleanup And Current Documentation Boundary

Decision:
高置信安全清理只允许根工作树空 `FETCH_HEAD`、四个空且无引用的 `.cursor/subagents/*.md`、根 `.generation/evals/*-latest.json`；不得触碰 `.git/FETCH_HEAD`、兼容性待确认项或其他评测数据。当前运行文档统一以 PT083 M 档、正式 Requirement Approval、单 run resume 和阶段隔离为现行口径。

Reason:
根运行产物可重建，但 `.git/FETCH_HEAD` 属于 Git 内部状态；Case Plan 依赖未来 testcase、Testcases 依赖未刷新 Bundle 都会造成阶段越界。历史 PT084/PT085/PT086 数字仍有决策追溯价值，不应为消除搜索命中而改写。

Impact:
Case Plan 阶段只消费上游设计资产，Testcases 阶段不消费未刷新 Bundle，Bundle 在 Traceability 前刷新校验。无代码 M 档工作项 strict 可显式 `--skip-code-reviews`，但 Harness run 尚无 Review `not_applicable` disposition。执行本轮复核时三类授权候选均已不存在，因此未重复删除；`.git/FETCH_HEAD` 保持原状。

## 2026-08-27 - Harness-Loop Validates, Scripts Generate

Decision:
当前宿主会话执行 Harness-Loop 时，`start/resume` 只做阶段校验与 checkpoint；各阶段产物由正式生成器或本会话 authoring 写入后，再 `resume --stop-at <stage>`。无 `--provider-command-json` 可信 adapter 时不得调用 `agent-roles`。输入（摘要、原图、binding）未变时，允许接回同一工作项已校验的设计链，但正式用例仍必须满足 75 条 Case Plan 一计划一用例；Coverage 合并生成器产出不足时不得把 17 条合并结果当作交付。无代码工作项在 review 具备 `not_applicable` 前停在 Traceability。

Reason:
用户要求自动跑完流水线。Harness 本身不生成 Structured PRD / Gate / Case Plan / Testcase；Cursor 会话也接不进 `agent-roles`。PT083 全流程重跑时图片与批准摘要未变，独立 Validator 与 image-evidence mapping 已证明设计链仍匹配当前 evidence。Coverage→testcase 生成器合并路径已知会从 82 条草稿收敛到约 17 条，不能单独满足 strict 追溯。

Impact:
`RUN-PT083-FULL-20260826` 可连续 resume 到 traceability，工作项 `--strict --skip-code-reviews` 作为无代码收口。后续同类请求按同一分工执行，不再每阶段停问；不得为打通 Harness 终态伪造 review 或降低 gate。


## 2026-09-04 - Runbook End-to-End Teaching Walkthrough

Decision:
`AI_TEST_CASE_PIPELINE.md` 在总体流程图之后新增第 3.1 节教学举例。它演示日常轨道：会话或脚本写入正式产物，Harness `start/resume` 只校验；四角色 `agent-roles` 仍以第 0 节为准。举例使用虚构工作项 `DEMO-001`，不得进入 CI 或项目样本。

Reason:
第 0 节说明发布控制，第 4–20 节按阶段拆实现，中间缺少一条需求如何走完全程的叙事。不写清两条轨道，读者会把 0.2 的四角色图误当成无 adapter 时的日常跑法。

Impact:
首次阅读顺序改为：第 0 节快速指南 → 第 3.1 节举例 → 第 4 节起的阶段实现。正式样本、真源和 Strict Gate 口径不变。

## 2026-09-21 - Blind Oracle Feedback Isolation

Decision:
盲测生成前的来源角色统一为 `primary_requirement / context_only / oracle_only`；后两类只能进入 audit。复合显式规则可用 `atomic_assertions` 逐断言拆分 Coverage。代码 diff 与已有测试只在资产冻结后通过独立 oracle-delta 评分进入 Review/Design Feedback，不直接反写 testcase。

Reason:
第二轮公开盲测证明，关联 issue 背景可能被误升为主验收，复合规则可能生成不可定位的多分支用例，而实现级边界只有解封 oracle 后才能合理识别。将三者分层可以同时保持盲测真实性与评审后的可迭代性。

Impact:
Coverage 生成器会把 `context_only/oracle_only` 显式规则降为 audit，并按 `atomic_assertions` 拆分；Coverage Validator 阻止非主来源进入 main；`score_oracle_delta.py` 独立计算 oracle 覆盖率与用例相关率。旧资产缺少新字段时仍按 `primary_requirement` 兼容。

## 2026-09-21 - Image Evidence Requirement Follows Actual Source Modality

Decision:
工作项声明 `image_evidence` 兼容占位时，只有 `source_manifest` 存在 `status=available` 的 `source_type=image`，或 inventory 实际包含图片，才执行图片非空强校验。纯文本来源的空 inventory 记录为 SKIPPED。

Reason:
Appsmith、Chatwoot、Saleor 三个公开 PR 盲测样本均为纯文本来源，全部正式资产和追溯已通过，但 Harness strict 仍被空图片列表统一阻断。图片证据要求应由真实输入模态决定，不能由兼容占位文件是否存在决定。

Impact:
纯文本需求可通过 Harness strict；有可用图片来源、非空 inventory、缺失或损坏 source manifest 仍保留原强校验，不降低图片型工作项门禁。

## 2026-09-21 - Atomic Assertion Confirmation Is Independent

Decision:
Coverage 生成器在规则提供 `atomic_assertions` 时，逐条依据原子断言自身是否含“待确认”决定 main/audit 分流；不得因父规则同时记录了其它未决限定而把全部已确认断言降为 audit。未拆分规则仍按完整 `rule_text` 判断，`context_only/oracle_only` 继续强制进入 audit。

Reason:
Supabase 恢复码规则明确规定无效、空值和格式不正确时不得建立会话，但只把具体格式与错误文案标为待确认。父句级判断导致三个已确认拒绝行为全部丢失主覆盖。

Impact:
已确认的原子行为可进入正式 Coverage，未决断言和非主来源仍被隔离；新增单测防止父规则中的局部待确认说明再次污染其它原子断言。

## 2026-09-21 - Blind R3 Testability Classification Preserves Source Scope

Decision:
第三轮公开盲测的 Testability Gate 以 Structured PRD 的来源范围和规则层级为边界：`primary_requirement` 明确行为进入 Acceptance Examples 候选，重复的 feature/field 规则使用 `skip_case`，Reasoning 风险与 `context_only` 规则只进入 `risk_note_only`；可验证结果与未确认细节并存时使用 `partially_testable`。

Reason:
门禁必须同时避免漏掉可测业务结果和把推理风险、重复语义、未定义格式或错误文案升级为强验收断言。

Impact:
四份 Gate 共 59 条并通过 Validator；下一阶段只能消费 `generate_acceptance_example` 项，Supabase 的具体恢复码格式、错误文案和上下文安全项不得进入正式验收主链。

## 2026-09-21 - Blind R3 Acceptance Examples Follow Atomic Main Coverage

Decision:
第三轮公开盲测的 Acceptance Examples 按 main Coverage 原子断言一对一生成，并同时保留 `source_gate_ids`、`source_rule_ids` 与 `coverage_refs`；Gate 中的重复、风险和非主来源决议不参与生成。

Reason:
仅按 Gate 父规则生成会重新合并已拆开的独立结果，而只按 Coverage 生成又可能绕过 Testability Gate。三向追溯能同时保持原子性和门禁边界。

Impact:
四份工作项共 37 条验收示例，精确覆盖 37 个 main Coverage 和 24 个允许 Gate；下一阶段 Case Plan 可直接以每条 Acceptance Example 的单一可观察结果为输入。

## 2026-09-21 - Blind R3 Case Plan Uses One-to-One Direct Generation

Decision:
第三轮公开盲测的 37 条 Acceptance Example 各生成一条 `case_plan_direct` 计划，并各自绑定唯一的稳定 testcase ID；页面与板块编码先登记到统一编号规则，不使用临时编号。

Reason:
一计划一用例可保持原子 Coverage 不被再次合并，并让正式用例生成阶段直接执行已确认的页面、类型、优先级和断言决策。

Impact:
四份 Case Plan 共 37 条，Gate、Example、Rule、Coverage 追溯完整；M 档不要求且未伪造 Verification Responsibility，下一阶段须严格复用预留 testcase ID。

## 2026-09-21 - Direct Generation Preserves Explicit Case Plan Type

Decision:
`case_plan_direct` 生成正式用例时，以 Case Plan 显式 `case_type` 为测试类型真源；通用语义推断只补齐文案，不得把已明确的类型重新解释为展示类。

Reason:
Celery 边界计划虽明确为 `field_constraint`，但来源描述中的“排序”触发展示语义推断，导致预留 `BD` 编号与生成的“功能”类型冲突。

Impact:
边界、异常、流程、状态和数据类型保持设计层决策，编号与测试类型一致；新增 direct 生成回归测试，未改变非 direct 流程或降低 lint 规则。

## 2026-09-21 - Baseline Comparison Is A Concrete Oracle

Decision:
质量评分中的“一致”不再一律视为抽象预期；当结果显式绑定迁移前、重试前、认证前、首次、原始或基线值时，按可判定的前后比较 Oracle 处理。

Reason:
Django 的记录数量、主键和字段值迁移前后对比，以及 Temporal 的 run 最终状态重试前后对比，都具备已记录基线与明确比较对象，旧规则却仅因包含“一致”而误报。

Impact:
真正的“与需求一致”等无基线抽象表述仍会被识别；显式 before/after 不变量不再制造弱用例噪声。新增回归测试，未放宽 Traceability、Bundle 或 testcase 校验。

## 2026-09-21 - Oracle Feedback Must Preserve Requirement Scope

Decision:
冻结资产后的 Oracle 反馈必须区分正式需求缺口、`oracle_only` 实现风险与实现差异。只有已批准需求能够支持的反馈进入正式设计主链；代码或新增测试独有的行为先进入 Gate 的 risk/audit。实现与已批准需求冲突时保留需求预期并记录 implementation gap，不按代码现状改写 testcase。

Reason:
第三轮盲测中 Temporal 的动态开关、冲突策略和错误传播，以及 Supabase 的 returnTo、异步交互均来自后置代码 Oracle。若全部等权回灌正式用例，会破坏盲测边界并把实现偶然细节升级为产品契约。Supabase 已批准摘要明确功能关闭时返回 MFA 验证页，不能因当前实现使用 `getReturnToPath()` 而修改 CP-010。

Impact:
本轮 9 条反馈分为 2 条正式设计补强、6 条 oracle-only 风险和 1 条实现差异。后续 Oracle scorer 需要拆分 requirement coverage 与 implementation-risk coverage，不能继续只用单一覆盖率解释用例质量。

## 2026-09-22 - Oracle Coverage Is Reported By Scope

Decision:
Oracle assertion 使用 `oracle_scope=requirement/implementation/risk` 分层；旧输入缺省为 `requirement`。评分结果保留总体兼容分，同时分别输出批准需求、实现行为和风险路径覆盖率。不同 scope 不互相替代，也不得用实现/风险缺口判定需求用例不合格。

Reason:
Temporal 与 Supabase 的动态开关、冲突策略、错误路径、returnTo 和异步 UI 行为来自冻结后的代码 Oracle，不在批准需求输入中。旧总体分将这些缺口与需求覆盖等权混合，错误地把 0.65/0.5909 解释为需求用例不足。

Impact:
7 份样本复算后，Temporal/Supabase requirement coverage 均为 1.0，implementation 分别为 0.25/0.3571，Temporal risk 为 0.0；Celery requirement 0.9444 保持为真实设计缺口。后续报告必须优先展示分层指标，总体分只用于兼容。

## 2026-09-22 - Harness Review Is A Validation Stage

Decision:
Harness Review 不再是零命令 checkpoint。所有工作项必须校验 design feedback；存在 Oracle 资产时必须校验 freeze/input/score 完整性、冻结哈希和当前评分重算一致性。Review fingerprint 必须包含这些输入，内容变化后旧 checkpoint 不得继续复用。

Reason:
此前 `review=succeeded` 只表示 review record 与 quality report 文件存在，不能证明 design feedback 合法、冻结资产未漂移或 Oracle score 未过期，容易把人工产物存在误当成 Review 结论可信。

Impact:
四份 R3 run 的旧 Review checkpoint 均因 fingerprint 变化自动失效并以两个 validator 重跑成功。反馈回灌后只有 requirement summary 不变且所有反馈已 applied 才允许相对原始冻结基线产生可审计差异。

## 2026-09-22 - Case Plan Assertion Is The Direct Generator Oracle

Decision:
`case_plan_direct` 模式中，Acceptance Example 继续提供 Given/When 执行上下文；只要 Case Plan 提供 `assertion`，正式 testcase 的预期结果必须以该 assertion 为准。Design feedback 标记 `applied` 时可附带 `feedback_application.json`，记录目标设计层文件的前后 SHA-256；Review 与统一工作项校验在该凭证存在时执行确定性校验，禁止把正式 testcase 作为回灌目标。

Reason:
Celery DF-001 已正确写入 Case Plan，但生成器仍优先返回旧 Acceptance Example 的 Then，导致设计反馈无法下传正式用例。仅依赖人工说明“已应用”也无法证明修改发生在声明的设计层。

Impact:
Celery 三条相关用例已通过生成器获得“同步载荷仅包含任务 ID、不传播远端 monotonic 时间戳”预期；批准需求覆盖率达到 1.0。公开补丁独有的 oldest-first 顺序继续留在 implementation oracle，未升级为产品验收契约。

## 2026-09-22 - Feedback Receipt Enforcement Is Opt-In By Manifest Generation

Decision:
新建工作项默认设置 `pipeline_policy.feedback_application_receipt_required=true`。启用后，只要存在 `status=applied` 的 design feedback，就必须有完整 `design/feedback_application.json`；Review 和 strict 工作项校验始终执行该判断。旧 manifest 未声明策略时允许返回 `legacy_compatible`，不补造历史 before hash。

Reason:
仅在凭证文件已存在时才校验，无法阻止新流程漏写凭证；反过来要求所有历史 applied feedback 补凭证，会迫使系统伪造当时没有记录的修改前哈希。以 manifest policy 区分新契约与历史兼容可同时关闭新漏洞并保存旧事实。

Impact:
Celery 作为 opt-in 样本必须并已提供 verified receipt；第一轮 Appsmith、Chatwoot、Saleor 保持可验证的 legacy-compatible 状态。新工作项若直接把 feedback 改为 applied 而不提交凭证，将在 Review 和统一工作项校验失败。

## 2026-09-22 - Feedback Application Uses Prepare Then Record

Decision:
标准反馈回灌采用两阶段协议：`prepare` 在任何设计修改前冻结 accepted feedback、目标层和目标文件 SHA-256；`record` 只在 feedback fingerprint 未漂移且目标设计产物发生真实变化时生成 receipt。写入顺序固定为 receipt first、feedback status second，重复 record 必须能够完成中断恢复。

Reason:
强制 receipt 仍不能阻止操作者在修改后手工倒填 before hash。工具化的修改前快照能减少这一人为风险；先写 receipt 再置 applied 可保证任一中断状态都会被现有门禁拒绝，且可安全重试。

Impact:
标准路径拒绝直接选择 `testcases_main.md`、覆盖已有 baseline、无变更 record 和 prepare 后修改 feedback 内容。baseline 快照保留在 `.generation/feedback_applications/`，不影响正式 testcase 真源。

## 2026-09-22 - Agent Feedback Application Uses A Dedicated Action Runtime

Decision:
Agent 回灌 design feedback 必须通过独立的受限 Action Runtime。Schema 仅允许 `prepare_feedback_application`、`propose_feedback_design_artifacts`、`record_feedback_application`；propose 只能写 prepare 快照中冻结的设计层路径，record 是唯一可以把反馈状态置为 `applied` 的动作。

Reason:
两阶段命令能证明 before hash 和真实变化，但若 Agent 仍可直接写工作项文件，设计修改与状态迁移就没有统一能力边界。把编辑动作纳入同一白名单后，Runtime 可以在写入前验证 feedback identity、fingerprint、target layer 和具体路径。

Impact:
受限入口不能修改 `design_feedback.json`、`feedback_application.json` 或正式 testcase，也不接受 shell 动作。外部进程仍拥有操作系统层面的文件权限，因此 Review/strict receipt gate 继续作为绕过 Runtime 后的确定性兜底；下一阶段可补不可变 action journal 和 Harness audit 重放。

## 2026-09-22 - Feedback Actions Use Immutable Intent And Result Records

Decision:
每个 feedback Action ID 分别持久化不可覆盖的 intent 与 result。相同 ID 只能绑定同一请求；完成结果可幂等复用，intent 后中断可用原动作恢复，确定性失败也必须形成 result。新工作项默认要求 applied feedback 具备完整 prepare/propose/record journal。

Reason:
仅有最终 receipt 无法证明 Agent 实际通过受限入口执行，也无法区分进程中断与无日志绕过。双记录既保留执行前意图，又避免通过覆写单一状态文件改写历史；失败结果终态化则避免一次可预期拒绝永久留下“疑似崩溃”。

Impact:
`audit-feedback-actions`、Harness Review 和 strict 会验证请求哈希、intent/result 配对、成功动作顺序、receipt 与最终状态；journal 变化会失效旧 Review checkpoint。旧 manifest 未启用策略时保留 legacy compatibility，不补造历史动作。当前日志尚未绑定具体 Harness run 或执行主体，该增强属于后续责任追踪而非正确性门禁。

## 2026-09-22 - Framework Validation Must Be Business-Sample Independent

Decision:
质量基线、Eval Golden、Harness Runtime 单元测试和收口脚本不得默认绑定任何具体业务工作项。业务样本只能作为显式输入单独校验；框架回归使用匿名、自包含 fixture。

Reason:
把 PT083 同时作为需求样本和框架默认正向样例，会让样本自身变化影响框架结论，并使“该需求通过”被误读为“项目通过”。测试代码直接复制业务目录还会形成隐藏依赖。

Impact:
基线移除业务工作项与项目壳命令；Golden 仅比较通用 fixture；收口入口要求显式项目和工作项参数；Runtime 测试迁移到匿名 fixture。新增独立性门禁，阻止已知业务样本标识和工作项校验命令重新进入框架验证范围。真实业务目录与历史记录不改写。

## 2026-09-22 - Feedback Action Journal Binds Trusted Execution Context

Decision:
feedback Action Runtime 必须从 action payload 外部接收 Harness `run_id`、`actor` 与 `provider`。journal 1.1 的 intent/result 同时记录该上下文，request hash 绑定 action 与上下文；同一 feedback 的成功动作必须属于同一 run。

Reason:
仅记录动作内容无法证明动作属于哪个执行过程，也无法识别跨 run 拼接或执行身份被改写。由调用边界注入上下文可以阻止模型在 action 内自报身份，并让 Harness audit 将反馈动作归属到具体 run。

Impact:
新工作项默认强制执行身份绑定；Runtime 和审计验证 run 存在、项目/工作项匹配以及 intent/result 上下文一致。旧 1.0 journal 继续只读兼容，不能补证历史身份。`actor` 与 `provider` 当前是可审计声明，不等同于宿主认证凭证。

## 2026-09-22 - No-Code Review Requires A Run-Scoped Disposition

Decision:
新工作项默认启用 `review_disposition_required=true`。没有业务代码输入时，必须由人工对具体 validate run 声明 `not_applicable`、执行者和原因，凭证绑定当时的 `code_review_scope.json`。Review 的确定性 validator 仍必须执行，通过后阶段记录为 `skipped`，strict gate 才可跳过代码评审资产。

Reason:
无代码工作项不应伪造代码评审完成，但直接使用全局 `--skip-code-reviews` 又缺少责任人、原因、run 归属和输入绑定。独立 disposition 可区分“不适用”与“尚未评审”，同时保留设计反馈、回灌和 Oracle 门禁。

Impact:
CI 不得自行声明 N/A；存在代码目录、Traceability 未成功或 scope 漂移时声明无效。run audit 校验凭证、声明事件、阶段终态和前置阶段。旧 manifest 延续原跳过行为，避免破坏历史运行；既有 run 不会被框架自动补写人工声明。

## 2026-09-22 - Requirement Summary Metadata Is Not An Executable Rule

Decision:
Reasoning 生成器不得把“关键数据”“关键契约”“关键公开 API”“资源字段”等清单说明，或“PR 未声明新增项”这类范围声明，归类为 `explicit_rules` 或生成 Coverage 候选；明确的输入、输出和行为契约仍保留。

Reason:
最终轮盲测发现，第 7 节的说明性元数据会被统一规则抽取逻辑提升为正式行为，导致后续 Coverage 数量虚高并可能生成不可执行用例。

Impact:
四份 R4 Reasoning Pack 共移除 8 条伪规则，真实规则、风险和待确认项不变。新增解析回归测试；历史产物不批量改写，重新生成时自动应用新口径。

## 2026-09-22 - Explicit Coverage Uses Feature Context And Rule Identity

Decision:
Coverage 生成器必须使用 Structured PRD `explicit_rules[].applies_to` 映射对应 feature 的页面、板块和模块上下文；Coverage 标题与去重身份必须来自具体规则文本或 atomic assertion，不能仅使用共享的 feature 名称。

Reason:
最终轮盲测发现，多 feature 工作项的顶层规则会丢失上下文；补上映射后，如果仍用 `applies_to` 作为标题，同一 feature 下的多条独立规则会被误合并。

Impact:
四份 R4 矩阵的 43 项主覆盖均获得完整上下文，且同一 feature 的不同规则保持独立。新增两项生成器回归测试；历史 Coverage 不批量改写，重新生成时应用新口径。

## 2026-09-22 - Testability Gate Binds Rule Identity And Text

Decision:
Testability Gate 除覆盖 Structured PRD 的 `rule_id` 外，还必须保证 `source_text` 与该规则正文一致；同一 ID 下的文本漂移必须判定为校验失败。

Reason:
只校验 ID 存在无法阻止规则内容在 Gate 中被静默改写，可能让后续 Acceptance Example 在看似完整的追溯链上执行错误语义。

Impact:
Gate Validator 新增规则正文一致性检查与正反向回归测试。四份 R4 Gate 全部精确匹配；历史已验证样本抽查无不兼容项。

## 2026-09-22 - Case Plan Direct Tagging Uses Explicit Side Or Terminal

Decision:
`case_plan_direct` 生成标签时，先使用明确的验证侧语义；若验证侧没有前后端关键词，则以稳定 testcase ID 中的 `API` / `SERVER` 终端段作为 `AI-API用例` 兜底。“列表”本身不再作为 `AI-UI用例` 判据。

Reason:
最终轮生成发现 APIStore 列表读取、TTS 音频解码和 BroadcastLogger 标签等纯后端用例会因为“列表”或缺少固定关键词而被误标为 UI 用例，导致执行载体与真实验证面不一致。

Impact:
四份 R4 后端样本重新生成后不再包含错误的 `AI-UI用例` 标签；显式包含页面、前端、展示或 B/C 端语义的计划仍可生成 UI 标签。新增 SERVER 兜底和 API 列表反例测试，历史资产不批量改写。

## 2026-09-22 - Coverage-First Traceability Preserves Explicit Rule IDs

Decision:
Coverage-first traceability 必须优先从 `structured_refs` 解析并保留实际显式规则 ID，不再把规则 ID 限定为 `ER-数字`；只有不存在合法显式引用和 ID 型 `rule_name` 时才使用上下文合成标识。

Reason:
最终轮盲测的规则采用 `GRA-R001`、`HA-R001`、`RAI-R001`、`K8S-R001` 等项目级命名。旧逻辑会把它们退化成重复的模块/功能/coverage-type 字符串，虽然 Coverage 与 testcase 存在，规则身份却不精确。

Impact:
四份 R4 追溯的 43 条记录均绑定真实 Structured Rule ID；旧描述型 `rule_name` 仍保留原 fallback 行为。新增自定义规则前缀与 fallback 回归测试，历史资产不批量改写。

## 2026-09-22 - Oracle Coverage Must Remain Layered

Decision:
最终轮公开盲测继续分别报告 requirement、implementation 与 risk Oracle coverage；总体分只作为补丁差异规模指标，不能用实现级缺口反推需求用例不相关或直接修改正式 testcase。

Reason:
Grafana #133083 的公开实现包含版本上限、错误传播和并发安全等需求摘要未确认的实现契约，使总体 Oracle coverage 明显低于需求层覆盖率。若合并口径，会把合理的需求边界误判为主流程失败，并诱发 Oracle 反向污染。

Impact:
四份 R4 的 43 条正式 testcase 相关率均为 1.0；6 条新发现只进入 design feedback。后续必须先分流反馈，需求可确认项才进入 Acceptance/Case Plan，纯实现风险保留在 Gate 或验证责任层。

## 2026-09-22 - Approved Requirement Gaps Re-enter At Testability Gate

Decision:
Oracle 发现若能追溯到已批准 Requirement Summary 与 Reasoning 的明确规则，但在 Structured PRD 后续链路漏传，应从 Testability Gate 重新进入正式设计链；不得直接修补 Case Plan 或 testcase。仅存在于实现 diff 的行为继续作为 risk-only，未决语义继续保持 needs-confirmation。

Reason:
Grafana 的 Serializer 接收请求 context 已由获批摘要和 `ER-002` 明确，但正式设计只覆盖了 watch context。直接修改 Case Plan 会跳过 Gate 与 Acceptance 的来源约束，既破坏追溯，也会把一次样本修复伪装成完整设计。

Impact:
Grafana DF-002 的 target layer 调整为 Testability Gate；下一阶段先生成可审计 Gate 决策，再顺序重建下游。其余 5 条反馈不会自动升级为正式业务用例。

## 2026-09-22 - Sequential Feedback Applications Form A Hash Chain

Decision:
同一设计产物连续承接多个 feedback 时，回灌凭证按目标路径组成有序哈希链；后一个 application 的 `before_sha256` 必须等于前一个 `after_sha256`，只有链尾必须等于当前文件。

Reason:
旧校验要求每个历史 receipt 的 `after_sha256` 都等于当前文件，第二次合法修改同一 Gate 后，第一份历史凭证必然被误报为过期。该约束既不支持批次回灌，也无法表达真实的版本演进。

Impact:
合法连续回灌可审计通过；缺失中间环节、前后哈希断裂或链尾与当前文件不一致仍会失败。此规则是框架通用逻辑，不绑定 Grafana、PT083 或任何单一样本。

## 2026-09-22 - Late Review N/A Declaration Reopens Deterministic Review

Decision:
当 validate run 的 Review 已成功、Strict Gate 尚未执行且本地代码目录确实为空时，允许用户补充 run-scoped `not_applicable` 声明；Runtime 必须把 Review 重开为 pending，清除旧 checkpoint，再重新执行全部 Review validator，成功后才记录为 `skipped/not_applicable`。

Reason:
旧生命周期只允许在 Review 前声明 N/A。若 Agent 先运行确定性 Review，用户随后批准 N/A，run 会永久卡在 Strict 前；直接保留 succeeded 又会使审计无法证明 N/A 路径重新执行过 Review。

Impact:
补充声明不会绕过 Review、Oracle、feedback receipt 或 Action journal；Strict 已运行、存在本地代码目录、Traceability 未成功或非人工环境时仍拒绝声明。新增回归测试覆盖成功 Review 后声明、重跑和审计闭环。

## 2026-09-22 - Feedback Application Journal Is A Release Artifact

Decision:
工作项 `.generation/feedback_applications/` 下的 baseline 快照与不可变 Action journal，以及 identity 校验所需的 `run_state.json` 和人工 `review_disposition.json` 属于 strict 可复验的正式审计证据，必须进入版本库；其余 run 过程文件与根级可再生评测/动作输入不进入版本库。

Reason:
新工作项启用 `feedback_action_journal_required=true` 后，applied feedback 缺少完整 journal 会被 Review 和 strict 拒绝。整体忽略 `.generation/` 会导致本地通过、干净克隆后无法复验。

Impact:
发布包保留 feedback prepare/propose/record 的 intent/result 与 before snapshot，并保留校验执行身份所需的最小 run 元数据；继续排除 events、诊断、hook、阶段日志、当前 run 指针、覆盖率数据库和根级生成缓存。
