# Progress

本文件是阶段流水账，不是真源，也不进 strict。当前任务、决策和阻塞分别写在 `docs/roadmap/NEXT_ACTION.md`、`DECISION_LOG.md`、`HUMAN_ACTION_REQUIRED.md`。新条目只追加到文末，禁止插入文件顶部或按 newest-first 回写。

## 2026-09-21 - OSS Blind Round Requirement Intake

- 初始化 `OSS-BLIND` 项目及 `APPSMITH-42244`、`CHATWOOT-15768`、`SALEOR-19804` 三个 M 档工作项。
- 只消费公开 PR 描述与其明确关联的公开 issue/原始 PR，分别生成 `inputs/public_source_snapshot.md`、`requirement_summary.md` 和 `source_manifest.json`；代码 diff 与已有测试被隔离为后续评分 oracle，不进入需求输入。
- Appsmith 的 Linear issue 需要授权，GitHub Advisory API 未返回详情，均记录为未解决来源；未据此脑补安全规则。
- 本轮只执行 Requirement Intake，未进入 Evidence、Reasoning、Structured PRD、Coverage、Case Plan 或 Testcase；下一步必须先由用户审核三个摘要并通过正式 approval CLI。
- 三份 Requirement Sources strict 均通过；对应 Harness run 已创建并停在 `waiting_approval`，下游阶段全部为 `pending`。
- `scripts/run_quality_baseline.py` 5/5 通过，包含105项单测、PT083 non-strict/strict、regression和项目壳校验。

## 2026-09-21 - OSS Blind Round Requirement Approval And Evidence

- 用户明确批准三份需求摘要后，使用正式 CLI 以 reviewer `ycp` 分别批准三个当前内容绑定的 receipt；未手写或复制 approval 文件。
- 三个 run 的 `requirement_intake` 均转为 `succeeded`，并分别 `resume --stop-at evidence`；Evidence 均为 `succeeded/attempts=1/exit=0`。
- 三个样本均为纯文本公开来源，保留初始化的合法空图片证据状态；未因缺少截图阻塞，也未伪造图片 evidence。
- 当前三个 run 均为 `paused`，Reasoning 及全部下游阶段为 `pending`。本轮未跨入 Reasoning、未修改业务代码、未读取 oracle 生成下游资产。

## 2026-09-21 - OSS Blind Round Reasoning Analysis

- 使用正式 `reasoning-analysis` 入口，分别从已批准的 `requirement_summary.md`、`source_manifest.json` 与空图片 Evidence 生成三份 `reasoning_pack.json` / `analysis_report.md`；未读取 Structured PRD、代码 diff 或已有测试作为生成输入。
- 首次内容审查发现通用生成器无条件注入 PT083 的 banner/瓷片/金刚区风险与测试维度，Schema 虽可通过但构成跨样本语义污染。
- 第 1 轮最小修复移除无条件业务模板：文本需求现在从摘要第 8 节生成风险、第 9 节生成待确认项、第 6 节提取边界场景，并从显式规则生成通用测试维度与 coverage candidates；图片输入的排序、状态和说明表风险只在存在对应证据时生成。
- 修复后 Appsmith 为 14 explicit / 3 risks / 3 edges / 4 ambiguities / 14 candidates；Chatwoot 为 15 / 3 / 4 / 4 / 15；Saleor 为 15 / 4 / 4 / 4 / 15。三个 analysis 目录均无 PT083 领域词残留。
- 新增 2 项文本需求回归测试；三份 Reasoning Pack Schema Validator 与三个 Harness `reasoning` checkpoint 均通过。三个 run 继续为 `paused`，Structured PRD 及下游保持 `pending`。
- `scripts/run_quality_baseline.py` 5/5 通过，包含 107 项单元测试、PT083 non-strict/strict、regression 和项目壳校验；未修改业务代码或降低门禁。

## 2026-09-21 - Reasoning Three-layer Hardening And Blind Retest

- 完成领域解耦：移除通用生成器中 banner、瓷片、金刚区、企微、小程序活动等 PT083 专用业务模板；图片输入的共享结构、重复字段和跨页面承接改为使用当前 Evidence 的页面、板块与字段动态表达。
- 完成来源语义门禁：新增 Grounding Contract 1.0。内容型 reasoning 必须有非空来源，文本摘录必须能在来源文件回查，来源文件必须存在，测试维度与 coverage candidate 不得引用不存在的 reasoning ID；新工作项默认 `reasoning_grounding_required=true`。
- 完成跨领域回归：覆盖 API/安全 URL、前端 `0/false` 类型保持、数据关系一致性、图片配置页与文本图片混合需求，并补充无来源污染、摘录不匹配、悬空 ID、缺失契约和 Harness 实际执行 Validator 的故障注入测试。
- Harness 的 Reasoning 从空命令 checkpoint 改为 validation。复验时进一步发现“显式 stop-at 已成功 checkpoint 会继续向下执行”缺陷，已修复为立即暂停；显式回退到较早 stop-at 时，下游旧 checkpoint 重置为 pending。
- 三份公开盲测均重新通过 Grounding Contract，Reasoning 日志各执行 1 条 Validator 命令；三个 run 已恢复为 `paused at reasoning`，Structured PRD 及下游均为 `pending`。过程中误触发的空 Testability Gate 失败已保留 attempt 计数但清除为 pending，未伪造成功。
- 全量 119 项单元测试通过；质量基线 5/5 通过，PT083 non-strict/strict、regression 与项目级 strict 均未回退。

## 2026-09-21 - OSS-BLIND Structured PRD

- Scope: 本轮仅处理 Appsmith #42244、Chatwoot #15768、Saleor #19804 的 Structured PRD；未读取代码 diff 或已有测试 oracle，未进入 Coverage、Testability Gate、Case Plan 或 testcase。
- Inputs consumed: 三份已批准的 `inputs/requirement_summary.md`、`inputs/source_manifest.json` 与通过 Grounding Contract 的 `analysis/reasoning_pack.json`。
- Outputs: 分别编写 `structured_prd/structured_prd.md` 真源，并由正式编译器生成 `structured_prd/structured_prd.json`。Appsmith 为 6 条显式规则、5 条 feature rule、2 个字段、1 条 flow；Chatwoot 为 7 条显式规则、8 条编译后 feature rule、5 个字段、1 条 flow；Saleor 为 7 条显式规则、7 条编译后 feature rule、8 个字段、1 条 flow。
- Semantics: Appsmith 聚焦连接前协议校验、Databricks driver 独占处理与失败关闭；Chatwoot 聚焦类型化值、0/false 保留、缺失值区分与严格相等；Saleor 聚焦跨批次标签关系追加、历史成员保留与返回契约。未把风险边界提升为已确认规则，三个产物均无 PT083 的 banner/瓷片/金刚区语义。
- Validation: 三份 Markdown 均成功编译且 Structured PRD Schema Validator 通过，无 repair；三个既有 run 均以 `resume --stop-at structured_prd` 成功暂停，Structured PRD 为 succeeded，Coverage 及下游保持 pending。
- Baseline: 119 项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线 5/5 通过。
- Next: 下一阶段仅生成并校验三个样本的 Coverage Matrix，不进入 Testability Gate。

## 2026-09-21 - OSS-BLIND Coverage Planning

- Scope: 本轮仅生成和校验三个公开盲测样本的 `coverage/coverage_matrix.json`，未读取代码 diff 或已有测试 oracle，未进入 Testability Gate、Acceptance Examples、Case Plan 或 testcase。
- Initial finding: 正式生成器首轮虽通过 Schema，但 Appsmith、Chatwoot、Saleor 分别只有1、2、2条 main Coverage；原因是通用业务规则未进入主链，生成器主要依赖字段形态及 PT083 专用关键词分支。
- Repair 1: 新增通用显式规则投影；优先从 `requirement_info.explicit_rules` 建立主 Coverage，旧资产缺少显式规则时才回退 `feature.rules`。Reasoning 的 edge case 与 business risk 统一保留为 `ai_reasoning/audit_item`，PT083 专用注入分支不再进入正式生成路径。
- Repair 2: 只允许可编辑输入字段生成 min/max/max_length 边界 Coverage，避免只读响应字段 `result_count` 被错误生成输入边界用例。
- Outputs: Appsmith 14条（6 main / 8 audit）、Chatwoot 19条（7 main / 12 audit）、Saleor 23条（6 main / 17 audit）。三个样本全部已确认显式规则均已映射，AI reasoning 进入 main 数量为0，未出现 banner/瓷片/金刚区/PT083 语义污染。
- Validation: Coverage Schema/Semantic Validator 全部通过；新增4项生成器回归测试通过；三个既有 run 均以 `resume --stop-at coverage` 成功暂停，Coverage 为 succeeded，Testability Gate 及下游保持 pending。
- Baseline: 123项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线5/5通过。
- Next: 下一阶段仅生成并校验三个样本的 Testability Gate，不进入 Acceptance Examples。

## 2026-09-21 - OSS-BLIND Testability Gate

