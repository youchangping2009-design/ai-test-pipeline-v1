# START HERE

这是 AI Test Pipeline 的统一入口页。

这个仓库定义的是流程、协议、校验口径和产物真源，不定义你必须使用哪个模型、哪个 provider、哪个宿主工具。

无论使用哪一种本地或远程 AI 宿主工具，都先看这份文件，再按需进入对应适配说明。

## 先记住 7 条

1. 仓库定义流程，不定义模型。
2. 当前宿主工具决定当前会话模型；仓库只消费运行时上下文。
3. `testcases_main.md` 是主 testcase 真源，`testcases.md` 只是兼容镜像。
4. `coverage_first_traceability.json` 是主 traceability 真源，`traceability_adapter.json` 是兼容层。
5. 正式用例不再建议直接从 `structured_prd` 生成；应先经过 `testability_gate` 与 `case_plan`。
6. 正式用例步骤和预期中的关键元素应遵守 `rules/testcase_element_notation.md`。
7. 正式用例的标题、前置条件、步骤和预期应遵守 `rules/testcase_human_readable_style.md`，优先使用人工可读、可执行、可判断的表达。

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
- `testcases/testpoints.md` / `testpoints.json` 与正式用例在 Case Generator 主流程同步生成，是从 `case_plan.json` 派生的人工评审视图，不是真源
- `testcases/field_audit.json` 与 `testcases/grouped_audit.json` 是审计产物
- `testcases_main.md` 按 `# 页面：xxx` + `## 板块：yyy` 分表；“所属模块 / 所属功能点”是表格内列，不是唯一分表依据
- testcase row 的 `__page_name / __section_name` 是隐藏分组字段，用于渲染和校验；规则见 `rules/testcase_grouping_rules.md`
- 正式 testcase 的文案表达应面向人工执行；机器字段、coverage 语言和 schema 语言只应保留在备注或结构化追溯产物中

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

```bash
/usr/bin/python3 scripts/init_project.py --project-code WX-YYPT
```

项目根采用轻量壳结构：

```text
README.md
project_manifest.json
inputs/common/
indexes/
reports/
knowledge/
work_items/
```

正式测试资产只保存在 `work_items/<WORK_ITEM_ID>/`。

项目级视图从工作项真源派生：

```bash
/usr/bin/python3 scripts/refresh_project_views.py --project-code WX-YYPT
/usr/bin/python3 scripts/validate_project.py --project-code WX-YYPT --strict
```

### 2. 初始化工作项

```bash
/usr/bin/python3 scripts/create_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

### 3. 放入输入资料

放到：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/`

所有工作项先归一化需求为：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/requirement_summary.md`

同时记录需求来源、外部链接和访问状态：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/source_manifest.json`

新工作项默认要求人工审核上述归一化内容。Harness 校验需求接入成功后会写入：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/requirement_approval.json`

该凭证绑定摘要、来源清单、原始输入聚合指纹、需求版本和审批 run；`pending` 时不得进入 evidence。

若输入主要是图片，再放到：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/images/`

### 4. 生成任务包

```bash
/usr/bin/python3 scripts/prepare_regeneration_run.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

### 5. 用当前宿主工具执行同一流程

这一步不要求你在仓库里写死模型名。

请根据你所在工具查看：

- `tool_adapters/codex/README.md`
- `tool_adapters/cursor/README.md`
- `tool_adapters/claude/README.md`

### 6. 执行统一校验

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

正式交付 / CI 建议启用严格模式：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --strict
```

当前 PT083 正式工作项已作为 strict 正向样例：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --skip-code-reviews \
  --strict
```

如需检查正式用例元素标注，可显式启用：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --check-element-notation
```

非 strict 下标注问题只输出 warning；strict 且显式启用时，明显未标注问题会失败。旧工作项默认保持兼容。

`validate_work_item.py` 默认只读，不刷新 `reviews/quality_report.json`。如确需重新生成质量报告，必须显式增加：

```bash
--write-report
```

### 7. 执行可恢复的只读 Harness 校验

首版 Harness Orchestrator 只编排已登记的 Validator，不调用模型、不执行生成器、不覆盖正式产物：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py start \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --work-item-level M \
  --strict \
  --stop-at case_plan
```

查看状态并从 checkpoint 恢复：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py status \
  --project-code WX-YGJ \
  --work-item-id PT083

/usr/bin/python3 scripts/run_work_item_pipeline.py resume \
  --project-code WX-YGJ \
  --work-item-id PT083
```

新工作项首次通过 `requirement_intake` 后会停在 `waiting_approval`。人工核对当前内容后执行：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-requirement \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --run-id <RUN_ID> \
  --reviewed-by <REVIEWER> \
  --note "<REVIEW_NOTE>"

