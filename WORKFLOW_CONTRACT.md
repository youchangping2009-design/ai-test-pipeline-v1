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
- 新工作项默认设置 `pipeline_policy.requirement_approval_required=true`；Requirement Sources 机器校验成功后必须停在 `waiting_approval`，由人工生成 `inputs/requirement_approval.json` 批准凭证后才能进入 evidence
- 凭证必须绑定 requirement summary、source manifest、原始输入聚合 fingerprint、需求版本和审批 run；任一绑定内容漂移立即使旧批准失效
- 旧 manifest 缺少 `requirement_approval_required` 时保持兼容；显式设置为 `true` 时，strict 必须要求有效且当前绑定匹配的 approved receipt

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
- Case Plan 阶段不得读取未来 `testcases_main.md` 作为前置输入；Testcases 阶段不得读取尚未刷新的 Bundle 作为前置输入；Bundle 必须在 Traceability 前刷新并校验
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
- 新工作项默认启用 `pipeline_policy.feedback_application_receipt_required=true`。当 feedback 标记为 `applied` 时，`design/feedback_application.json` 必须记录反馈 ID、目标设计层以及修改文件的前后 SHA-256；旧 manifest 缺少该 policy 时保持 legacy compatibility，不补造历史哈希
- 标准回灌顺序为 `manage_feedback_application.py prepare` -> 修改目标设计层 -> `manage_feedback_application.py record`。prepare 只接受 `accepted` feedback 并拒绝覆盖既有 baseline；record 要求反馈内容与目标层未漂移、至少一个已冻结产物发生变化，并以“先写 receipt、后置 applied”的顺序支持中断后幂等恢复
- Agent 执行回灌时不得直接写工作项文件，必须通过 `run_work_item_pipeline.py feedback-action` 提交符合 `harness_feedback_action.schema.json` 的动作。白名单仅包含 `prepare_feedback_application`、`propose_feedback_design_artifacts`、`record_feedback_application`；propose 只能写 prepare 快照中的路径，record 是唯一状态迁移入口
- `feedback-action` 的 `run_id`、`actor` 与 `provider` 必须由受信调用侧注入，不能由模型 Action payload 自报。Runtime 校验 run 存在且项目/工作项身份匹配，再将执行上下文与 Action 一起纳入请求 SHA-256
- 新工作项默认启用 `pipeline_policy.feedback_action_journal_required=true` 与 `feedback_action_execution_identity_required=true`。Runtime 在动作执行前创建不可覆盖的 intent，成功或确定性失败后创建不可覆盖的 result；相同 action ID/请求/执行上下文可幂等读取结果，不同绑定不得复用 ID。Review、strict 与 Harness run audit 重放校验 journal；旧 manifest 和 1.0 journal 不补造历史身份

### Traceability

- `traceability/coverage_first_traceability.json` 是主真源
- `traceability/traceability_adapter.json` 是兼容层，可按需再生
- `traceability/traceability_matrix.json` 仅保留 legacy 对照角色，minimal retention 下可清理

### Review / Export

- `reviews/quality_report.json` 是质量报告真源
- `reviews/review_record.md` 是阅读友好型评审记录
- `reviews/oracle_delta_input.json` 记录冻结测试资产与后置代码/测试 oracle 的人工映射；assertion 使用可选 `oracle_scope=requirement/implementation/risk` 区分批准需求、实现行为和风险路径，旧输入缺省为 `requirement`。`reviews/oracle_delta_score.json` 同时保留总体兼容分和三类分层覆盖率。两者只用于生成后评测，不得反向污染盲测输入。
- Harness Review 阶段必须执行 design feedback 与 feedback application validator；启用 receipt policy 的工作项存在 `applied` feedback 时，缺失或不完整回灌凭证必须失败。旧工作项只允许显式识别为 legacy compatible，不得生成伪造凭证。当 freeze/input/score 任一 Oracle 资产出现时，三者必须齐全，并以只读方式校验冻结哈希与当前评分重算结果。反馈回灌后允许设计/用例资产相对原始冻结基线变化，但 requirement summary 不得漂移，且所有反馈必须已标记 applied。
- 新工作项默认启用 `review_disposition_required=true`。无代码映证必须由人工为具体 validate run 声明 `not_applicable`、执行者和原因，凭证绑定当前 `code_review_scope.json`。N/A 不绕过 Review validator；全部通过后 Review stage 记录为 `skipped`，strict gate 才允许 `--skip-code-reviews`。scope 漂移、存在代码目录、CI 自声明或缺失凭证均不得复用该路径。
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
- `.generation/runs`（仅终结且无 pending approval/未恢复事务时）
- `.generation/current_run.json`
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

