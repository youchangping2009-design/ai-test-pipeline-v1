# 人工介入与审查环节

本文档说明 AI Test Pipeline 从头到尾哪些环节必须有人介入、哪些环节建议人审查、对应看哪些产物、谁来看、看什么、用什么命令收口。

它配合 `AI_TEST_CASE_PIPELINE.md` 使用，不替代流程契约。最终交付仍以 `validate_work_item.py --strict` 的退出码为准。

路径均相对于工作项根目录：

```text
assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/
```

过程产物在：

```text
.generation/runs/<RUN_ID>/
```

---

## 1. 先分清三类“人要出手”


| 类型   | 含义                                            | 不做人会怎样                  |
| ---- | --------------------------------------------- | ----------------------- |
| 契约硬门 | Harness 或 Strict 会停住，必须有 reviewer / 显式 CLI    | 无法进入下一阶段，或不能交付          |
| 阶段审查 | 当前日常跑法是“会话/脚本写产物 + resume 校验”，机器只校结构；语义对不对要人看 | 可能稳定地产出错误结果，但校验仍可能通过    |
| 异常介入 | 失败、崩溃、预算耗尽、审批悬挂、两轮 repair 仍失败                 | 不能 resume / 不能清理 / 不能发布 |


原则：

1. 机器负责格式、引用、指纹、阶段顺序和退出码。
2. 人负责需求是否理解对、待确认是否诚实、设计分流是否合理、正式用例能不能执行、候选能不能覆盖真源。
3. Reviewer 可以写评审结论，不能直接改 `testcases_main.md`。
4. 看到 `waiting_approval` 不等于已经交付，只表示系统认为这份内容值得给人看。
5. CI 只能校验已有批准凭证，不能代替人点批准。

---



## 2. 总览

按时间顺序。标注为“硬门”的环节有正式 CLI 或 Strict 拦截。


| 序号  | 环节                   | 类型                   | 谁来做         | 主要审查产物                                            | 正式动作                                         |
| --- | -------------------- | -------------------- | ----------- | ------------------------------------------------- | -------------------------------------------- |
| H0  | 选择工作项档位 S/M/L        | 阶段审查                 | 测试负责人       | `manifest.json`                                   | 写入 `work_item_level`                         |
| H1  | 准备并核对原始输入            | 阶段审查                 | 需求/测试       | `inputs/` 原文、截图                                   | 放入工作项，不删原始材料                                 |
| H2  | 需求归一化审核              | **硬门**               | 需求负责人 + 测试  | `requirement_summary.md`、`source_manifest.json`   | `approve-requirement` / `reject-requirement` |
| H3  | 图片证据抽查               | 阶段审查                 | 测试          | `image_evidence_inventory.json`                   | `resume --stop-at evidence` 前确认              |
| H4  | Reasoning 歧义确认       | 阶段审查                 | 测试 / 产品     | `reasoning_pack.json`、`analysis_report.md`        | 待确认项保持待确认，或回写摘要后重批                           |
| H5  | Structured PRD 保真审查  | 阶段审查                 | 测试 / 产品     | `structured_prd.md`、`.json`                       | 只改 authoring 真源再编译                           |
| H6  | Coverage / Gate 分流审查 | 阶段审查                 | 测试设计        | `coverage_matrix.json`、`testability_gate.*`       | 确认可测、待确认、风险、技术背景被切开                          |
| H7  | Acceptance / 责任图审查   | 阶段审查                 | 测试设计        | `acceptance_examples.*`；L 档另看责任图和矩阵               | M/L 必看；S 档可无 Acceptance                      |
| H8  | Case Plan 审查         | 阶段审查；Agent 路径为**硬门** | 测试设计        | `case_plan.md/json`；Agent 时看 staging              | 日常确认后生成用例；Agent 用 `approve-case-plan`        |
| H9  | Testpoints + 正式用例审查  | 阶段审查                 | 测试执行 / 测试设计 | `testpoints.*`、`testcases_main.md`                | 不接受候选用例直接覆盖真源                                |
| H10 | Traceability 缺口裁决    | 阶段审查                 | 测试设计        | `coverage_first_traceability.json`、quality report | 回设计层补链，禁止伪映射                                 |
| H11 | 用例评审                 | 阶段审查；交付前建议完成         | 测试负责人       | `review_record.md`、checklist、质量报告                 | 写结论和问题清单；不改正式用例                              |
| H12 | 代码映证确认               | 有代码时的**硬门**          | 开发 + 测试     | `code_reviews/`*、`design_feedback.*`              | 只把 confirmed finding 反馈到设计层                  |
| H13 | 无代码收口选择              | 阶段审查                 | 测试负责人       | 是否存在代码分支                                          | 显式 `--skip-code-reviews`，不伪造评审               |
| H14 | Agent / 全链发布审批       | **硬门**               | 测试负责人       | staging、candidate、approval、diff                   | `approve-`* / `reject-*`                     |
| H15 | 并行 Reviewer 失败       | **硬门**               | 测试负责人       | parallel review findings                          | 只能 `reject-roles`                            |
| H16 | 崩溃恢复与悬挂审批            | **硬门**               | 平台 / 测试负责人  | run_state、transaction、recovery                    | `recover-`*，恢复后业务必须新 run                     |
| H17 | 两轮 repair 仍失败        | **硬门**               | 框架或业务负责人    | `docs/roadmap/HUMAN_ACTION_REQUIRED.md`           | 人工决策，禁止降规则                                   |
| H18 | 正式交付签字               | 阶段审查                 | 测试负责人       | Strict 退出码、项目汇总                                   | 刷新项目视图后交付                                    |