- Scope: 本轮仅生成并校验三个公开盲测样本的 `acceptance/testability_gate.json/md`，未读取代码 diff 或已有测试 oracle，未生成 Acceptance Examples、Case Plan 或 testcase。
- Coverage consistency repair: Gate 前复核发现 priority=medium 的已确认规则被统一降为 audit；已改为仅依据“待确认”语义降级。Chatwoot“数量徽标与会话列表一致”恢复为 main，Saleor 缺性能阈值的规则继续保持 audit。
- Outputs: Appsmith 14条 Gate（6 generate / 5 skip duplicate / 3 risk note）；Chatwoot 18条（7 generate / 8 skip duplicate / 3 risk note）；Saleor 18条（6 generate / 7 skip duplicate / 4 risk note / 1 needs confirmation）。
- Guardrails: Structured PRD 中全部稳定 rule_id 均经过 Gate；feature/field 同义规则使用 `skip_case` 去重。10条 Reasoning business risk 全部为 `risk_hardening/risk_only/risk_note_only`，Saleor 性能阈值为 `needs_confirmation`，没有风险或未决项进入正式验收候选。
- Validation: 三份 Testability Gate Validator 均通过；Appsmith 首轮仅因 reason 中“验收示例”触发占位词检查，最小改写措辞后通过。三个既有 run 均以 `resume --stop-at testability_gate` 成功暂停，Acceptance Examples 及下游保持 pending。
- Baseline: 124项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线5/5通过。
- Next: 下一阶段仅生成并校验三个样本的 Acceptance Examples，不进入 Case Plan。

## 2026-09-21 - OSS-BLIND Acceptance Examples

- Scope: 本轮仅生成并校验三个公开盲测样本的 `acceptance/acceptance_examples.json/md`，未读取代码 diff 或已有测试 oracle，未进入 Case Plan、testcase 或更下游阶段。
- Outputs: Appsmith 6条、Chatwoot 7条、Saleor 6条规则级 Given/When/Then；19个 `generate_acceptance_example` Gate 全部且仅被覆盖，每条均保留 source gate、source rule 与 main coverage 引用。
- Semantics: Appsmith 覆盖连接前协议校验、driver 选择、失败关闭、token 兼容和无错误目标连接副作用；Chatwoot 覆盖 number 类型、0/false、缺失值、严格相等、运算符、列表计数及既有筛选回归；Saleor 覆盖标签追加、新标签创建、跨批次集合、混合标签、返回契约及既有接口回归。
- Guardrails: 10条 Reasoning 风险、所有 `skip_case` 及 Saleor 性能阈值 `needs_confirmation` 均未进入正式验收示例；未出现 PT083 的 banner/瓷片/金刚区语义。
- Validation: 三份 Acceptance Examples Validator、JSON/Markdown 数量一致性和 gate/rule/coverage 追溯守卫均通过。三个既有 run 均以 `resume --stop-at acceptance_examples` 成功暂停，Case Plan 及下游保持 pending。
- Baseline: 124项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线5/5通过。
- Next: 下一阶段仅生成并校验三个样本的 Case Plan，不进入 Testcase Generation。

## 2026-09-21 - OSS-BLIND Case Plan

- Scope: 本轮仅生成并校验三个公开盲测样本的 `testcases/case_plan.json/md`，未读取代码 diff 或已有测试 oracle，未生成正式 testcase、testpoints、traceability 或 review 产物。
- Outputs: Appsmith 6条、Chatwoot 7条、Saleor 6条 Case Plan；全部使用 `generation_mode=case_plan_direct`，19条计划分别映射唯一稳定 testcase ID。
- Traceability: 19个 Acceptance Example 与19个允许 Gate 全量且仅被承接；每条计划同时记录 source rule 与 main Coverage，所有计划均为 `product_acceptance`、`should_generate_case=true`。
- Semantics: Appsmith 计划覆盖协议、driver 路由、失败关闭、token 兼容与网络副作用；Chatwoot 覆盖类型、falsy 值、严格相等、运算符、数量展示及回归；Saleor 覆盖新旧标签、跨批次成员集合、响应落库一致性及既有错误/接口行为。
- Numbering: 在统一编号规则中登记 `DATABRICKS/CONNECT`、`CONVERSATION/FILTER`、`GIFTCARDBULK/BULKCREATE` 页面与板块编码，未引入未登记的 testcase 编号片段。
- Guardrails: 未纳入风险、`skip_case` 或 Saleor 性能阈值待确认项；M 档未伪造 `source_responsibility_ids`，未出现 PT083 领域语义。
- Validation: 三份 Case Plan Schema/Validator、Gate/Acceptance/Rule/Coverage 追溯、唯一 testcase ID 与 JSON/Markdown 数量一致性检查均通过。三个既有 run 均以 `resume --stop-at case_plan` 成功暂停，Testcase Generation 及下游保持 pending。
- Baseline: 124项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线5/5通过。
- Next: 下一阶段仅从 Case Plan 生成正式 testcase 与同步 testpoints，不进入 Traceability 或 Review。

## 2026-09-21 - OSS-BLIND Testcase Generation

- Scope: 本轮仅执行 Testcase Generation，并同步生成 `testcases_main.md`、`testcases.md`、`testpoints.json/md`、开发自测与审计派生物；未刷新 bundle、traceability、review 或 strict gate，未读取代码 diff/已有测试 oracle。
- Initial finding: direct-mode 首次虽正确生成6/7/6条并保持一计划一用例，但通用步骤模板仍把 Chatwoot 筛选与 Saleor GraphQL 场景写成“点击保存/重新打开记录”，Appsmith linkage 出现泛化 B端/服务端/C端检查，API 场景还被标记为 AI-UI。
- Repair 1: direct renderer 显式消费 Acceptance Example 的 Given/When/Then，保留 Case Plan 标题与类型意图，并按 `verification_side` 分配 API/UI 标签；新增跨领域 API 回归单测。
- Repair 2: 按正式 lint 结果对尚未发布的 Case Plan 稳定编号与测试类型做一致性收敛；Chatwoot 输入到请求到匹配作为流程计划，其余值判断归入数据校验；技术运算符正文转为“等于/不等于”；linkage 补充可查询最终状态。
- Outputs: Appsmith 6条（功能/异常/流程验证）、Chatwoot 7条（功能/数据校验/流程验证）、Saleor 6条（数据校验/权限/流程验证）。三份主用例与兼容镜像一致，19条 testpoints 与19条 Case Plan 一一对应。
- Guardrails: 正式用例中不再出现错误的保存模板、泛化 B/C 端检查或 PT083 领域词；所有用例均保留 CasePlan、Acceptance、Rule、Coverage 引用。Saleor 元素标注仅剩6条普通“接口”名词建议反引号的 warning，无 error。
- Validation: 三份 testcase lint、元素标注 strict、页面板块 strict、testpoints strict、携 testcase 的 Case Plan Validator 均通过；三个既有 run 以 `resume --stop-at testcases` 成功暂停，Traceability 及下游保持 pending。
- Baseline: 125项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线5/5通过。
- Next: 下一阶段仅刷新 bundle、必要派生资产与 Coverage-First Traceability，不进入 Review 或 strict gate。

## 2026-09-21 - OSS-BLIND Bundle And Coverage-First Traceability

- Scope: 本轮仅刷新三个公开盲测样本的 testcase 派生资产并生成 Coverage-First Traceability；未读取代码 diff 或已有测试 oracle，未进入 Review 或 strict gate。
- Outputs: Appsmith、Chatwoot、Saleor 的 Bundle/Testpoints 分别为 6/6、7/7、6/6，开发自测分别为 5、5、4 条；Coverage-First/Adapter 分别为 6/6、7/7、6/6。
- Authenticity: 三个工作项的 main Coverage ID、追溯 Coverage ID、Bundle testcase ID 与追溯 testcase ID 均精确一致；全部 `invalid_record_count=0`、`false_traceability_rate=0.0`，未补写虚假映射。
- Validation: 三份 testpoints strict、Bundle Validator、Traceability Primary Validator 均通过；三个既有 run 均以 `resume --stop-at traceability` 成功暂停，Traceability 为 succeeded，Review 与 strict gate 保持 pending。
- Baseline: 125 项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线 5/5 通过。
- Next: 下一阶段仅进入 Review，冻结当前资产后使用隔离的公开 diff 与已有测试作为评分 oracle；不直接改写 testcase，不进入 strict gate。

## 2026-09-21 - OSS-BLIND Oracle Review

- Scope: 在读取 oracle 前冻结三份工作项从 requirement summary 到 Coverage-First Traceability 的 8 类资产；随后只读取三个公开 PR 的固定 head SHA、changed files patch 与新增测试断言。未修改正式 testcase 或上游设计真源，未进入 strict gate。
- Appsmith: 核心协议拦截、指定 driver、失败关闭和 token 兼容命中；确认精确错误文案、`UID/PWD` 映射与失败分支原子性 3 条反馈，建议开始测试。
- Chatwoot: number 输入、0/false、缺失值和严格匹配命中；确认空数组/空对象、`days_before=0` 两条遗漏，以及 context-only 数量徽标进入 main 的范围过伸，建议带风险开始测试。
- Saleor: `add(*instances)` 关系追加与跨批次标签集合主链命中；确认标签大小写归一/重复去重遗漏及 CP-003 oracle 抽象两条反馈，建议带风险开始测试。
- Review outputs: 三份 `reviews/code_change_risk_report.md`、三份 `reviews/blind_asset_freeze.json`、三份 `review_record.md` 与 8 条 `design_feedback`；聚合结论写入 `reports/round_2_oracle_review.md`。
- Validation: 三份 design feedback validator 通过；内置 scorer 已刷新质量报告，Appsmith/Chatwoot 无 weak case，Saleor 报告 1 条 abstract oracle warning；三个既有 run 均以 `resume --stop-at review` 成功暂停，Review succeeded，strict gate pending。
- Limitation: 三个业务仓库未本地 checkout，因此仅完成 L0/L1 静态映证，上游单测 L2 未执行；不把 PR 已合并或测试代码存在等同于本地测试通过。
- Next: 下一阶段先归类并修复可通用化的流程问题，不针对单个样本直接补写 testcase，也不进入 strict gate。