### 6.1 Harness 运行契约

Harness 运行层只管理阶段顺序、checkpoint、事件、诊断和停止原因，不改变业务产物真源。

首版确定性 Orchestrator 的正式边界：

- `scripts/run_work_item_pipeline.py` 支持 `start / status / resume / cancel`
- Run、Stage、Event、Diagnostic、Model Action、Approval 使用 `schemas/harness_*.schema.json`
- `.generation/runs/<RUN_ID>/run_state.json` 是过程状态，不是工作项业务真源
- 阶段命令必须来自 `scripts/harness/stage_registry.py` 白名单，不允许透传任意 shell
- 首版只执行只读 Validator 和 artifact checkpoint，不调用模型、不执行生成器
- 恢复时仅复用输入指纹未变化的成功 checkpoint；指纹变化会使该阶段及下游失效
- 同一业务执行应复用一个 run 并通过 `resume` 推进 checkpoint，不为每个阶段创建新 run
- Requirement approval required 时，requirement intake checkpoint 使用正式 canonical approval binding（run、summary、source manifest、raw inputs、requirement version），不把 manifest 的运行期/派生字段纳入审批有效性
- `resume` 不得绕过 pending/rejected receipt；canonical binding 漂移必须使 requirement intake 及下游 checkpoint 失效并重新请求人工审批，旧完整-manifest checkpoint 可在 approved receipt 仍匹配时仅规范化指纹
- `approve-requirement / reject-requirement` 必须显式接收 reviewer 和 note；重复同一决议幂等，冲突决议失败；`recover-requirement-approval` 只补全已持久化 receipt 对应的 event/state，不伪造 reviewer
- CI 只能验证 approval receipt，不能调用人工批准入口；minimal cleanup 和受控生成不得删除、发布或生成 approval receipt
- 最终结论仍以 `validate_work_item.py` 的现有门禁为准，Harness 不得降低或绕过 strict
- 运行日志、事件与诊断可按 minimal retention 清理，不得反写正式产物

Harness Diagnostic 必须满足：

- `stage_id` 表示应负责修复的责任阶段，`observed_stage_id` 表示实际观察到失败的阶段
- 每条失败至少提供 `code / artifact_path / severity / message / repair_hint / source_validator`
- 聚合门禁输出允许路由到上游责任阶段，但不得改变原 Validator 的退出码和通过/失败结论
- 无法分类的错误必须生成 `HARNESS_VALIDATOR_FAILED`，不得因解析失败而丢失原失败
- 同一阶段的多次失败按 `diagnostics/<STAGE_ID>/attempt-<N>.json` 分开保存
- 诊断摘要必须清理常见 API Key 与 Authorization 信息；完整日志仍不得主动写入凭证

### 6.2 受限 Agent Loop 契约

当前 Agent Loop 只允许作用于 `testcases/case_plan.json`：