/usr/bin/python3 scripts/run_work_item_pipeline.py resume \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --run-id <RUN_ID>
```

拒绝使用 `reject-requirement`。若进程在 receipt 已写、event/state 尚未完成时退出，使用 `recover-requirement-approval` 幂等补全。摘要、source manifest、原始输入或需求版本变化后，旧批准立即失效并重新进入 `waiting_approval`；仅修改 manifest 的运行期/派生字段不会撤销批准。CLI 必须显式传 reviewer；CI 环境不能执行批准。

阶段推进继续复用同一 `run_id`：Case Plan 阶段不依赖未来 `testcases_main.md`，Testcases 阶段不依赖未刷新的 Bundle；`testcase_bundle.json` 必须在 Traceability 前刷新并校验。无代码 M 档可在工作项 strict 使用 `--skip-code-reviews`，但当前 Harness run 尚无 Review `not_applicable` disposition。

运行状态、阶段日志、事件流与诊断写入 `.generation/runs/<RUN_ID>/`。这些是过程产物，不是真源；当前模型循环、自动 repair、Hook 与分阶段提交仍不在此入口中。

Validator 失败时，Harness 会把文本输出归一化为：

```text
.generation/runs/<RUN_ID>/diagnostics/<STAGE_ID>/attempt-<N>.json
```

每条诊断至少包含错误代码、责任阶段、产物路径、严重级别、修复提示和原始 Validator。聚合 Strict Gate 的失败会按产物语义路由回责任阶段；无法识别的输出使用 `HARNESS_VALIDATOR_FAILED` 兜底，不会静默丢失。

### 8. 运行受限 Case Plan Agent Loop

P3 仅开放 `testcases/case_plan.json` 单阶段试点。模型适配器通过 stdin 接收 turn request，并且 stdout 只能返回一个 Model Action JSON：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py agent-case-plan \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --work-item-level M \
  --provider-command-json '["/path/to/trusted-model-adapter"]'
```

模型只能读取白名单产物、搜索 `inputs/`、提交 Case Plan staging、请求 Validator 或审批。最多执行 8 个 turn 和 2 轮 repair。`commit_stage` 只会生成 pending approval，默认不会修改正式 Case Plan。

人工检查 staging、诊断和 diff 后，必须绑定本轮 approval 与 candidate hash 才能提交：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-case-plan \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --approval-id <APPROVAL_ID> \
  --candidate-hash <CANDIDATE_SHA256> \
  --approved-by <REVIEWER>
```

提交前 Harness 会再次检查正式目标、上游设计产物和 staging candidate 的 hash。任一漂移都会拒绝覆盖。正式替换由 `case_plan_commit_transaction.json` 记录：目标替换前状态为 `prepared/committing`，替换成功后先写 `committed` journal，再完成 approval/run metadata。

若审批进程被中断，先执行恢复：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py recover-case-plan \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID>
```

`prepared/committing` 会从备份回滚并恢复 pending approval；`committed` 会校验正式目标 hash 后幂等完成 approval、run state 和事件。备份缺失或 hash 漂移时只报告错误，不执行部分恢复。未恢复 transaction 存在时拒绝直接 reject 或 cleanup。

提交后 `testcases / traceability / review / strict_gate` 被标记为待刷新；Case Plan 阶段成功不等于工作项可交付。

`--provider-command-json` 是人工配置的可信运行时适配器，不属于模型可调用工具。Harness 不使用 shell 解释该参数，但无法替代操作系统级进程沙箱。

### 9. 预算、观测与 Run 审计

command adapter 可返回 `{action, usage, runtime}` envelope。启用 token/cost 门禁时，未报告 usage 会停止运行：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py agent-case-plan \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --provider-command-json '["/path/to/trusted-model-adapter"]' \
  --require-usage \
  --max-wall-seconds 600 \
  --max-total-tokens 100000 \
  --max-cost-usd 1.0
```

每个 Agent run 会输出：

- `telemetry.json`：调用次数、模型耗时、token、cost、动作、Validator 和预算
- `run_summary.json`：终态、停止原因和关键计数
- `audit_report.json`：state、event、Action、approval、diagnostic 重放结果

审计命令：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py audit-run \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID>
```

拒绝 pending approval：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py reject-case-plan \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --approval-id <APPROVAL_ID> \
  --rejected-by <REVIEWER> \
  --reason "<REASON>"