## 2026-09-21 - Generic Source Scope, Atomicity And Oracle Delta

- Scope: 只修复公开盲测暴露出的通用流水线能力；未改三份冻结的 Structured PRD、Coverage、Gate、Acceptance、Case Plan、testcase 或 traceability，未进入 strict gate。
- Source scope: Structured PRD 显式规则新增兼容字段 `source_scope=primary_requirement/context_only/oracle_only`；Coverage 生成器将后两类固定降为 audit，Validator 阻止其进入 main。
- Atomicity: 显式规则可提供 `atomic_assertions`，Coverage 按独立断言拆分；scorer 新增多失败分支弱用例识别，能够命中 Appsmith CP-004。
- Oracle scoring: 新增 `scripts/score_oracle_delta.py`，强制全部冻结 testcase 完成范围分类，并分别计算 oracle coverage 与 testcase relevance；missing/partial 必须关联 design feedback。
- Blind scores: Appsmith `0.8333/1.0`，Chatwoot `0.6875/0.8571`，Saleor `0.5833/1.0`（oracle coverage/testcase relevance）。
- Compatibility: 新字段保持可选，旧 Structured PRD 缺省按 `primary_requirement` 处理；未降低任何既有 gate。
- Validation: 聚焦单测 17/17、三份 oracle-delta 输入校验与评分、质量基线 5/5（132 项单测）全部通过；三份冻结清单中的正式资产哈希保持一致。
- Next: 下一阶段应用 8 条 design feedback，从设计层重生成三份样本并对比冻结基线，不直接手改 testcase。

## 2026-09-21 - Process Journal Write Rules Unified

- 盘点过程文档职责后统一写法：当前状态就地改，带日期流水账只追加到文末。
- `PROGRESS.md`、`DECISION_LOG` 带日期条目、`NEXT_ACTION` Completion Notes 禁止插到顶部；`WORK_QUEUE` 只改表格；`HUMAN_ACTION_REQUIRED` 未决项就地改，Resolved 追加到末尾。
- 将误插在 `DECISION_LOG` 顶部的 `2026-09-21 Blind Oracle Feedback Isolation` 移回文末；将 `NEXT_ACTION` 中 2026-09-04 walkthrough 从 Completion Notes 节首移到节末。
- 未修改业务代码、工作项产物或规则强度。

## 2026-09-21 - OSS-BLIND Round 2 Strict Gate Closeout

- Scope: 仅将 Appsmith #42244、Chatwoot #15768、Saleor #19804 三个既有 run 从 Review 推进到 Harness `strict_gate`，未修改三份业务设计或正式 testcase。
- First attempt: 三个 strict gate 均只因纯文本来源的空 `image_evidence` 被旧校验分支判定为失败；其余 Manifest、Requirement、Design、Traceability、Testcase、Bundle、Testpoints、Case Plan 与 Review Gate 全部通过。
- Repair 1: `validate_work_item.py` 改为仅在来源清单含可用图片或 inventory 实际非空时执行图片非空校验；纯文本空 inventory 显式记为 SKIPPED，有图片来源及非空 inventory 仍保持强校验。
- Result: 三个原 run 的 strict gate 均在第 2 次尝试成功，run 状态全部为 completed。OSS-BLIND 项目视图刷新为 3/3 ready、25 条 testcase、0 个开放风险、0 个过期质量报告。
- Baseline repair: 全量基线额外暴露 strict 开发自测参数未接通、恢复到既有 checkpoint 误记 completed，以及四角色测试夹具依赖已删除导出文件；第 2 轮最小修复后聚焦 3 项测试和全量 134 项单测通过。
- Validation: 三份工作项 strict 均返回 0；`scripts/run_quality_baseline.py` 5/5 通过；未修改业务代码、未降低门禁、无需新增人工阻塞。

## 2026-09-21 - OSS-BLIND Round 2 Evaluation Closeout

- 汇总三份样本首轮与设计回修后的 Oracle 指标，新增 `reports/round_2_blind_test_closeout.md`；明确回修后的 1.0 是反馈闭环结果，不替代首轮真实能力。
- 首轮 Oracle coverage 为 Appsmith 0.8333、Chatwoot 0.6875、Saleor 0.5833；回修后三份 Oracle coverage 与 testcase relevance 均为 1.0。
- 归纳 7 类通用问题：领域模板污染、main Coverage 投影不足、来源范围过伸、复合断言未拆分、API 用例模板错误、纯文本图片门禁误阻断，以及 Harness checkpoint/strict 派生契约缺口。
- 扩测判断：可继续新增 3–5 个公开文本型 PR，但必须冻结后解封 Oracle、分别报告首轮与回修后指标，并优先覆盖本轮未涉及的需求形态。

## 2026-09-21 - OSS-BLIND-R3 Requirement Intake

- 初始化独立项目 `OSS-BLIND-R3` 和四个 M 档工作项：Django #21801（数据库迁移/唯一约束）、Celery #10668（撤销任务/跨主机时钟/滚动升级）、Temporal #11968（SignalWithStart 关闭后重试幂等）、Supabase #50569（MFA 恢复码/一次性消费/功能开关）。
- 每项写入 `inputs/public_source_snapshot.md`、`requirement_summary.md` 与 `source_manifest.json`；只消费 PR 作者正文及明确的公开问题描述，排除 changed files、提交 diff、新增测试和自动生成摘要。
- 四份 Requirement Sources strict 全部通过；四个 Harness run 完成 Requirement Intake 后均停在 `waiting_approval`，Evidence 及下游全部 pending。
- 当前需要用户审核四份需求摘要；未自动生成 approval receipt，未修改业务代码，未读取后置 Oracle。

## 2026-09-21 - OSS-BLIND-R3 Requirement Approval And Evidence

- 用户明确批准 Django #21801、Celery #10668、Temporal #11968、Supabase #50569 四份需求摘要；通过正式 `approve-requirement` CLI 写入四份与摘要、来源清单、原始输入和 run 绑定的 approved receipt，未手写或伪造审批文件。
- 复用四个既有 Harness run，以 `resume --stop-at evidence` 推进；四项 Requirement Intake 与 Evidence 均为 `succeeded`、attempt=1、exit=0，run 在 Reasoning 前保持 `paused`。
- 四个工作项均为纯文本来源，Evidence 阶段保持空图片 inventory 和空通用 evidence items 的显式边界；未读取 changed files、代码 patch、新增测试或自动摘要，Oracle 继续隔离。
- 本阶段未生成 Reasoning、Structured PRD 或后续测试资产，未修改业务代码。下一阶段仅生成并校验四份 Reasoning Pack。
- 四个 run 的审计均 `audit_passed=true`、`audit_errors=0`；全量质量基线 5/5 通过，134 项单元测试通过。

## 2026-09-21 - OSS-BLIND-R3 Reasoning Analysis

- Scope: 本轮仅从已批准的 `requirement_summary.md`、`source_manifest.json` 与纯文本 Evidence 边界生成四份 `analysis/reasoning_pack.json` 和 `analysis_report.md`；未读取代码 diff、新增测试或自动摘要，未进入 Structured PRD。
- Outputs: Django 14 条显式规则、3 条风险、1 条边界、3 条待确认、5 个测试维度、14 个 Coverage Candidate；Celery 为 16/4/1/4/7/16；Temporal 为 15/4/2/4/6/15；Supabase 为 15/4/1/4/6/15。
- Grounding: 四份产物均声明 Grounding Contract 1.0，内容型条目可回查当前需求摘要；测试维度与 Coverage Candidate 无悬空 Reasoning ID，未检出 PT083 或上一轮样本领域词污染。
- Validation: 四份 Reasoning Pack Validator 全部通过；四个原 Harness run 均以 `resume --stop-at reasoning` 成功暂停，Reasoning attempt=1、exit=0；run audit 4/4 通过。
- Baseline: 全量质量基线 5/5 通过，134 项单元测试通过。
- Next: Structured PRD 阶段需去重重复语义，并将“来源未声明接口/埋点”等缺失说明及示例配置信息保持为背景或审计信息，避免进入正式产品验收主规则。

## 2026-09-21 - OSS-BLIND-R3 Structured PRD