- 模型每个 turn 只能返回一个符合 `harness_model_action.schema.json` 的 Action
- 允许动作仅为读取白名单产物、搜索 `inputs/`、写 Case Plan staging、运行阶段校验、请求提交或人工审批
- `propose_artifacts` 只能写 `.generation/runs/<RUN_ID>/staging/testcases/case_plan.json`
- staging 校验必须使用现有 Case Plan Validator，并按 S/M/L 复用 examples 与 responsibility 强制策略
- staging 阶段不得携带旧 `testcases_main.md` 反向锁死新的 Case Plan
- 每个 run 最多 8 个模型 turn；初次校验失败后最多 2 轮 repair
- `commit_stage` 只能创建 pending approval；正式提交必须通过独立 `approve-case-plan`
- 审批必须绑定 approval ID、candidate hash、正式目标 hash 和上游 fingerprint
- 提交前任一 hash 漂移必须拒绝；提交成功后必须标记 testcase、traceability、review 和 strict gate 失效
- 正式 Case Plan 替换必须先写 commit transaction；目标替换成功后先持久化 `committed` journal，再完成 approval/run metadata
- `prepared/committing` 恢复必须回滚到原目标和 pending approval；`committed` 恢复必须校验目标 hash 后幂等完成 metadata
- 未恢复 transaction 存在时不得 reject approval、清理 run 或开始新的正式提交
- Case Plan Agent 完成只表示该阶段完成，不能替代工作项 strict 验收

模型 command adapter 是人工选择的可信运行时边界。Harness 必须使用 argv 直接执行、禁止 `shell=True`；该约束不等价于操作系统沙箱。

### 6.3 Harness 治理与可观测性契约

- Agent run 必须记录模型调用次数和耗时、动作计数、Validator 尝试、诊断数与终态。
- adapter 报告 usage 时记录 input/output/total token、cost、provider 和 model；不得猜测缺失用量。
- wall time 与模型调用预算始终可执行；配置 token/cost 预算或 `require_usage` 后，usage 缺失必须停止并请求审批。
- 超预算后的 Action 不得分发，不得借 repair 或审批绕过预算继续模型调用。
- `telemetry.json` 与 `run_summary.json` 是过程审计产物，不是业务真源。
- pending approval 必须支持独立 approve/reject；reject 不得提交 staging，run 进入 cancelled。
- `audit-run` 必须校验 run state、连续 Event sequence、Action、Approval、Diagnostic、Telemetry 和终态一致性。
- 审计失败只报告不一致，不修改 Validator 结论、不修复业务产物。

### 6.4 Harness Hook 契约

- Hook 事件仅为 `pre_stage / post_stage / fail_stage / approval_requested / approval_resolved / repair_requested`。
- Hook 配置只能引用 `scripts/hooks/*.py`；Dispatcher 使用 Python argv 直接执行，禁止 `shell=True`、任意可执行文件和命令参数透传。
- Hook 只通过 stdin 接收结构化事件，运行环境不继承 API Key、Authorization 等业务凭证。
- 单个 Hook 必须配置 1～30 秒超时和不超过 65536 字符的 stdout 上限。
- `pre_stage / post_stage / repair_requested` 可使用 `fail_run`；`fail_stage / approval_requested / approval_resolved` 只能使用 `warn`。
- `fail_run` 只阻止 Harness 编排继续，不得伪造或覆盖 Validator 原始退出码。
- 每次 Hook execution 必须持久化并写入事件流，`audit-run` 必须校验其 Schema。
- Handler 是受审查的仓库代码，不等价于操作系统级文件或网络沙箱；不得写正式工作项资产。

### 6.5 受控全链路生成与发布契约

- regeneration bundle 只能写当前工作项正式资产白名单，禁止路径穿越、跨工作项和修改 `manifest.json`、原始输入或业务代码。
- bundle 必须先在隔离仓库副本执行现有 post normalizer 与 `validate_work_item --strict --skip-code-reviews`。
- 隔离校验成功后只写 run staging、candidate manifest 和 pending approval，不得直接覆盖正式资产。
- Approval 必须绑定 candidate aggregate hash、全部正式目标 aggregate hash、manifest/raw inputs fingerprint 和逐文件 hash。
- 发布前必须再次校验全部绑定值；任一正式目标、候选或上游输入漂移都必须拒绝发布。
- 多文件发布必须先备份，再使用同目录临时文件替换，并维护 `publish_transaction.json`。
- 任一替换或发布后正式 strict 失败时，必须恢复所有旧文件并删除本轮新增文件。
- 检测到 `prepared/publishing` transaction 时必须先恢复；不得在未恢复事务上开始新发布。
- Command provider 使用可信 argv 和 stdin/stdout JSON 协议，禁止 `shell=True`；该边界不等价于操作系统级模型沙箱。
- 成功发布不执行代码评审，不修改业务代码；最终工作项仍必须满足现有 strict。