```

### 10. 运行受限 Harness Hook

Hook 配置固定在 `config/harness_hooks.json`。配置只能引用仓库内受审查的 `scripts/hooks/*.py`；Harness 使用当前 Python argv 直接执行，通过 stdin 传入结构化事件，不接受任意 shell 或可执行文件。

支持事件：

- `pre_stage / post_stage / fail_stage`
- `approval_requested / approval_resolved`
- `repair_requested`

`pre_stage / post_stage / repair_requested` 可使用 `fail_run` 阻塞编排；失败通知和审批 Hook 只能使用 `warn`，不得反向覆盖 Validator 或审批结论。每次执行写入：

```text
.generation/runs/<RUN_ID>/hooks/<EXECUTION_ID>.json
```

手工重放已登记 Hook：

```bash
/usr/bin/python3 scripts/run_hook_dispatcher.py \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --event post_stage \
  --stage-id strict_gate
```

仓库默认启用 `strict-gate-stage-summary`，它只在只读 Harness 的 `strict_gate` 成功后记录阶段摘要，不写业务产物。Hook handler 属于受信任的仓库代码；当前约束不是操作系统级沙箱。

### 11. 运行受控全链路生成

先在隔离仓库副本中执行 regeneration bundle、后处理和 strict，正式工作项不会在候选阶段被修改：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py generate \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --work-item-level M \
  --provider existing
```

可信 command adapter 使用 argv JSON，通过 stdin 接收 generation request，并返回 bundle JSON 或 `{bundle, usage, runtime}`：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py generate \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --provider command \
  --provider-command-json '["/path/to/trusted-generation-adapter"]'
```

候选通过后停在 `waiting_approval`。人工检查 `generation_candidate.json`、`staging/work_item/` 和 approval 绑定值后发布：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-generation \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --approval-id <APPROVAL_ID> \
  --candidate-hash <CANDIDATE_SHA256> \
  --approved-by <REVIEWER>
```

拒绝候选使用 `reject-generation`。发布前 Harness 会复核候选文件、全部正式目标 hash 和原始输入 fingerprint；发布使用 backup、临时文件、transaction journal 和失败回滚，完成后再次执行正式 strict。若进程在发布窗口被强制终止，使用：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py recover-generation \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --force-unlock
```

多文件事务是带 journal 的逻辑原子发布，不是文件系统原生多文件原子操作；检测到 `prepared/publishing` transaction 时必须先恢复，不得继续发布。

### 12. 运行分级 Eval 与回归门禁

统一入口提供三档评测：

```bash
/usr/bin/python3 scripts/run_eval_suite.py --tier smoke
/usr/bin/python3 scripts/run_eval_suite.py --tier regression
/usr/bin/python3 scripts/run_eval_suite.py --tier golden
```

- `smoke`：3 个快速代表 fixture，用于本地高频反馈。
- `regression`：全部 6 个 fixture 和 57 个规则/Validator 检查，用于 PR 门禁。
- `golden`：在 regression 基础上执行全量 Harness 单元测试和 PT083 M strict，并对比 `evals/baselines/golden.json`。

报告默认写入 `.generation/evals/<TIER>-latest.json`，包含逐 fixture 耗时、检查数、预期失败数、内容指纹、命令结果和 baseline 差异。任何 fixture/命令失败、负向样例意外通过、指标变化、fixture 指纹漂移或 baseline 缺失都会使门禁非零退出。

Golden baseline 不会自动刷新。只有在变更已评审且全部检查通过时，才可显式执行：

```bash
/usr/bin/python3 scripts/run_eval_suite.py --tier golden --update-baseline
```

仓库 CI 在 PR / push 先运行全量 Harness 单元测试，再运行 regression；main/master push 与手工触发额外运行 golden。`run_evals.py --fixture/--all` 继续作为兼容入口。

### 13. 运行四角色受限 Agent Runtime

四角色固定按 `PRD Structurer -> Case Generator -> Case Reviewer -> Asset Formatter` 顺序执行。可信 command adapter 每个 turn 只能返回一个 Model Action：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py agent-roles \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --work-item-level M \
  --provider-command-json '["/path/to/trusted-role-adapter"]' \
  --require-usage
```

允许 Action 仅为：

- `read_artifact / search_inputs`
- `propose_artifacts`
- `run_stage_validation / finish_stage`
- `request_approval`

角色写入边界：

- PRD Structurer：`evidence/evidence_inventory.json` 与 `structured_prd/*`；交接时必须同时提交语义一致的 `structured_prd.md` authoring 真源和 JSON 编译投影
- Case Generator：`testcases_main.md` 及其 testcase 派生视图，不得修改 `case_plan`；交接前必须通过 testpoints、Case Plan 与 testcase 交叉校验
- Case Reviewer：仅 `reviews/*`，不得重写 testcase
- Asset Formatter：仅 `feishu_ready.md`，不得修改业务真源

每个角色候选先写 `.generation/runs/<RUN_ID>/role_workspace/`，必须通过该角色 Validator 才能交接。Formatter 完成后，Harness 将累计候选送入隔离仓库执行现有 normalizer 与 L/S/M strict；通过后生成 `generation_candidate.json` 和 hash 绑定审批，仍不会自动发布。

审批发布：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-roles \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --approval-id <APPROVAL_ID> \
  --candidate-hash <CANDIDATE_SHA256> \
  --approved-by <REVIEWER>
```

拒绝使用 `reject-roles`。发布前会复核候选、正式目标和原始输入 hash；发布继续复用 transaction journal、备份、发布后 strict 与失败回滚。四角色共享 wall/token/cost 预算、Hook、Telemetry、事件和 audit；command adapter 是受信任 argv，不等价于操作系统级模型沙箱。

Case Reviewer 默认仍使用单 Reviewer。需要启用 P5-001 三路并行评审时显式增加：

```bash
--parallel-reviewers \
--max-turns-per-reviewer 4 \
--reviewer-timeout-seconds 120
```

并行模式固定运行 evidence、flow、testcase 三路只读 Reviewer。三路模型调用最多使用 3 个本地线程并发，默认共享模型调用预算提高为 48；token、cost、wall 与 usage 门禁继续共享且并发安全。每路只能读取工作项 role staging，并向自己的 run-local 目录提交结构化 findings；最终 `reviews/review_record.md` 由确定性聚合器写入 staging。

只有 3/3 succeeded 才会生成 review bundle、执行现有 Review Gate 并进入 Formatter。任一路失败、超时、越权、非法 Action、staging 漂移或共享预算不足，run 都停在 `manual_decision` pending approval；该审批仅允许通过 `reject-roles` 拒绝/取消，不提供绕过 3/3 的继续入口。该能力只承诺单机 Reviewer 子阶段并发，不承诺分布式锁、OS 沙箱、长期 memory、任意 shell 或自动代码评审。

若四角色进程异常退出并遗留 `status=running`，使用：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py recover-roles \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --run-id <RUN_ID> \
  --recovered-by <OPERATOR> \
  --reason <CRASH_REASON> \
  --force-unlock
```

`recover-roles` 只会在确认锁持有进程已死亡后保留 run-local staging、Action、Finding、日志和诊断，把未完成角色标为 skipped，并将 run 终态化为 cancelled。它不会续 model turn、复用部分 Reviewer 结果、补跑 Reviewer 或发布正式资产。存在 pending approval 时仍须使用 `approve-roles/reject-roles`；存在未完成发布事务时先使用 `recover-generation`。恢复后的业务执行必须创建新 run。

### 14. 执行 Harness-Loop 端到端收口验收

```bash
/usr/bin/python3 scripts/run_harness_closeout.py \
  --project-code WX-YGJ \
  --work-item-id PT083 \
  --work-item-level M
```

该入口顺序执行确定性 Harness、`audit-run`、golden eval 和完整质量基线，并比较运行前后工作项 `.generation` 之外的聚合 hash。任一命令失败或正式资产发生变化都会返回非零。

运行清理前，`cleanup_derived_artifacts.py` 会检查进程锁、非终结 run、pending approval 和未恢复发布事务；崩溃遗留的 running multi-role run 会明确提示先执行 `recover-roles`。存在任一阻断项时拒绝实际删除。默认会先把终结 run 的 `publish_backup`、transaction 和 candidate 元数据归档到 `.generation/backups/`。完整边界和关闭清单见 `docs/harness_loop_closeout.md`。

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
- `.generation/runs`
- `.generation/current_run.json`
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

```bash
/usr/bin/python3 scripts/cleanup_derived_artifacts.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --mode minimal
```

minimal 校验：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --retention minimal
```

strict 模式会阻止：

- 缺少或仍为模板的 `requirement_summary.md` / `source_manifest.json`
- 空模板 `testability_gate`
- 空模板 `case_plan`
- 缺少、为空或与 `case_plan` 不一致的 `testpoints.md/json`
- 活跃 Case Plan 缺少 coverage/testcase 生成映射，或生成结果为空
- `quality_report.json` 的主产物指纹已过期
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

工作项级别写入 `manifest.json.work_item_level`。执行时按“命令行显式 `--work-item-level` 覆盖 > manifest > 默认 M”解析；未指定命令行参数时不再盲目固定使用 S 或 M，而是优先读取工作项配置。

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