- Scope: 本轮仅生成并校验四份 `structured_prd.md/json`；未读取代码 diff、新增测试或自动摘要，未进入 Coverage。
- Outputs: Django、Celery、Temporal 各 6 条 primary rule，Supabase 为 6 条 primary rule 加 1 条 `context_only` 安全背景；四项均具备页面/系统观察面、模块、功能和 1 条三步骤 main flow。
- Semantics: Reasoning 中重复的目标、研发拆解和测试关注点已合并；复合分支通过 `atomic_assertions` 保留；“来源未声明接口/埋点”等缺失说明未进入显式规则，服务端样本未虚构 UI 控件。
- Repair 1: 首轮发现 Temporal 的 namespace、workflow ID、request ID、signal name 仅被列为关键输入，并无必填证据；已将 `required=true` 修正为 `false`，重新编译、校验并使 Harness 重新建立 Structured PRD checkpoint。
- Validation: 四份 Structured PRD Validator 全部通过；Harness Structured PRD 均 succeeded，Temporal attempts=2、其余 attempts=1；规则引用与 module/flow 映射检查通过，run audit 4/4 通过。
- Baseline: 全量质量基线 5/5 通过，134 项单元测试通过。
- Next: Coverage 阶段按原子断言拆分 main coverage，并将 Supabase `context_only` 安全背景固定降为 audit。

## 2026-09-21 - OSS-BLIND-R3 Coverage Planning

- Scope: 本轮仅从四份 Structured PRD 与 Reasoning Pack 生成并校验 `coverage/coverage_matrix.json`；未进入 Testability Gate，未读取后置 Oracle。
- Initial finding: Supabase 的父规则同时包含三个明确拒绝断言和“具体格式/错误文案待确认”，生成器按父句统一判断，将三个已确认原子断言全部错误降为 audit，造成主覆盖缺失。
- Repair 1: `generate_coverage_matrix.py` 改为在存在 `atomic_assertions` 时逐断言判断“待确认”，不继承父句中与该断言无关的未决限定；新增回归测试验证已确认原子断言保持 `main_testcase/business`。
- Outputs: Django 7 main / 4 audit，Celery 11 / 5，Temporal 8 / 11，Supabase 11 / 9；所有复合规则完成原子拆分，Supabase 3 条 `context_only` 安全断言全部为 audit。
- Validation: Coverage Generator 聚焦单测 9/9 通过；四份 Coverage Matrix Validator 全部通过；四个原 Harness run 均以 `resume --stop-at coverage` 成功暂停，Coverage attempt=1、exit=0；run audit 4/4 通过。
- Baseline: 全量质量基线 5/5 通过，135 项单元测试通过。
- Next: 下一阶段仅生成并校验 Testability Gate，不进入 Acceptance Examples。

## 2026-09-21 - OSS-BLIND-R3 Testability Gate

- Scope: 本轮仅生成并校验 Django #21801、Celery #10668、Temporal #11968、Supabase #50569 的 `acceptance/testability_gate.json/md`；未进入 Acceptance Examples，未读取后置 Oracle。
- Outputs: Django 12 条、Celery 14 条、Temporal 15 条、Supabase 18 条；全部 Structured PRD 稳定规则 ID 均经过门禁。
- Decisions: 主需求明确行为进入 `generate_acceptance_example`；feature/field 同义规则使用 `skip_case`；Reasoning 风险与 Supabase `context_only` 安全规则使用 `risk_note_only`。
- Pending semantics: Supabase 无效、空值、格式不正确输入的“不建立会话”结果可测，但具体格式规则和错误文案仍为 `partially_testable`，未生成强断言。
- Validation: 四份 Testability Gate Validator 全部通过；四个既有 run 均以 `resume --stop-at testability_gate` 成功暂停，Gate attempt=1、exit=0；run audit 4/4 通过。
- Baseline: 135 项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线 5/5 通过。
- Next: 下一阶段仅生成 Acceptance Examples，不进入 Case Plan。

## 2026-09-21 - OSS-BLIND-R3 Acceptance Examples

- Scope: 本轮仅从 Testability Gate、Structured PRD 与 main Coverage 生成四份 `acceptance/acceptance_examples.json/md`；未进入 Case Plan，未读取后置 Oracle。
- Outputs: Django 7 条、Celery 11 条、Temporal 8 条、Supabase 11 条，共 37 条原子 Given/When/Then。
- Traceability: 24 个 `generate_acceptance_example` Gate 全部覆盖；37 个 main Coverage 均被且仅被一个验收示例引用，Gate、Rule、Coverage 三向引用一致。
- Guardrails: 未消费 `skip_case`、`risk_note_only` 或 audit Coverage；Supabase 只验证明确的会话拒绝结果，不固化未定义的恢复码格式和错误文案。
- Validation: 四份 Acceptance Examples Validator 全部通过；JSON/Markdown 数量一致；四个既有 run 均以 `resume --stop-at acceptance_examples` 成功暂停，Acceptance attempt=1、exit=0；run audit 4/4 通过。
- Baseline: 135 项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线 5/5 通过。
- Next: 下一阶段仅生成 Case Plan，不进入正式 testcase。

## 2026-09-21 - OSS-BLIND-R3 Case Plan

- Scope: 本轮仅从四份 Acceptance Examples 生成并校验 `testcases/case_plan.json/md`；未生成正式 testcase，未读取后置 Oracle。
- Outputs: Django 7 条、Celery 11 条、Temporal 8 条、Supabase 11 条，共 37 条 `case_plan_direct` 计划。
- Traceability: 37 条计划与 Acceptance Example 一对一，均保留 Gate、Example、Rule、Coverage 引用；37 个 `generated_testcase_ids` 全局唯一。
- Numbering: 在统一编号规则中登记 `DJANGOMIG/INDEXSCHEMA`、`CELERYWORKER/REVOKE`、`TEMPORALAPI/SIGNALSTART`、`RECOVERYAUTH/RECOVERYCODE`；未使用未登记编号片段。
- Guardrails: 全部计划为 `product_acceptance` 且使用明确页面/板块和业务断言；M 档 `source_responsibility_ids` 保持为空，未纳入风险、context-only 或待确认细节。
- Validation: 四份 Case Plan Validator 全部通过；JSON/Markdown 数量一致；四个既有 run 均以 `resume --stop-at case_plan` 成功暂停，Case Plan attempt=1、exit=0；run audit 4/4 通过。
- Baseline: 135 项单元测试、PT083 non-strict/strict、6/6 regression fixtures 与 WX-YGJ project strict 全部通过，质量基线 5/5 通过。
- Next: 下一阶段仅生成正式 testcase、testpoints 与开发自测派生视图，不进入 Traceability。

## 2026-09-21 - OSS-BLIND-R3 Testcase Generation

- Scope: 本轮仅从四份 `case_plan_direct` 生成正式 testcase、兼容镜像、testpoints、开发自测和当前阶段审计产物；未生成 Bundle/Traceability，未进入 Review/strict gate，Oracle 继续隔离。
- Candidate findings: 首轮候选发现服务端验证端标签不明确、Django/Temporal 缺少流程型计划、Celery 两条边界计划被推断为功能、Supabase 两条异常计划类型不清及两个页面标题缺少元素标注。
- Repair: 语义债务回写 Acceptance/Case Plan；direct 生成器改为尊重显式 `case_type`，新增回归测试。未手改生成后的正式 testcase，未降低任何校验规则。
- Outputs: Django 7、Celery 11、Temporal 8、Supabase 11 条正式用例，共 37 条；每条均复用 Case Plan 预留 ID，并与 37 条 testpoint 一一对应。兼容 `testcases.md` 与主真源一致。
- Validation: 四份 testcase lint、元素标注 strict、页面板块 strict、testpoints strict、携 testcase 的 Case Plan Validator 全部通过；四个既有 run 均以 `resume --stop-at testcases` 成功暂停，testcases attempt=1、Traceability 及下游 pending；run audit 4/4 通过。
- Baseline: 全量质量基线 5/5 通过，136 项单元测试通过。
- Next: 下一阶段仅执行 Bundle 后处理与 Traceability，刷新派生产物和质量报告指纹后复用原 run 停在 Traceability，不进入 Review 或 strict gate。

## 2026-09-21 - OSS-BLIND-R3 Bundle And Traceability

- Scope: 本轮仅刷新 testcase bundle、testpoints、开发自测、Coverage-First Traceability、兼容 Adapter、legacy 空对照与质量报告；未进入 Review/strict gate，未读取 PR diff、新增测试或其它 Oracle。
- Candidate result: Django/Celery/Temporal/Supabase 分别生成 7/11/8/11 条 Bundle、Testpoint、主追溯和 Adapter，合计 37；四份主追溯均 invalid=0、false traceability rate=0。
- Finding: 初次质量评分把 Django 的迁移前后记录逐项比较、Temporal 的重试前后最终状态比较误报为 abstract oracle；两条均有前置记录基线和明确比较对象，属于评分器误报而非用例缺陷。
- Repair 1: 通用评分规则增加显式基线比较识别，覆盖迁移前、重试前、认证前、首次、原始和基线值；保留无基线“一致”抽象表述的告警。新增回归测试后四份 weak/generalized/duplicate/semantic mismatch 均为0。
- Outputs: 37 条 Bundle、37 条 Testpoint、34 条开发自测、37 条 Coverage-First Traceability、37 条兼容 Adapter；质量报告指纹均绑定当前 Structured PRD、Coverage、testcase 与主追溯。
- Validation: Bundle、Testpoints strict、Traceability primary+adapter Validator 四项全部通过；四个既有 run 均以 `resume --stop-at traceability` 成功暂停，Traceability attempt=1、Review/strict gate pending；run audit 4/4 通过。
- Baseline: 全量质量基线 5/5 通过，137 项单元测试通过。
- Next: 冻结四份盲测资产及哈希后解封固定 PR head Oracle，仅通过 Review/Design Feedback 反馈发现，不直接修改正式 testcase。
## 2026-09-21 - OSS-BLIND-R3 Oracle Review

