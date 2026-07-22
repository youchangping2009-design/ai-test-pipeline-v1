# Decision Log

本文件只记录已经确定的关键决策，不记录执行流水账。

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
切换 testcase 真源会影响 validators、exporters、regeneration bundle、traceability builder 和团队交付习惯；Codex 不应自行切换。

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

## Decision Format

后续新增决策时使用：

```text
YYYY-MM-DD - Decision Title
Decision:
Reason:
Impact:
```

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