### 6.6 分级 Eval 与回归门禁契约

- Eval 唯一正式入口为 `scripts/run_eval_suite.py --tier smoke|regression|golden`；`run_evals.py` 保留为 fixture 兼容入口。
- `smoke` 必须覆盖快速正向规则与负向 Validator；`regression` 必须覆盖全部登记 fixture；`golden` 必须包含 regression、全量 Harness 单元测试和代表性工作项 strict。
- 每次执行必须输出符合 `eval_suite_report.schema.json` 的结构化报告，至少包含逐 fixture 指纹、检查数、预期失败数、耗时、命令退出码和 baseline 差异。
- 负向 fixture 意外通过与正向 fixture 失败同等阻断；不得删除负向检查或降低 Validator 强度以通过门禁。
- Golden baseline 必须绑定 suite version、fixture 集、量化检查数、预期失败数、命令数和逐 fixture SHA-256。
- baseline 缺失、指标漂移、fixture 指纹漂移或执行失败必须非零退出；baseline 只能通过显式 `--update-baseline` 且在本轮全部检查通过后更新。
- PR / push 至少运行全量 Harness 单元测试与 regression；主分支与人工发布前应运行 golden。CI 不得使用 `--update-baseline` 自动接受漂移。
- Eval 报告和运行日志是派生产物，不是需求、Case Plan 或 testcase 真源，不得反写正式工作项资产。

### 6.7 多角色受限 Agent Runtime 契约

- 多角色顺序固定为 `prd_structurer -> case_generator -> case_reviewer -> asset_formatter`；后序角色不得在前序角色校验成功前执行。
- 每个模型 turn 只能返回一个 `harness_model_action`；允许 Action 仅为读取、输入搜索、staging 提案、阶段校验、结束阶段和请求审批。
- PRD Structurer 只能写 evidence/structured PRD，且必须同步提交 `structured_prd.md` authoring 真源与语义一致的 JSON 编译投影；Case Generator 只能写 testcase 交付及派生视图且不得修改 Case Plan，并必须在交接前校验 testpoints、Case Plan 与 testcase 的交叉一致性；Reviewer 只能写 reviews 且不得重写 testcase；Formatter 只能写 `feishu_ready.md`。
- `search_inputs` 只开放给 PRD Structurer；其他角色必须消费已结构化的上游产物，不得绕过设计层重新解释 raw input。
- 所有角色输出只能写 run 内 `role_workspace`；每个角色必须至少提交一个候选并通过角色 Validator，校验后的 staging hash 漂移必须重新校验。
- 四角色共享模型调用、wall time、token、cost 预算；每角色最多 8 turn、2 repair，耗尽时必须停在人工审批，不得继续调用模型。
- Reviewer 的问题结论不得直接覆盖 testcase；Formatter 的输出是派生阅读资产，不得成为业务真源。
- Formatter 阶段结束前必须将累计候选送入隔离仓库执行现有 normalizer 与 strict；只有隔离 strict 通过才能创建发布审批。
- 最终 Approval 必须绑定 candidate、全部正式目标和 manifest/raw inputs hash；正式发布复用 transaction journal、备份、发布后 strict 与失败回滚。
- `approve-roles / reject-roles` 只处理 `multi_role` run；manual/预算/repair 审批不得借发布入口直接写正式资产。
- `role_runtime_state.json`、Action、Diagnostic、Telemetry、Hook、Approval、generation candidate 和 publish transaction 必须可由 `audit-run` 重放。

### 6.8 Harness-Loop 收口与保留契约