- Scope: 在解封 Oracle 前冻结四个工作项从 requirement summary 到 Coverage-First Traceability 的 8 类资产；随后只检查四个公开 PR 的固定 head、changed-files patch 与已有测试。未修改 Coverage、Gate、Acceptance、Case Plan 或正式 testcase，未进入 strict gate。
- Results: Django 6/6 Oracle assertions 命中，coverage 1.0；Celery 8 covered + 1 partial，coverage 0.9444；Temporal 6 covered + 1 partial + 3 missing，coverage 0.65；Supabase 4 covered + 5 partial + 2 missing，coverage 0.5909。37 条 testcase 全部为 direct match 或 requirement regression，相关率 1.0。
- Feedback: 共记录 9 条 open design feedback：Celery 1 条同步载荷契约；Temporal 4 条响应字段、冲突策略、动态开关、错误传播；Supabase 4 条 returnTo、失败反馈、直接访问目标待确认、异步交互。Django 无新增设计缺口。所有反馈目标均为 testability gate、acceptance examples 或 case plan。
- Evidence: 四份 `blind_asset_freeze.json` 哈希复验一致；详细报告为各工作项 `reviews/code_change_risk_report.md` 与聚合 `reports/round_3_oracle_review.md`。四个上游仓库未 checkout，L2 测试未执行。
- Validation: 四份 design feedback validator、四份 oracle delta scorer、冻结哈希检查均通过；四个既有 run 以 `resume --stop-at review` 成功暂停，Review succeeded、strict pending；run audit 4/4、质量基线 5/5（137 项单测）通过。
- Next: 下一阶段从设计层处理已确认反馈；Supabase CP-010 的返回目标必须先确认，不得按当前实现直接覆盖用例。

## 2026-09-21 - OSS-BLIND-R3 Oracle Feedback Triage

- Scope: 复核四份已批准 requirement summary，对 9 条 Oracle 反馈做来源分流；仅更新 design feedback 分类/状态与聚合分流报告，未修改 Gate、Acceptance、Case Plan、testcase 或 traceability。
- Result: Celery 载荷契约和 Temporal 公共响应字段共 2 条进入正式设计补强候选；Temporal 3 条与 Supabase 3 条实现独有行为保持 oracle-only risk/audit；Supabase 功能关闭跳转确认是实现与批准需求不一致，保留 CP-010。
- Correction: 上一阶段把 Supabase 返回目标标为 needs_confirmation；复核批准摘要后更正为 implementation_gap，不再要求用户在既有明确需求上二次选择。
- Validation: 四份 design feedback validator 通过，四份冻结清单 SHA-256 复验一致，质量基线 5/5（137 项单测）通过。
- Next: 从设计层应用已接受反馈并重生成；正式主链只吸收 2 条需求支持的补强，其余保持 risk/audit 或实现问题。

## 2026-09-22 - Oracle Scope Scoring

- Scope: 修复 Oracle 单一覆盖率混合批准需求、实现细节和风险路径的问题；未修改业务代码、Gate、Acceptance、Case Plan、testcase 或冻结资产。
- Implementation: `score_oracle_delta.py` 支持可选 `oracle_scope=requirement/implementation/risk`，旧输入缺省 requirement；输出保留总体兼容分并新增三类 assertion 数量、disposition 分布和独立覆盖率。
- Blind validation: 两批 7 份样本全部复算。第一批 Appsmith/Chatwoot/Saleor requirement 与 implementation 均为 1.0；Django requirement=1.0，Celery requirement=0.9444，Temporal requirement/implementation/risk=1.0/0.25/0.0，Supabase requirement/implementation=1.0/0.3571；7 份 testcase relevance 均为 1.0。
- Correction: Temporal 额外响应字段未进入批准摘要，DF-001 从正式 case gap 收敛为 oracle-only risk；当前 9 条反馈应按 1 条正式设计补强、7 条 oracle-only 风险、1 条实现差异处理。
- Validation: Oracle scorer 聚焦单测 5/5、7 份 CLI 复算、design feedback validator、冻结资产哈希检查、质量基线 5/5（139 项单测）通过。
- Next: 修复 Harness Review checkpoint 的空校验，接入 design feedback、Oracle delta 和冻结哈希检查，并用四份 R3 run 验证。

## 2026-09-22 - Harness Review Checkpoint Validation

- Scope: 修复 Review 阶段无命令、只看文件存在的问题；未修改业务代码、正式 testcase、Case Plan、Gate 或冻结资产，未进入 Strict Gate。
- Implementation: Review StageSpec 改为 validation，始终运行 design feedback validator；新增只读 `validate_oracle_review.py` 校验 Oracle 三件套、冻结路径/hash、manifest 身份与 score 重算一致性；Review fingerprint 纳入全部相关输入。
- Compatibility: 非盲测工作项只执行 design feedback validator；历史反馈回灌样本在 requirement summary 未漂移且所有 feedback=applied 时允许保留原始 freeze，并标记 post-feedback regeneration。
- Blind validation: Django/Celery/Temporal/Supabase 四个既有 run 均自动重跑 Review，attempt=2、commands=2、exit=0，Review succeeded、Strict pending；run audit 4/4 通过。
- Negative tests: 未应用反馈时冻结资产漂移失败、过期 Oracle score 失败、Oracle 文件变化触发 fingerprint 变化；历史 Appsmith 回灌样本兼容通过。
- Validation: 聚焦测试 28/28，质量基线 5/5（144 项单测）通过。
- Next: 实现受限 design feedback apply 流程，并用 Celery 的 requirement gap 从设计层补强与重生成。

## 2026-09-22 - Design Feedback Application And Celery Regeneration

- Scope: 本阶段新增可审计的设计反馈回灌凭证，并仅处理 Celery DF-001；未修改任何业务代码，也未手工编辑正式 testcase。
- Finding: 首次从已更新 Case Plan 重生成后，正式用例仍使用 Acceptance Example 的旧 Then，证明 `case_plan_direct` 没有把 Case Plan assertion 当作最终预期真源。
- Repair: 新增 `design_feedback_application` schema 与 validator，限制每条 applied feedback 只能修改其声明的设计层并记录 before/after SHA-256；Review fingerprint、Review 命令和统一工作项校验均在凭证存在时纳入该产物。通用生成器改为使用 Acceptance Example 的 Given/When、使用 Case Plan assertion 的 expected。
- Celery: DF-001/DF-002 已将“hello/mingle/双向同步载荷仅包含任务 ID、不传播远端 monotonic 时间戳”依次写入 AE-005/006/008 与 CP-005/006/008，并由生成器重建 11 条正式用例、testpoints、开发自测、bundle、traceability 与质量报告。oldest-first 只保留为 implementation oracle，不进入产品验收主链。
- Result: requirement Oracle coverage 由 0.9444 升至 1.0；implementation coverage=0.5，overall compatibility=0.95，testcase relevance=1.0；主追溯 invalid=0、false traceability rate=0。
- Validation: 聚焦单测 19/19；Celery strict 通过；原 run 完整重放后 Review attempt=4、Strict Gate attempt=2 均 succeeded；全量质量基线 5/5、149 项单测通过。
- Next: 下一阶段评估新 applied feedback 强制 receipt 的兼容迁移策略；历史已 applied 样本不得伪造旧变更哈希。

## 2026-09-22 - Feedback Receipt Lifecycle Enforcement

- Scope: 本阶段只强化 feedback application 生命周期；未修改业务代码、正式 testcase 或 Oracle 结论。
- Policy: `create_work_item.py` 新建 manifest 默认启用 `feedback_application_receipt_required=true`，并登记 `design/feedback_application.json` 产物路径；manifest schema 在策略启用时要求该路径声明。
- Enforcement: Harness Review 与 `validate_work_item.py` 不再按 receipt 是否存在决定是否执行 validator。强制策略下 applied feedback 缺 receipt 必须失败；receipt 存在时继续校验目标层、完整 feedback 集合、合法 SHA-256 与当前 after hash。
- Compatibility: 旧 manifest 未声明策略且存在历史 applied feedback 时返回 `legacy_compatible`。Appsmith、Chatwoot、Saleor 三份历史样本均通过该路径，没有补写或伪造 before hash。
- Validation: 聚焦测试 29/29；Celery receipt verified（2 applications / 4 artifacts）、strict 和 Oracle Review 通过；全量质量基线 5/5、152 项单测通过。
- Next: 增加两阶段 prepare/record 命令，在设计层修改前自动捕获 baseline hash，修改后自动生成并校验 receipt。

## 2026-09-22 - Feedback Application Two-Phase Workflow