---



## 3. 契约硬门详解



### H2. 需求归一化批准

这是新工作项默认的第一道正式人工门。机器校验 `requirement_sources` 通过后，run 必须进入 `waiting_approval`。没有匹配的 approved receipt，不得进入 evidence。

**谁来审**

- 需求 / 产品：确认范围、增量、待确认项是否属实。
- 测试负责人：确认来源清单完整、没有把猜测写成确定规则。
- CLI 必须显式传 `--reviewed-by`。

**必须看的产物**


| 产物                                                        | 看什么                                            |
| --------------------------------------------------------- | ---------------------------------------------- |
| `inputs/` 下原始材料                                           | 原文、截图、链接是否就是本轮消费的那批                            |
| `inputs/requirement_summary.md`                           | 已确认 / 待确认是否分开；有没有脑补必填、拦截、Toast、频率              |
| `inputs/source_manifest.json`                             | 每条来源的类型、路径或 URL、访问状态；失败来源不能假装已读                |
| `manifest.json` 的 `requirement_version`、`work_item_level` | 版本和档位是否就是本轮要跑的                                 |
| `.generation/runs/<RUN_ID>/run_state.json`                | 是否停在 `requirement_intake` / `waiting_approval` |
| 即将生成的 `inputs/requirement_approval.json`                  | 批准后核对 binding：摘要、来源清单、原始输入指纹、版本、run            |


**不要看什么当通过依据**

- 不要只看“摘要写得很完整”。
- 不要用口头“没问题”代替 CLI。
- 不要手写或伪造 receipt。

**命令**

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-requirement \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --reviewed-by <REVIEWER> \
  --note "<REVIEW_NOTE>"
```

拒绝：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py reject-requirement \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --reviewed-by <REVIEWER> \
  --note "<REASON>"
```