- 工作项级进程锁必须绑定 PID 与唯一所有权 token；活跃进程锁不得被 `--force-unlock` 删除，旧持有者不得删除后继锁。
- 恢复未完成发布前必须确认全部既有正式文件均有备份；备份缺失时不得执行部分恢复。
- 恢复必须清理 transaction 记录的发布临时文件；回滚临时文件无论成功或失败都不得残留。
- `audit-run` 除 Schema 与事件序列外，必须交叉校验 Action、Approval、Hook execution 与对应事件。
- minimal 清理不得删除非终结 run、pending approval、进程锁或 `prepared/publishing` 事务；默认保留发布备份和 transaction/candidate 元数据。
- minimal 清理同样不得删除 `prepared/committing` Case Plan commit transaction；必须先执行 `recover-case-plan`。
- `scripts/run_harness_closeout.py` 是正式端到端关闭入口，必须执行确定性 Harness、run audit、golden 和质量基线，并证明 `.generation` 之外的工作项文件未变化。
- 本地锁不等价于分布式锁，transaction journal 不等价于文件系统原生多文件原子提交；这些边界必须显式记录。

### 6.9 并行 Reviewer Runtime 契约

- 并行 Reviewer 仅通过 `agent-roles --parallel-reviewers` 显式启用；默认单 Reviewer 路径保持兼容。
- Case Reviewer 子阶段固定为 `evidence -> flow -> testcase` 的确定性持久化顺序，模型调用最多 3 worker 真实并发；线程只缓冲 Action、事件与结果，Coordinator 串行落盘。
- 三路 Reviewer 只读工作项 role staging，只能向各自 run-local 目录提交结构化 findings；不得写 structured PRD、Case Plan、testcase 或正式 reviews。
- 共享 model call/token/cost/wall/usage 预算必须并发安全。并行模式默认 model call budget 为 48，并支持 per-reviewer turn、repair 与 timeout 配置。
- 3/3 succeeded 是不可绕过的 barrier。任一路失败、超时、非法 Action、路径越权、staging 漂移或预算停止时，不生成聚合 bundle、不进入 Formatter/发布，只创建 `manual_decision` pending approval；该审批没有 continue 选项，只能使用 `reject-roles` 结束。
- Findings 必须包含稳定 ID、Reviewer、类型、产物路径、位置、severity、message、suggestion、trace IDs 与确定性 dedupe key。聚合按 severity、Reviewer、finding ID 稳定排序，以标准化路径/位置/消息去重并记录冲突。
- 仅在 3/3 后生成 run-local review bundle 和确定性 `reviews/review_record.md` staging，再执行现有 Review Gate 与角色 staging 漂移校验；通过后方可继续 Formatter 和最终发布审批。
- Telemetry 与 audit 必须记录并交叉校验每路 calls/tokens/cost/status、Action、finding、事件、barrier、bundle hash 与终态；历史 run 不存在 parallel review state 时跳过。
- 当前只承诺单机 Case Reviewer 子阶段并发；不引入分布式锁、长期 memory、任意 shell、自动代码评审或 OS 级沙箱。

### 6.10 Multi-role 崩溃恢复契约

- `recover-roles` 只处理异常遗留为 `running` 的 multi-role run；正常 `waiting_approval` 必须继续使用 `approve-roles/reject-roles`。
- 活跃 PID 持有的锁不得强制删除；只有确认持有进程已死亡后才允许 `--force-unlock` 恢复。
- 恢复必须保留 run-local staging、Action、Finding、日志和诊断，把所有未完成角色标为 skipped，清空 current role，并将 run 终态化为 cancelled。
- 恢复不得续 model turn、复用部分并行 Reviewer 结果、补跑任一路 Reviewer、生成聚合 bundle、进入 Formatter 或发布正式资产；后续业务执行必须创建新 run。
- 存在未完成 publish transaction 时必须先执行 `recover-generation`；存在 pending approval 时不得由恢复入口代替人工审批。
- `multi_role_recovery.json`、恢复事件、run/role state、Telemetry、Run Summary 与 cleanup blocker 必须可由 `audit-run` 交叉复核；重复恢复必须幂等。

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