- Scope: 本阶段只实现 feedback 回灌 baseline 捕获与 receipt 记录工具；未修改任何工作项设计资产、正式 testcase 或业务代码。
- Prepare: 新命令只接受 accepted feedback，按 target_layer 解析允许路径，冻结当前 SHA-256 到 `.generation/feedback_applications/<DF-ID>.before.json`，并拒绝覆盖已有快照和越界 target。
- Record: 校验项目/工作项/feedback/target layer/fingerprint 未漂移，至少一个已冻结设计产物发生变化后生成或合并 receipt，再把 feedback 状态置为 applied；已有相同 receipt 时可幂等完成状态收口。
- Safety: receipt-first/status-second 确保中断时不会出现 applied 但无凭证的放行窗口；已有其它 applied feedback 缺 receipt 时拒绝写入新状态。
- Validation: 两阶段正常链路、正式 testcase 越界、无变更、feedback 漂移、中断恢复 5 类测试通过；与 receipt/review 联合聚焦测试 18/18；全量质量基线 5/5、157 项单测通过。
- Next: 评估接入受限 Action Runtime，只允许 Agent 通过白名单 prepare/record 动作改变反馈生命周期。

## 2026-09-22 - Feedback Application Restricted Action Runtime

- Scope: 本阶段只增加 Agent 反馈回灌的受限动作入口；未修改业务代码、盲测设计资产、正式 testcase 或 Oracle 结论。
- Contract: 新增 `harness_feedback_action.schema.json`，仅允许 prepare、propose、record 三类动作；arbitrary shell 和其它动作在 schema 层拒绝。
- Isolation: propose 复核 feedback identity/fingerprint/target layer，只能写 prepare 快照冻结的路径，禁止直接修改 feedback 状态、receipt 和正式 testcase。
- Lifecycle: propose 后 feedback 仍为 accepted；只有 record 可复用 receipt-first/status-second 事务迁移到 applied，并保留中断恢复能力。
- Validation: 5 类 Runtime 新测试通过；与两阶段、receipt 和 Harness contract 联合聚焦测试 40/40；全量质量基线 5/5、162 项单测通过；`git diff --check` 通过。
- Next: 为三类 feedback action 增加不可变 action journal、action ID 幂等和 Harness audit 重放。

## 2026-09-22 - Feedback Action Journal And Audit

- Scope: 本阶段只补强 feedback Action 的过程证据、幂等恢复与审计；未修改业务代码、盲测正式资产或 Oracle 结论。
- Journal: 每个 Action ID 在执行前写不可覆盖 intent，成功或确定性失败后写不可覆盖 result；请求 SHA-256 将两者绑定，禁止不同请求复用 ID。
- Recovery: 已完成动作重复调用直接返回原 result；prepare 在 intent 后中断且快照已落盘时可用原 action 恢复。失败动作形成终态 result，修正后必须使用新 ID。
- Audit: 新增独立 `audit-feedback-actions` CLI；Review 与 strict 同步检查配对、hash、成功动作顺序、receipt 和 applied 状态，journal 文件已进入 Review fingerprint。
- Compatibility: 新工作项默认要求 action journal；旧 Celery 等已 applied 样本无历史日志时返回 `legacy_compatible`，不补造记录。
- Validation: 聚焦测试 66/66、Celery strict、全量质量基线 5/5（170 项单测）与 `git diff --check` 均通过。
- Next: 可选增强为 journal 增加 Harness run、actor/provider 身份绑定；当前反馈应用正确性闭环无阻塞。

## 2026-09-22 - Framework Sample Independence

- Scope: 解除质量基线、Golden、Harness 收口入口和 Runtime 单元测试对 PT083/WX-YGJ 业务样本的默认或隐式依赖；未修改业务代码，未删除真实样本或历史盲测证据。
- Implementation: Eval fixture 匿名化为 `CONFIGURATION_RULES / FIXTURE-CONFIG-001`；Runtime 测试使用 `tests/fixtures/runtime_work_item`；收口 CLI 的项目与工作项参数改为必填；隔离生成可从显式外部工作项目录播种验证副本。
- Guard: 新增 `validate_framework_sample_independence.py` 并接入质量基线，扫描框架脚本、测试、Eval 和当前指南，同时拒绝基线或 Eval 命令绑定 `validate_work_item.py`、`validate_project.py` 或 `assets/projects/`。
- Documentation: 当前入口、SOP、架构和收口文档不再把具体业务需求描述为框架正向样例；`assets/projects/` 明确为业务样本与历史产物。
- Validation: 独立性门禁通过；Runtime 聚焦测试 64/64、Eval 测试 7/7、全量质量基线 4/4（170 项单测）通过；Golden baseline 已按匿名 fixture 指纹刷新。

## 2026-09-22 - Feedback Action Execution Identity

- Scope: 只增强 feedback Action journal、Runtime、CLI 与 Harness audit 的执行身份追溯；未修改业务代码、正式 testcase、设计反馈内容或历史 journal。
- Contract: journal 1.1 新增 `execution_context`，记录 Harness `run_id`、`actor`、`provider`；request hash 同时覆盖 action 与执行上下文。
- Enforcement: CLI 从 action payload 外部接收身份；Runtime 校验 run 存在及项目/工作项一致；审计拒绝 intent/result 身份漂移、身份篡改和同一 feedback 跨 run 成功执行，并按 run 汇总反馈动作。
- Compatibility: 新工作项默认要求执行身份；旧 1.0 journal 保持 `legacy_compatible`，不补造历史身份。
- Validation: 聚焦回归 55/55；全量质量基线 4/4，177 项单测通过；Regression/Golden Eval 均为 6/6；`git diff --check` 通过。
- Remaining risk: `actor` / `provider` 仍是调用方提供的可审计声明，只有宿主传入认证 principal/provider 元数据后才能升级为认证身份。

## 2026-09-22 - Harness Review Not-Applicable Disposition

- Scope: 修复无代码工作项无法在不伪造 Review 成功的前提下进入 Harness strict gate 的状态缺口；未修改业务代码、正式 testcase、设计反馈或历史 run。
- Contract: 新增 `harness_review_disposition.schema.json` 和 run-scoped `review_disposition.json`，记录 `not_applicable`、人工声明者、原因及代码评审 scope 哈希。
- Runtime: 新增 `mark-review-not-applicable` CLI；只接受已完成 Traceability、代码目录为空的 validate run，并拒绝 CI 自声明、重复冲突和 scope 漂移。
- Enforcement: N/A 后 Review validators 仍完整执行；通过后 Review 记为 `skipped` 并产生审计事件。新工作项仅凭有效 disposition 才在 strict gate 使用 `--skip-code-reviews`，正常代码评审路径不受影响。
- Audit: run audit 校验凭证、声明事件、`stage_not_applicable` 事件、Review 尝试结果与 Traceability 前置状态。
- Validation: 聚焦回归 28/28、关联回归 32/32；全量质量基线 4/4，182 项单测通过；Regression/Golden Eval 均 6/6；`git diff --check` 通过。
- Remaining risk: 既有历史 run 需要实际责任人显式声明 N/A 后才能恢复到 strict；框架不会自动补造该事实。

## 2026-09-22 - OSS-BLIND-R4 Final-Round Requirement Intake

- Scope: 启动发布前最终公开盲测轮，仅执行需求接入与归一化；未修改业务代码，未进入 Reasoning、Structured PRD、测试设计、用例生成或 Oracle Review。
- Samples: 新建 `OSS-BLIND-R4` 及四个 M 档工作项：Grafana #133083、Home Assistant #182800、Rails #58429、Kubernetes #141831；均未与前两轮 7 个样本重复。
- Blind boundary: 只消费 PR 作者公开描述与合并元数据，逐项冻结 `inputs/public_source_snapshot.md`；代码 diff、commit、Review 评论、实现路径和测试断言均排除在生成输入之外。
- Outputs: 四个工作项均完成 `inputs/requirement_summary.md` 与 `inputs/source_manifest.json`，分别覆盖显式 Serializer、重复 ID3、BroadcastLogger tagged 语义、空 DeviceTaintRule selector 警告四类行为。
- Validation: 四份 Requirement Sources strict 通过；全仓质量基线 4/4、182 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Next: 等待人工批准四份需求摘要；批准后单独执行 Reasoning Analysis 阶段。

## 2026-09-22 - OSS-BLIND-R4 Reasoning Analysis

- Scope: 记录四份需求摘要的人工批准并执行 Reasoning Analysis；未读取代码 diff、commit、测试实现或 Review Oracle，未生成 Structured PRD 之后的正式资产。
- Approval: 四份 `inputs/requirement_approval.json` 分别绑定 `RUN-R4-<WORK_ITEM_ID>`、当前摘要/来源指纹与用户批准事实。
- Finding: 生成器会把摘要第 7 节的说明性元数据当成显式规则和 Coverage 候选，可能把“PR 未声明新增项”等非行为信息带入后续主覆盖。
- Repair: `generate_reasoning_pack.py` 新增说明性前缀过滤，仅排除关键数据/契约/API/资源字段清单和未声明项，保留真实输出契约；新增单元回归测试后重生成四份产物，共移除 8 条伪规则。
- Outputs: 四份 Reasoning Pack 共 53 条显式规则、16 条风险、9 条边界场景、16 条待确认项；未发现 PT083 或前两轮样本语义污染。
- Validation: 四份来源语义 strict 校验、四个 Harness run audit 均通过；全仓质量基线 4/4、183 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Boundary note: Grafana run 首次恢复时未显式传 `--stop-at reasoning`，按 Harness 既定语义继续只读校验至 Testability Gate 并失败；未写下游资产，随后已显式恢复为 reasoning checkpoint。后续阶段必须每次传入目标 `--stop-at`。
- Next: 下一阶段仅生成和校验四份 Structured PRD。