receipt 已写但 event/state 未完成时：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py recover-requirement-approval \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID>
```

**何时必须重批**

摘要、来源清单、原始输入聚合指纹、需求版本任一变化，旧批准立即失效。仅修改 manifest 的运行期 / 派生字段不会撤销批准。

---



### H8-Agent / H14. 候选发布批准

只要走了 `agent-case-plan`、`agent-roles` 或 `generate`，候选只在 `.generation/runs/<RUN_ID>/`。正式目录不会自动变。发布必须用独立 `approve-*`，并带上精确 hash。

**谁来审**

- 测试负责人批准或拒绝。
- 平台维护人可协助核对 hash、事务和审计，但不代替业务判断。

**批准前必须看的产物**


| 产物                                                             | 看什么                                                                                 |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `.generation/runs/<RUN_ID>/run_state.json`                     | `waiting_approval`，当前阶段符合预期                                                         |
| `.generation/runs/<RUN_ID>/role_runtime_state.json`            | 四角色是否都校验通过；谁跳过、谁失败                                                                  |
| `.generation/runs/<RUN_ID>/parallel_review/runtime_state.json` | 若启用并行 Reviewer，必须 3/3 succeeded                                                     |
| `.generation/runs/<RUN_ID>/parallel_review/review_bundle.json` | 高风险 finding 有没有未处理                                                                  |
| `.generation/runs/<RUN_ID>/staging/` 或 `role_workspace/`       | 候选内容，对照正式目录做 diff                                                                   |
| `.generation/runs/<RUN_ID>/generation_candidate.json`          | 将覆盖哪些正式文件，范围是否越权                                                                    |
| `.generation/runs/<RUN_ID>/approvals/*.json`                   | approval ID、candidate hash、target hash、upstream fingerprint                         |
| `.generation/runs/<RUN_ID>/telemetry.json`                     | 是否超预算、usage 是否缺失                                                                    |
| 正式真源快照                                                         | `structured_prd.md`、`case_plan.json`、`testcases_main.md` 等当前 hash 是否与 approval 绑定一致 |


**审查要点**

- 候选 diff 没有意外删除、没有切换 testcase 真源。
- Case Generator 没有改 Case Plan。
- Reviewer 没有重写正式用例。
- Formatter 只动了 `feishu_ready.md` 这类阅读导出。
- `soft_prompt` 没有变成保存失败。
- `technical_background`、`risk_note` 没有混进产品验收。
- 一计划一用例，没有用合并结果覆盖已有正式用例。

**命令**

```bash
# 四角色
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-roles \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --approval-id <APPROVAL_ID> \
  --candidate-hash <CANDIDATE_SHA256> \
  --approved-by <REVIEWER>

# Case Plan 单文件
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-case-plan \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --approval-id <APPROVAL_ID> \
  --candidate-hash <CANDIDATE_SHA256> \
  --approved-by <REVIEWER>

# 全链路 generate
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-generation \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --approval-id <APPROVAL_ID> \
  --candidate-hash <CANDIDATE_SHA256> \
  --approved-by <REVIEWER>
```

拒绝把对应命令换成 `reject-roles` / `reject-case-plan` / `reject-generation`。拒绝后正式资产不变，run 进入 cancelled。

任一 hash 漂移必须拒绝，不要“按最新文件再批一次”混用旧 approval ID。

---



### H15. 并行 Reviewer 3/3 失败

启用 `--parallel-reviewers` 后，Evidence / Flow / Testcase 任一路失败、超时、越权、非法 Action、预算不足或 staging 漂移，都只创建 `manual_decision` pending approval。

**没有 continue 入口。** 只能 `reject-roles`。

**要看的产物**

- `.generation/runs/<RUN_ID>/parallel_review/` 下各路 findings
- `runtime_state.json` 里哪一路失败
- 对应 Action 与 Diagnostic

---



### H12. 代码映证确认

工作项存在前后端代码分支，且未使用 `--skip-code-reviews` 时，Strict 会要求 code review 请求和 confirmation。

**谁来审**

- 开发：对照实现写 frontend / backend review。
- 测试：只把 `confirmed` 的 finding 转成设计层反馈。

**必须看的产物**


| 产物                                          | 看什么                                        |
| ------------------------------------------- | ------------------------------------------ |
| `code_reviews/code_review_request.md`       | 范围是否就是本工作项                                 |
| `code_reviews/code_review_scope.json`       | 分支、目录、是否在范围内                               |
| `code_reviews/frontend_code_review.md`      | 实现与需求差在哪                                   |
| `code_reviews/backend_code_review.md`       | 接口、校验、默认值是否与规则一致                           |
| `code_reviews/frontend_confirmation.json`   | 哪些 finding 被测试确认                           |
| `code_reviews/backend_confirmation.json`    | 同上                                         |
| `design/design_feedback.json`               | 目标层只能是 Gate / Acceptance / Case Plan 等设计产物 |
| `design/unmapped_code_review_findings.json` | 无法映射 Case Plan 的项，单独保留                     |


禁止把映证结论直接写进 `testcases_main.md`。要补用例，先改设计层，再重新派生。

---



### H16. 恢复类介入

这些不是业务评审，但必须由人选择正确入口，不能当“继续跑”使用。


| 状态                                 | 人要看的产物                                                     | 动作                                     |
| ---------------------------------- | ---------------------------------------------------------- | -------------------------------------- |
| Case Plan 事务 `prepared/committing` | `case_plan_commit_transaction.json`、正式 `case_plan.json`、备份 | `recover-case-plan`                    |
| 多文件发布 `prepared/publishing`        | `publish_transaction.json`、备份、临时文件                         | `recover-generation`                   |
| 四角色崩溃且 `status=running`            | `multi_role_recovery.json`、锁、staging                       | `recover-roles`；原 run 取消，业务换新 `RUN_ID` |
| receipt 已写、event 未完成               | `inputs/requirement_approval.json`、run events              | `recover-requirement-approval`         |
| `waiting_approval`                 | approval 文件                                                | 只能 approve / reject，禁止用 recover 绕过     |


`recover-roles` 不续模型上下文，不复用部分 Reviewer 结果。

---



### H17. 两轮 repair 仍失败

自动 repair 最多 2 轮，且不得降低规则强度。仍失败时写入：

```text
docs/roadmap/HUMAN_ACTION_REQUIRED.md
```

人要看：

- 对应阶段 Diagnostic：`code`、责任阶段、产物路径、`repair_hint`
- 当前正式产物与候选 diff
- 是规则缺口、输入不足，还是生成器缺陷

在人工决策前，不要继续盲改，也不要为了通过校验删除负向检查。

---



## 4. 阶段审查详解

以下环节在“会话 authoring + `resume --stop-at`”日常路径上，Harness 往往只检查文件是否可过 Validator。语义审查要人做。建议每个 `stop-at` 都先看产物，再 resume。

### H0. 选择 S/M/L

**产物：** `manifest.json` 的 `work_item_level`


| 档位  | 人要额外接受的强制产物                                               |
| --- | --------------------------------------------------------- |
| S   | Gate + Case Plan + Testcase                               |
| M   | 另加 Acceptance Examples。当前默认档，PT083 正式样本是 M                |
| L   | 再加 `verification_responsibility_map`、`test_design_matrix` |


生成、Bundle、最终校验必须用同一档位。命令行 `--work-item-level` 只覆盖本轮，不代替长期配置。

---



### H1. 原始输入

**产物**

- `inputs/` 下 PRD、补充说明、聊天摘录
- `inputs/images/`
- 项目级 `assets/projects/<PROJECT_CODE>/inputs/common/`（跨工作项公共材料）

**审查点**

- 材料是否属于本 `WORK_ITEM_ID`，有没有拿错图、拿错需求。
- 外部链接是否可访问；访问失败必须记进 source manifest，不能装成已读。
- 原始材料必须保留。归一化结果不能替代原文。

---



### H3. 图片证据

**产物：** `image_evidence/image_evidence_inventory.json`

**审查点**

- 页面、板块、字段名是否就是图上的字。
- 红色星号、必传、说明表有没有漏。
- 图上看不见的拦截、Toast、默认值有没有被写成确定规则。
- 多张图 SHA-256 完全相同是否符合预期（例如刻意复用旧图做流程回归）。

纯文本需求没有图，不把这一步当阻塞。

---



### H4. Reasoning

**产物**

- `analysis/reasoning_pack.json`
- `analysis/analysis_report.md`

**审查点**

- explicit / implicit / risk / ambiguity 是否分开。
- 有没有从通用 banner / 瓷片 / 金刚区套话推断本需求没有的模块。
- 待确认项是否原样保留。
- 是否显式消费了摘要和来源清单，而不是从下游 Structured PRD 反推。

发现需求理解错了：改摘要和来源清单，重新走 H2，不要只改 reasoning。

---



### H5. Structured PRD

**产物**

- `structured_prd/structured_prd.md`（authoring 真源）
- `structured_prd/structured_prd.json`（编译投影）

**审查点**

- 字段、条件、数据源、提示语是否还能回到原文或图。
- `required=true` 是否有“必填 / 必传”文字或原型星号。
- 页面 / 板块有没有被弱兜底成“添加弹窗”“小程序首页”。
- Markdown 和 JSON 语义是否一致。只改 JSON 不算改完。

---



### H6. Coverage 与 Testability Gate

**产物**

- `coverage/coverage_matrix.json`
- `acceptance/testability_gate.md`
- `acceptance/testability_gate.json`

**审查点**

- 主用例候选和 audit item 是否切对。
- `soft_prompt` 是否仍只是提示展示。
- `technical_background` 是否被隔离。
- `risk_note` / `api_guard` 是否独立，没有进 `product_acceptance`。
- `needs_confirmation` 有没有被提前写成可生成用例。
- Structured PRD 的稳定规则是否都被 Gate 接到。

这是“测什么、不测什么”的人审重点。后面 Case Plan 很难从错误分流里自愈。

---



### H7. Acceptance Examples，以及 L 档设计层

**产物**

- `acceptance/acceptance_examples.md`
- `acceptance/acceptance_examples.json`
- L 档：`design/verification_responsibility_map.md/json`
- L 档：`design/test_design_matrix.md/json`

**审查点**

- Given / When / Then 是否可观察，有没有“功能正常”。
- 是否单规则单断言。
- soft prompt 的 Then 是否只有展示，没有保存失败。
- 每条 example 是否指回存在的 Gate。
- L 档：B 端 / C 端 / API / 风险责任是否分开；C 端消费是否有 linkage 计划。

---



### H8. Case Plan（日常路径）

日常不走 Agent 时，没有 `approve-case-plan` 硬门，但正式用例前必须有人看计划。

**产物**

- `testcases/case_plan.md`
- `testcases/case_plan.json`

**审查点**

- 每条 `should_generate_case=true` 是否都该生成。
- 是否具备 page / section / module / feature。
- 是否引用有效 Gate / Example。
- `generated_testcase_ids` 是否稳定、唯一。
- 待确认、技术背景、风险项是否被排除。
- 测试同学能否只看计划就知道下一张用例表会长什么样。

`testcases/testpoints.md` 是给人看的派生视图，审查时可以一起看，但不能代替 Case Plan。

---



### H9. 正式用例与测试点

**产物**


| 产物                                            | 角色                   |
| --------------------------------------------- | -------------------- |
| `testcases/testcases_main.md`                 | 正式用例真源，必须审           |
| `testcases/testpoints.md` / `testpoints.json` | 与用例同步的评审视图           |
| `testcases/testcases.md`                      | 兼容镜像，抽查一致性即可         |
| `testcases/dev_self_testcases.md`             | 开发自测派生，看“开发必测”过滤是否合理 |
| `testcases/testcase_bundle.json`              | 投影，不作为业务审查主对象        |


**审查点**

- 一计划一用例，备注有 `来源 CasePlan：CP-xxx`。
- 按 `# 页面` + `## 板块` 分表。
- 步骤和预期能直接执行、直接判断。
- 元素标注齐全：`[]` 页面、`【】` 按钮、`《》` 弹窗、`“”` 字段、`{}` 值、`<>` 状态、`「」` 提示。
- 没有“语义等价 / 配置正确 / 功能正常”。
- 没有把筛选控件脑补成必填拦截。
- 核心流程同时有 `开发必测` 与 `测试必测`。

未经人工评审，不得用重跑候选用例覆盖已经交付的 `testcases_main.md`。

---



### H10. Traceability 与质量报告

**产物**

- `traceability/coverage_first_traceability.json`
- `traceability/traceability_adapter.json`（兼容层，抽查）
- `reviews/quality_report.json`
- `reviews/missing_rules.json`
- `reviews/missing_fidelity_points.json`
- `reviews/weak_cases.json`
- `reviews/generalized_cases.json`
- `reviews/duplicate_case_report.json`

**审查点**

- 每个唯一 main Coverage 是否落到真实用例，而不是备注里的空挂。
- `invalid=0`，主失真率是否可接受（正式交付要求 0）。
- 缺口是回 Gate / Case Plan 补链，还是把不该成为 main 的 Coverage 降为 audit。
- 质量报告指纹是否仍对应当前 Structured PRD、Coverage、Testcase、主 Traceability。

禁止为了过门禁制造伪映射。

---



### H11. 用例评审

**产物**

- `reviews/review_record.md`
- `skills/review-gate/checklists/manual_review_checklist.md`
- 上面的质量派生产物
- 并行 Reviewer 时的 `review_bundle.json`

**审查点**

- 评审结论：通过 / 有条件通过 / 不通过。
- 问题清单是否指到具体产物和 ID。
- Flow、分组、编号、标签、优先级是否可执行。
- 待确认项是否仍然暴露给提测，而不是被用例吃掉。

当前 Harness `review` 阶段还没有可审计的 `not_applicable`。`review_record.md` 若仍是“待评审”，不要 resume 到 `strict_gate` 假装评审完成。工作项交付可用 `validate_work_item.py --strict`，与 Harness review checkpoint 分开理解。

---



### H13. 无代码工作项

没有前后端分支时：

- 不要伪造 `code_review_request`、confirmation、评审人。
- 工作项 Strict 使用 `--skip-code-reviews`。
- Harness run 保持停在最后一个真实完成的阶段（通常是 Traceability）。

人要留下的是“本次无代码、已显式 skip”的事实，不是一份假的代码评审。

---



### H18. 交付前总检

**产物**

- `validate_work_item.py --strict` 退出码和日志
- `reviews/quality_report.json`
- 项目级 `indexes/`、`reports/project_quality_summary.md`
- 如有 Harness run：`audit-run` 结果

人确认的是：契约门过了，且 H2、H6、H8、H9、H11 的语义审查也做过。只报“脚本通过”不够。

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --strict

/usr/bin/python3 scripts/refresh_project_views.py \
  --project-code <PROJECT_CODE>
```

---



## 5. 按角色看：你通常只审这些



### 需求 / 产品

- `inputs/requirement_summary.md`
- `inputs/source_manifest.json`
- 原始 `inputs/` 与图片
- Reasoning / Gate 里的待确认和风险
- 需求批准 CLI 的 note



### 测试设计 / 测试负责人

- 档位
- Gate、Acceptance、Case Plan
- `testpoints.*` 与 `testcases_main.md`
- Traceability 缺口
- `review_record.md`
- 所有 `approve-*` / `reject-*`



### 测试执行

- `testcases_main.md` 能否按步骤做、按预期判
- 标签里的 `测试必测`
- 评审问题是否影响开测



### 开发

- `testcases/dev_self_testcases.md`
- 代码映证材料
- 不直接改正式用例真源



### 平台维护

- run_state、approval hash、transaction、audit
- `HUMAN_ACTION_REQUIRED.md` 中的框架缺陷
- 不代替业务批准需求或发布候选



### AI Agent

- 只在白名单里读和写 staging
- 不得自行批准、不得降低门禁、不得覆盖正式真源

---



## 6. 日常路径和 Agent 路径分别要人停几次



### 日常：写产物 + resume 校验（当前主路径）

```text
放输入
→ 审摘要和来源清单          【硬门 approve-requirement】
→ 抽查图片证据
→ 看 Reasoning 待确认
→ 看 Structured PRD
→ 看 Coverage / Gate 分流
→ 看 Acceptance（M/L）
→ 看 Case Plan
→ 看 Testpoints 与正式用例
→ 看 Traceability 缺口
→ 写或确认 Review
→ 有代码则确认映证；无代码则显式 skip
→ Strict
```

最小不可省略的人：H2 需求批准、H6 分流抽查、H8 Case Plan、H9 正式用例、H18 交付总检。

### Agent / generate 路径

在上面之外，每次准备覆盖正式资产都再加一次：

```text
隔离 strict 通过
→ waiting_approval
→ 人看 staging / candidate / hash / findings
→ approve-* 或 reject-*          【硬门】
→ 发布后正式 strict
→ audit-run
```

框架试运行必须显式拒绝，证明候选不会自动发布。

---



## 7. 审查清单（可直接打印）



### 需求批准前

- [ ] 原始材料在 `inputs/`，没有只留摘要
- [ ] `requirement_summary.md` 不是模板
- [ ] 已确认和待确认分开
- [ ] `source_manifest.json` 每条来源都有访问状态
- [ ] 准备用正式 CLI 批准，不手写 receipt



### 设计层进入 Case Plan 前

- [ ] 必填都有文字或星号证据
- [ ] soft prompt 仍是提示
- [ ] 技术背景和风险不在主验收
- [ ] 待确认没有被写成正式规则
- [ ] M 档 Acceptance 可观察；L 档责任图非空



### 正式用例发布或落盘前

- [ ] 每条用例能回到 Case Plan
- [ ] 页面 + 板块分组清楚
- [ ] 步骤和预期人能执行
- [ ] 没有候选用例覆盖已交付真源
- [ ] Agent 路径核对了 candidate hash



### 交付前

- [ ] `validate_work_item.py --strict` 为 0
- [ ] 质量报告指纹未过期
- [ ] Review 结论真实，或无代码已显式 skip
- [ ] 项目视图已刷新
- [ ] 如有 run，`audit-run` 无 error

---



## 8. 对应命令速查


| 人工动作              | 命令                                                         |
| ----------------- | ---------------------------------------------------------- |
| 只读校验到某阶段          | `run_work_item_pipeline.py start/resume --stop-at <stage>` |
| 批准 / 拒绝需求         | `approve-requirement` / `reject-requirement`               |
| 补全需求审批事件          | `recover-requirement-approval`                             |
| 批准 / 拒绝 Case Plan | `approve-case-plan` / `reject-case-plan`                   |
| 批准 / 拒绝四角色发布      | `approve-roles` / `reject-roles`                           |
| 批准 / 拒绝全链生成       | `approve-generation` / `reject-generation`                 |
| 恢复 Case Plan 事务   | `recover-case-plan`                                        |
| 恢复多文件发布           | `recover-generation`                                       |
| 恢复崩溃的四角色 run      | `recover-roles`                                            |
| 审计 run            | `audit-run`                                                |
| 工作项交付门禁           | `validate_work_item.py --strict`                           |
| 无代码门禁             | 同上，加 `--skip-code-reviews`                                 |
| 框架总验收             | `run_harness_closeout.py`                                  |


---



## 9. 一句话

人不必替脚本做格式检查，但必须在四处做主：

1. **需求有没有理解对** — 审摘要、来源、原始输入，并正式批准。
2. **哪些规则准许生成用例** — 审 Gate、Acceptance、Case Plan。
3. **正式用例能不能拿去执行** — 审 `testcases_main.md` 和 testpoints。
4. **候选能不能覆盖真源** — 审 staging 与 hash，再 `approve-`* 或拒绝。

除此之外的介入，都是失败、崩溃和框架缺陷，记录在 Diagnostic 与 `docs/roadmap/HUMAN_ACTION_REQUIRED.md`，不要混进日常业务评审。