## 2026-09-22 - OSS-BLIND-R4 Structured PRD

- Scope: 只执行四份 Structured PRD authoring、编译与阶段校验；未读取实现 Oracle，未生成 Coverage、测试设计或正式 testcase。
- Outputs: Grafana/Home Assistant/Rails/Kubernetes 分别形成 6/6/7/7 条正式规则，共 4 个系统观察面、8 个 feature 和 6 条 flow。
- Semantics: 显式 Serializer、ID3 元数据保真、BroadcastLogger block/非 block 语义、DeviceTaintRule 非阻塞 Warning 均拆成可独立判断规则；未决错误契约、格式兼容和并发边界未被脑补为验收要求。
- Traceability: 所有 flow step 均映射到存在的 module/feature 并引用正式 rule ID；Markdown 为 authoring 真源，JSON 由仓库编译器生成。
- Validation: 四份 Structured PRD validator、四个 Harness checkpoint、四个 run audit 均通过；未发现 PT083 或历史盲测样本语义污染。全仓质量基线 4/4、183 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Next: 下一阶段仅生成并校验 Coverage Matrix。

## 2026-09-22 - OSS-BLIND-R4 Coverage Planning

- Scope: 只执行四份 Coverage Matrix 的生成、语义抽查和 Harness checkpoint；未进入 Testability Gate、Acceptance Examples、Case Plan 或 testcase，也未读取代码 Oracle。
- Finding: 多 feature Structured PRD 的顶层规则没有按 `applies_to` 绑定 feature 上下文；补上映射后，相同 `applies_to` 又被当作 Coverage 标题参与去重，导致不同正式规则被合并。
- Repair: Coverage 生成器按 `applies_to -> feature_name` 映射页面/板块/模块/功能点，并始终以具体规则文本或 atomic assertion 作为 Coverage 标题；新增“多 feature 上下文映射”和“同 feature 多规则不误合并”回归测试。
- Outputs: 四份矩阵共 68 项；Grafana 14 main/5 audit、Home Assistant 6/4、Rails 10/6、Kubernetes 13/10。43 项主覆盖上下文完整且唯一，25 项风险/边界保持 audit-only，0 项 drop。
- Validation: 四份 Coverage validator、四个 Harness checkpoint、四个 run audit 通过；无 PT083 或历史样本语义污染。全仓质量基线 4/4、185 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Next: 下一阶段只生成并校验 Testability Gate。

## 2026-09-22 - OSS-BLIND-R4 Testability Gate

- Scope: 只执行四份 Testability Gate 分类、校验和 Harness checkpoint；未生成 Acceptance Examples、Case Plan 或 testcase，未读取代码 Oracle。
- Decisions: 四份 Gate 共 42 条；26 条已确认 Structured PRD 规则均为可测并进入 `generate_acceptance_example`，16 条 Reasoning 风险全部保持 `risk_note_only`。
- Isolation: 9 条边界场景继续由 audit Coverage 承接，不在 Gate 中重复升级；没有 technical background、soft prompt、待确认项或风险进入正式验收主链。
- Finding and repair: 原 Validator 只检查 `source_rule_id` 是否覆盖，无法发现相同 ID 下 `source_text` 漂移；现已强制 Gate 正文与 Structured PRD 对应规则一致，并新增正反向回归测试。
- Validation: 四份 Gate validator、四个 Harness checkpoint、四个 run audit 通过；全仓质量基线 4/4、187 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Next: 下一阶段按 43 项 main Coverage 生成原子 Acceptance Examples，并关联 26 条允许 Gate。

## 2026-09-22 - OSS-BLIND-R4 Acceptance Examples

- Scope: 只执行四份 Acceptance Examples 编写、校验和 Harness checkpoint；未进入 Case Plan、正式 testcase 或代码 Oracle Review。
- Outputs: Grafana/Home Assistant/Rails/Kubernetes 分别生成 14/6/10/13 条原子 Given/When/Then，共 43 条，覆盖序列化路径、MP3 标签保真、BroadcastLogger 标签语义和 DeviceTaintRule 非阻塞 Warning。
- Traceability: 每条示例同时绑定 Gate、Structured Rule 和一项 main Coverage；43 项 main Coverage 全覆盖、无重复，16 条 risk-note Gate 与 25 项 audit-only Coverage 均未进入正式验收示例。
- Oracle: Kubernetes Warning 使用 `soft_display`，非阻塞 create/update、持久化和 warnings-as-errors 分离断言；其余后端行为按可观察调用、状态或数据结果判断，未把风险提示升级成强契约。
- Validation: 四份 Acceptance validator、四个 Harness `acceptance_examples` checkpoint、四个 run audit 均通过；全仓质量基线 4/4、187 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Next: 下一阶段仅生成并校验四份 Case Plan，显式停在正式 testcase 之前。

## 2026-09-22 - OSS-BLIND-R4 Case Plan

- Scope: 只执行四份 Case Plan 设计、编号映射登记、校验和 Harness checkpoint；未生成正式 testcase，未进入 Traceability、Review 或代码 Oracle。
- Outputs: Grafana/Home Assistant/Rails/Kubernetes 分别生成 14/6/10/13 条 `case_plan_direct` 计划，共 43 条；Acceptance Example、Case Plan、main Coverage 和稳定 testcase ID 均为 43/43 一一对应。
- Semantics: 后端任务、数据持久化、跨层联动、字段契约分别进入对应 case type；Kubernetes 的 8 条 Warning 展示保持 `prompt_display`，未升级为 `save_block`，非阻塞 create/update、持久化和客户端退出码单独承接。
- Numbering: 在公共编号规则中登记 APIStore、TTS 音频、BroadcastLogger、DeviceTaintRule 四个页面编码及其板块编码，后续正式 testcase 不使用临时或未登记编号。
- Validation: 四份 Case Plan validator、四个 Harness `case_plan` checkpoint、四个 run audit 均通过；全仓质量基线 4/4、187 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Next: 下一阶段按 Case Plan 直出正式 testcase 与规定派生视图，并显式停在 `testcases`。

## 2026-09-22 - OSS-BLIND-R4 Testcase Generation

- Scope: 只执行四份 `case_plan_direct` 正式用例生成及同轮 testcase 派生产物刷新；未进入 Traceability、Review、Strict Gate 或代码 Oracle。
- Outputs: Grafana/Home Assistant/Rails/Kubernetes 分别生成 14/6/10/13 条正式 testcase，共 43 条；同步生成兼容镜像、testpoints、开发自测、field/grouped audit、duplicate report 与 testcase bundle，未追溯候选为 0。
- Design repair: 首轮 lint 发现 Grafana 缺流程型计划，已将“同一 Go 类型不同 GVK 持久化与读回”调整为 P0 linkage，并为四个样本的 linkage 断言补充可观察终态；Home Assistant 的模糊“正常/成功”预期改成解码结果与样本数量断言；Kubernetes 校验错误用例编号修正为 `AB`。
- Generator repair: `case_plan_direct` 标签生成新增 `API/SERVER` 终端兜底，并移除仅凭“列表”判为 UI 的规则，防止后端 list/日志/音频/持久化用例误标 `AI-UI用例`；新增 2 项回归测试，R4 后端样本当前无错误 UI 标签。
- Validation: 四份 testcase lint、元素标注、分组、testpoints、Case Plan、bundle validator 通过；四个 Harness `testcases` checkpoint 与 run audit 通过；全仓质量基线 4/4、189 项单元测试通过，Regression/Golden 均为 6/6。
- Next: 下一阶段生成 coverage-first traceability 与兼容 adapter，并显式停在 `traceability`。

## 2026-09-22 - OSS-BLIND-R4 Traceability

- Scope: 只生成和校验四份 coverage-first traceability 与兼容 adapter；未读取实现 diff，未执行 Oracle Review、反馈回灌或 Strict Gate。
- Outputs: Grafana/Home Assistant/Rails/Kubernetes 分别生成 14/6/10/13 条追溯记录，共 43 条；Coverage 到 testcase 映射与 Case Plan 完全一致，`false_traceability_rate=0.0`、`invalid_record_count=0`。
- Finding: 追溯生成器只接受 `ER-数字` 形式的显式规则 ID，`GRA-R001`、`HA-R001` 等有效业务规则会退化成模块/功能/coverage-type 合成标识，同一规则的原子覆盖因此不能可靠绑定真实规则身份。
- Repair: `infer_rule_id` 改为优先解析 `structured_refs` 中的任意合法 `explicit_rules.<ID>`，其次接受无空格、含数字的 ID 型 `rule_name`，最后才使用上下文 fallback；新增 2 项单元测试验证自定义规则前缀和旧式描述型 fallback。
- Validation: 四份 Traceability validator、四个 Harness `traceability` checkpoint、四个 run audit 通过；全仓质量基线 4/4、191 项单元测试通过，Regression/Golden 均为 6/6；`git diff --check` 通过。
- Next: 冻结四份盲测资产后读取公开 PR 实现作为 Oracle，执行差异评分与 Review，并保持反馈只回到 design 层。

## 2026-09-22 - OSS-BLIND-R4 Oracle Review

- Scope: 在读取任何实现 Oracle 前冻结四份工作项的 Requirement、Structured PRD、Coverage、Gate、Acceptance、Case Plan、正式 testcase 与 Traceability 共 8 类资产；本阶段只做后置静态映证，未修改设计层或正式 testcase。
- Oracle: 固定 Grafana #133083 `9aeaf1e7`、Home Assistant #182800 `e1734829`、Rails #58429 `edd687c7`、Kubernetes #141831 `42d2a3f1`，审阅公开 PR diff、新增测试与公开验证说明；未 checkout 上游仓库，未执行 L2 上游测试。
- Results: 四份分别形成 8/6/6/8 个 Oracle assertion；coverage 为 0.375/1.0/0.8333/0.875，需求层 coverage 为 0.8333/1.0/1.0/1.0。43 条正式 testcase 全部为 direct match 或 requirement regression，相关率均为 1.0，无样本污染。
- Feedback: 形成 6 条 accepted design feedback：Grafana 4 条（非 watch context、错误与 JSON 异常、版本策略、并发安全）、Rails 1 条（零 tagging logger）、Kubernetes 1 条（空字符串指针语义）；Home Assistant 无新增缺口。反馈未标记 applied，未直接覆盖 testcase。
- Validation: 四份 design feedback validator 与 Oracle Review validator 通过，冻结哈希 4/4 完整；四个 Harness run 均以 `resume --stop-at review` 成功暂停，Review succeeded、Strict Gate pending；run audit 4/4、质量基线 4/4（191 项单测）、Regression/Golden 6/6 与 `git diff --check` 通过。
- Next: 下一阶段只做 6 条 feedback 的来源分流与处置设计，不直接回灌或重生成。

## 2026-09-22 - OSS-BLIND-R4 Feedback Triage

- Scope: 仅对 Oracle Review 的 6 条 design feedback 做来源分流、目标层复核和后续处置设计；未修改 Gate、Acceptance、Case Plan、正式 testcase 或业务代码。
- Triage: Grafana DF-002 为已批准需求在正式设计链中的漏传，应从 Testability Gate 重新进入 Acceptance/Case Plan；Grafana DF-001/003/004 与 Rails DF-001 为 oracle-only 实现风险，只进入 Gate risk-note；Kubernetes DF-001 保持 needs-confirmation，不生成正式用例。
- Routing repair: 将 Grafana DF-002 的 target layer 从 `case_plan` 调整为 `testability_gate`，避免在没有 Gate/Acceptance 来源的情况下直接扩写 Case Plan。
- Outputs: 新增 `assets/projects/OSS-BLIND-R4/reports/round_4_feedback_triage.md`，记录 1/4/1 分流、逐项理由、Action 顺序和验收边界。
- Validation: 四份 design feedback validator、四份 Oracle Review validator、Harness run audit 4/4、质量基线 4/4（191 项单测）、Regression/Golden 6/6 与 `git diff --check` 通过；Grafana Review 因 feedback 路由变化完成 attempt=2。
- Next: 下一阶段仅通过 Harness 白名单 feedback Action 回灌 6 条 Testability Gate 反馈并生成 receipt/journal，不跨入下游重生成。

## 2026-09-22 - OSS-BLIND-R4 Feedback Application

- Scope: 通过 Harness 白名单 feedback Action 回灌 6 条 Testability Gate 反馈；未修改业务代码，未生成 Acceptance、Case Plan 或正式 testcase。
- Applied: Grafana 4 条、Rails 1 条、Kubernetes 1 条均为 `applied`；Home Assistant 无反馈且保持不变。Grafana DF-002 进入 `generate_acceptance_example`，4 条实现风险保持 `risk_note_only`，Kubernetes 歧义保持 `needs_confirmation`。
- Audit: Grafana/Rails/Kubernetes 分别产生 12/3/3 个成功 Action，均具备 intent/result journal、run/actor/provider 身份与 before/after SHA-256；无失败动作或跨 run 混用。
- Framework repair: `validate_feedback_application.py` 改为验证同一路径的顺序哈希链，解决同一 Gate 多次合法回灌被历史 receipt 误报的问题；新增链成功与断链失败测试。
- Outputs: 更新三份 `acceptance/testability_gate.{json,md}`、三份 `design/feedback_application.json`、对应 Action journal，并新增 `reports/round_4_feedback_application.md`。
- Validation: Gate、feedback application、Action journal/audit、design feedback、Oracle Review 全部通过；聚焦回归 34/34；质量基线 4/4，193 项单测通过，Regression/Golden 均 6/6。
- Next: 仅重建 Grafana DF-002 的 Acceptance/Case Plan/testcase 与派生产物，随后刷新 Rails/Kubernetes 的 Review/Strict 状态；risk-only 与 needs-confirmation 不进入正式用例。

## 2026-09-22 - OSS-BLIND-R4 Downstream Regeneration

- Scope: 将已批准的 Grafana DF-002 从 `ER-002` / `TG-012` 顺序下传到 Coverage、Acceptance、Case Plan、正式 testcase 与派生产物；未修改业务代码。
- Outputs: 新增 3 个原子 Coverage、`AE-015`～`AE-017`、`CP-015`～`CP-017` 和 3 条 context 传播 API testcase；Grafana 用例由 14 增至 17，R4 总数由 43 增至 46。
- Isolation: Grafana 3 条实现风险、Rails 1 条实现风险和 Kubernetes 1 条待确认歧义均未生成正式 testcase；其他三份样本 testcase 不变。
- Metrics: Grafana requirement Oracle coverage 从 `0.8333` 提升到 `1.0`，testcase relevance 保持 `1.0`；17 条 coverage-first traceability 全部有效，失真率为 0。
- Refresh: 刷新 Grafana testcase bundle、testpoints、开发自测、审计、traceability、quality report 和 Oracle score；刷新其余三份缺少当前源指纹的 quality report；项目视图为 4 个 ready 工作项、46 条 testcase、0 个过期质量报告。
- Validation: 四个 Harness Review 与 run audit 通过；四份资产级 strict 使用显式 `--skip-code-reviews` 均通过。
- Blocker: 四份 code review scope 都没有本地代码目录且 policy 要求人工作出 run-scoped N/A 声明。未获用户明确授权前不代填声明，Harness Strict Gate 保持 pending。

## 2026-09-22 - OSS-BLIND-R4 Strict Closeout

- Approval: 用户明确批准四份最终轮 run 的本地代码评审 `not_applicable` 声明；每份凭证均绑定原 run、声明者 `ycp` 和当前 code review scope 哈希。
- Lifecycle repair: 修复 Review 已成功但 Strict 尚未执行时无法补充 disposition 的死锁；声明后只重开 Review，由 Harness 重新执行确定性 validator，再写入 `skipped/not_applicable` 终态。
- Validation: 新增“成功 Review 后声明并重跑”的单元测试；四个 run 的 Review 均重新执行且 Strict Gate succeeded，run audit 4/4 通过。
- Project: `OSS-BLIND-R4` 项目 strict 通过，4 个工作项均 ready，共 46 条 testcase、3 个开放风险、0 个过期质量报告。
- Next: 生成最终轮及累计 11 份公开 PR 盲测的发布前收口评估，不再修改测试资产语义。

## 2026-09-22 - Release Readiness Closeout

- Scope: 完成三批 11 份公开 PR 盲测的发布前收口与仓库清理；未修改任何业务代码或测试资产语义。
- Completion: 补齐 Django、Temporal、Supabase 三个 R3 run 的 Strict Gate，四个 R3 run audit 全部通过，并刷新 R3 项目视图为 4/4 ready、37 条 testcase、0 个过期质量报告。
- Packaging repair: `.gitignore` 不再整体忽略 `.generation/`，保留新工作项 strict 所需的 feedback application baseline、不可变 Action journal、`run_state.json` 与人工 disposition；继续忽略 events、诊断、hook、阶段日志、当前 run 指针、根级评测缓存和临时 Action 输入。
- Documentation repair: `P1_2_RESPONSIBILITY_VALIDATION.md` 的正向命令改用已有且校验通过的匿名 `LINKAGE_ONLY` fixture，移除已删除 PT083 expected fixture 的失效引用；R4 N/A 样本的直接 strict 命令明确使用 `--skip-code-reviews`。
- Release assessment: 三个项目共 11/11 ready、108 条正式 testcase；R3 的 8 条实现/风险观察与 R4 的 3 个软质量风险保留为非阻塞项。详细结论见 `assets/projects/OSS-BLIND-R4/reports/final_release_readiness.md`。
- Validation: 匿名责任图文档示例改用可通过 validator 的 `LINKAGE_ONLY` fixture；全量质量基线 4/4（194 项单测）、Regression/Golden 6/6、三项目 strict、R4 四工作项 strict、11 个 Harness run audit 和模拟发布包 R4 strict 4/4 全部通过。
