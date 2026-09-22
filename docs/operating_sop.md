# Operating SOP

本文档给出 AI Test Pipeline 的日常操作 SOP，适用于：

- 测试同学
- 需求分析同学
- 使用 AI Agent 的协作者
- 后续接入 CI 的维护者

建议先阅读：

- `START_HERE.md`
- `WORKFLOW_CONTRACT.md`

---

## 一、SOP 目标

确保团队在使用本仓库时做到：

- 目录结构统一
- 产物格式统一
- 规则执行统一
- review 过程可追溯
- 校验入口统一

---

## 二、标准操作场景

常见场景包括：

1. 新项目接入
2. 项目下新增一个需求
3. 生成主流程需求归一化产物 `inputs/requirement_summary.md` 与 `inputs/source_manifest.json`
4. 对某个工作项生成 structured_prd
5. 对某个工作项生成 testcase
6. 对某个工作项进行 review
7. 在提交前执行统一校验

---

## 三、新项目接入 SOP

### 步骤 1：初始化项目

执行：

```bash
/usr/bin/python3 scripts/init_project.py \
  --project-code WX-YYPT \
  --project-name 测试项目 \
  --business-line 广告业务
```

检查点：

- 项目目录是否创建成功
- `README.md` 是否生成
- `project_manifest.json` 是否生成
- `inputs/common/`、`indexes/`、`reports/`、`knowledge/` 与 `work_items/` 是否生成
- 项目根不得出现正式 structured PRD、testcase、traceability 或 review 真源

---

## 四、新需求接入 SOP

### 步骤 1：初始化工作项

执行：

```bash
/usr/bin/python3 scripts/create_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --title 首次需求验证 \
  --requirement-version v1
```

检查点：

- `work_items/<WORK_ITEM_ID>/` 是否创建成功
- `manifest.json` 是否生成
- `evidence/evidence_inventory.json` 是否生成
- `structured_prd/structured_prd.json` 是否生成
- `traceability/coverage_first_traceability.json` 是否生成
- `traceability/traceability_adapter.json` 是否生成
- `testcases/testcases_main.md` 是否生成
- `reviews/review_record.md` 是否生成

---

### 步骤 2：放置输入资料

将资料放入：

`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/`

建议资料类型：

- PRD
- 截图
- 原型图
- 补充说明
- 规则附件

检查点：

- 输入资料是否完整
- 文件命名是否可读
- 是否能追溯需求来源

---

## 五、需求整理 SOP（主流程前置）

所有工作项在进入 structured_prd 前必须执行 `skills/requirement-summary/`，产出：

`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/requirement_summary.md`

`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/source_manifest.json`

输入清单：

```bash
/usr/bin/python3 skills/requirement-summary/scripts/inventory_inputs.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

原则：

- 只归一化输入，不生成 `structured_prd`、设计层或正式 testcase
- 原始 PRD 已足够规整时仍需形成摘要和来源清单
- `prd-structuring` 应优先读取 `requirement_summary.md`，并结合原始资料核对
- 如需记录飞书、原型、截图、公开文档等来源，补充 `inputs/source_manifest.json`；该清单只记录来源与访问状态，不替代原始输入

输出契约见 `skills/requirement-summary/references/output-contract.md`。

---

### 步骤 3：人工审核 Requirement Summary

新工作项默认启用 `pipeline_policy.requirement_approval_required=true`。Requirement Sources 机器校验通过后，Harness run 会停在 `waiting_approval`；人工核对摘要、来源清单和原始输入后执行：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py approve-requirement \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --reviewed-by <REVIEWER> \
  --note "<NOTE>"

/usr/bin/python3 scripts/run_work_item_pipeline.py resume \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID>
```

拒绝使用 `reject-requirement`。若 receipt 已持久化但 event/state 尚未完成，使用 `recover-requirement-approval` 幂等恢复。`requirement_summary.md`、`source_manifest.json`、原始输入或需求版本变化会使旧批准失效；仅修改 manifest 运行期/派生字段不会撤销批准。CI 只能校验 receipt，不能执行人工批准。

---

## 六、Evidence 产出 SOP

### 步骤 1：补全 evidence_inventory

目标文件：

`evidence/evidence_inventory.json`

至少应覆盖：

- 可见元素
- 交互入口
- 输入字段
- 列表 / Banner / 卡片区
- 弹窗 / 空态 / 底栏

若输入主要来自截图、原型图或页面草图，建议先补：

`image_evidence/image_evidence_inventory.json`

若有原始图片文件，建议先放入：

`inputs/images/`

并先执行：

```bash
/usr/bin/python3 skills/prd-image-evidence-extractor/scripts/validate_image_evidence.py \
  --input assets/projects/WX-YYPT/work_items/REQ-001/image_evidence/image_evidence_inventory.json
```

---

## 七、structured_prd 产出 SOP

### 步骤 1：补全 structured_prd

目标文件：

`structured_prd/structured_prd.json`

至少应包含：

- `project_info`
- `requirement_info`
- `pages`
- `modules`
- `flows`

其中：

- `modules` 负责模块、功能点、字段、规则
- `features[].page_name` 负责页面、Tab、一级页面容器或明确页面入口
- `features[].section_name` 负责页面下的业务板块、弹窗、抽屉、配置区、列表区、表单区或链路区
- `flows` 负责主流程、支撑流程、状态流转、checkpoint
- 若存在 `image_evidence_inventory.json`，structured_prd 必须继续承接其页面骨架、字段矩阵、字段规则、说明表和便签补充规则

---

### 步骤 2：执行 structured_prd 校验

执行：

```bash
/usr/bin/python3 skills/prd-structuring/scripts/validate_structured_prd.py \
  --input assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json
```

通过标准：

- schema 校验通过
- Flow 业务规则校验通过

若本次输入来自图片，再执行桥接校验：

```bash
/usr/bin/python3 scripts/validate_image_evidence_mapping.py \
  --image-evidence assets/projects/WX-YYPT/work_items/REQ-001/image_evidence/image_evidence_inventory.json \
  --structured-prd assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json
```

若图片命中后台配置页家族模式，再执行链路校验：

```bash
/usr/bin/python3 scripts/validate_backend_config_chain.py \
  --image-evidence assets/projects/WX-YYPT/work_items/REQ-001/image_evidence/image_evidence_inventory.json \
  --evidence assets/projects/WX-YYPT/work_items/REQ-001/evidence/evidence_inventory.json \
  --structured-prd assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json \
  --testcases assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md
```

---

## 七、Traceability 产出 SOP

### 步骤 1：补全主 traceability 与兼容层

目标文件：

- `traceability/coverage_first_traceability.json`
- `traceability/traceability_adapter.json`
- `traceability/traceability_matrix.json`（legacy 对照）

要求：

- 主链应符合 `evidence / reasoning_pack -> rule -> coverage -> testcase`
- 兼容层只服务旧消费方
- legacy 对照不再决定主门禁

---

## 八、testcase 产出 SOP

### 步骤 1：补全 case_plan

目标文件：

- `testcases/case_plan.json`
- `testcases/case_plan.md`

要求：

- 每条计划必须有来源 `source_gate_ids`
- 每条计划必须有 `assertion`
- `soft_prompt` 只能生成 `prompt_display / ui_display`
- `technical_background` 不能生成正式 case_plan
- 正式 testcase 必须从 case_plan 派生

目标文件：

- `testcases/testcases_main.md`
- `testcases/testcases.md`（兼容镜像）
- `testcases/testpoints.md` / `testpoints.json`（主流程评审视图，与正式用例同步生成）
- `testcases/testcase_bundle.json`（兼容结构化投影，由 `testcases_main.md` 派生，并在 Traceability 前刷新）

要求：

- 使用统一表头
- 一行一条用例
- 按 `# 页面：xxx` + `## 板块：yyy` 拆分多个 Markdown 表格
- 表格内继续保留“所属模块 / 所属功能点”列，不能只按所属模块分表
- 同时覆盖单点用例和流程类用例

页面 / 板块分组规则见 `rules/testcase_grouping_rules.md`。非 strict 下弱分组只 warning；strict 下禁止空页面、空板块、默认页面、未识别页面、默认板块、其他、未分类等弱兜底。
- 步骤和预期中的关键元素遵守 `rules/testcase_element_notation.md`
- 页面 / Tab 用 `[]`，按钮 / 操作入口用 `【】`，弹窗 / 抽屉 / 面板用 `《》`
- 字段 / 列表列用 `“”`，枚举值 / 输入值用 `{}`，状态 / 结果用 `<>`
- 提示语 / Toast 用 `「」`，接口 / 参数 / 技术字段用反引号
- 标题、前置条件、步骤和预期遵守 `rules/testcase_human_readable_style.md`，正文优先使用人工可读、可执行、可判断的表达

流程类用例重点检查：

- 测试类型是否为“流程验证 / 状态流转 / 数据校验”
- 备注是否有 `来源 Flow`
- 编号 type_code 是否为 `FL / ST / DV`
- 标签是否只使用封闭集合
- 是否体现终态结果与关键结果

---

### 步骤 2：执行 testcase lint

执行：

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_lint.py \
  --input assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md
```

可选执行元素标注 lint：

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_element_lint.py \
  --input assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md
```

若需要在工作项校验中启用：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --check-element-notation
```

说明：

- 初始化模板可以仅包含表头
- 正式 review 前必须补齐真实用例
- `testpoints.md/json` 必须与正式用例同步生成，以 case_plan 为来源；不允许替代 `case_plan` 或 `testcases_main.md`
- `testcase_bundle.json` 当前只是 compatibility-only 投影，不允许反向覆盖 `testcases_main.md`
- Case Plan 阶段不得依赖未来 testcase；Testcases 阶段不得依赖未刷新的 Bundle；Bundle 一致性校验在 Traceability 前执行
- 非 strict 下元素标注问题只 warning；strict 且显式启用时，明显未标注问题会失败
- 工作项也可在 `manifest.json` 中配置 `testcase_element_notation.enabled=true` 启用同一检查

---

## 九、Review SOP

### 步骤 1：补全 review 记录

目标文件：

`reviews/review_record.md`

至少应包含：

- `评审结论`
- `问题清单`

---

### 步骤 2：对照 checklist 进行人工评审

参考文件：

`skills/review-gate/checklists/manual_review_checklist.md`

重点关注：

- Flow 结构评审
- 用例组织方式评审
- 编号 / 标签 / 优先级 / 测试类型评审
- 评审投入识别

---

## 十、统一校验 SOP

### 1. 项目级视图刷新与轻量壳校验

项目级不保存正式测试资产。先从工作项真源刷新索引和质量汇总，再校验项目壳：

```bash
/usr/bin/python3 scripts/refresh_project_views.py --project-code WX-YYPT
/usr/bin/python3 scripts/validate_project.py --project-code WX-YYPT --strict
```

---

### 2. 工作项级统一校验

适用于单个工作项质量门：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --strict
```

该脚本会检查：

- `manifest.json`
- `structured_prd/structured_prd.json`
- `testcases/testcases_main.md`
- `reviews/review_record.md`
- `manual_review_checklist.md`

并串联：

- `validate_structured_prd.py`
- `testcase_lint.py`
- `review_gate.py`

---

## 十一、失败处理 SOP

若统一校验失败，按以下顺序处理：

1. 先看 summary 中哪个阶段失败
2. 优先修复结构性问题
3. 再修复内容质量问题
4. 最后重跑统一校验

优先级建议：

1. 先修复 `structured_prd` 结构与 Flow 映射问题
2. 再修复 testcase 编号、标签、优先级与流程型用例问题
3. 再补全 review_record 与 checklist 相关内容

---

## 十二、CI 接入建议

后续接入 CI 时，建议使用以下入口：

### 项目级

```bash
/usr/bin/python3 scripts/refresh_project_views.py --project-code WX-YYPT
/usr/bin/python3 scripts/validate_project.py \
  --project-code WX-YYPT \
  --strict \
  --validate-work-items
```

### 工作项级

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

原则：

- 初始化阶段允许空模板
- 正式 review / MR / CI 阶段应使用严格质量门
- 任一关键校验失败返回非 0

---

## 十三、日常推荐命令

初始化项目：

```bash
/usr/bin/python3 scripts/init_project.py --project-code WX-YYPT
```

初始化工作项：

```bash
/usr/bin/python3 scripts/create_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

生成重跑任务包：

```bash
/usr/bin/python3 scripts/prepare_regeneration_run.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

生成 regeneration bundle：

```bash
/usr/bin/python3 scripts/generate_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --provider existing
```

如需接入本地命令、本地工具或宿主执行器：

```bash
/usr/bin/python3 scripts/generate_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --provider command \
  --generator-command "/path/to/your-local-runner"
```

如需使用 HTTP endpoint 兼容入口：

```bash
/usr/bin/python3 scripts/generate_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --provider openai
```

说明：

- `existing / command / openai` 都是兼容执行入口
- 模型、endpoint、凭证应由当前宿主工具或运行时环境决定
- 仓库只消费运行时上下文，不把模型写死在流程里

执行 regeneration bundle：

```bash
/usr/bin/python3 scripts/execute_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --bundle assets/projects/WX-YYPT/work_items/REQ-001/.generation/latest/regeneration_bundle.json
```

校验工作项：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

正式交付 / CI 严格校验：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --strict
```

显式工作项 strict 示例（示例标识需替换为实际值）：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code DEMO \
  --work-item-id REQ-001 \
  --skip-code-reviews \
  --strict
```

说明：

- `validate_work_item.py` 默认只读，不刷新 `reviews/quality_report.json`
- 需要刷新质量报告时显式传 `--write-report`
- 正式 testcase 必须显式引用 `case_plan_id`，推荐在备注中写 `来源 CasePlan：CP-xxx`
- strict 会阻止空模板、弱产物、无来源用例和引用不存在 case_plan 的用例
- 通用 eval fixture 包含 forbidden patterns 与 required assertions 两类检查
- 新工作项不得直接依赖 `--skip-code-reviews` 绕过 Harness Review；明确无代码输入时，必须为具体 run 声明 `not_applicable`
- N/A 只免除代码评审资产要求，Review 中的 design feedback、回灌凭证、Action journal 和 Oracle 校验仍必须通过

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py mark-review-not-applicable \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --declared-by <REVIEWER> \
  --reason "本工作项未提供业务代码，代码映证不适用"

/usr/bin/python3 scripts/run_work_item_pipeline.py resume \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --stop-at strict_gate
```

M/L strict 下还会强制验收示例：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code DEMO \
  --work-item-id REQ-001 \
  --skip-code-reviews \
  --strict \
  --work-item-level M
```

要求：

- `acceptance/acceptance_examples.json` 非空
- example 必须包含 Given / When / Then
- `case_plan.source_example_ids` 必须引用存在的 example
- S 档轻量需求可使用 `--work-item-level S`，不强制 acceptance examples
- L 档复杂需求使用 `--work-item-level L`，会额外强制 `design/verification_responsibility_map.json` 与 `design/test_design_matrix.json`，且 `case_plan.source_responsibility_ids` 必须指向存在并与 gate 规则一致的 responsibility

工作项级别建议：

- S: 小改动或单点规则，使用 `testability_gate -> case_plan -> testcases`
- M: 常规需求，使用 `testability_gate -> acceptance_examples -> case_plan -> testcases`
- L: 跨端链路、API兜底或风险责任明显的复杂需求，使用 `testability_gate -> acceptance_examples -> verification_responsibility_map -> test_design_matrix -> case_plan -> testcases`

初始化工作项时应将级别写入 `manifest.json.work_item_level`。日常生成和校验不传参数时读取 manifest；需要临时调整时显式传 `--work-item-level`，优先级为“CLI 覆盖 > manifest > 默认 M”。

L strict 下，`test_design_matrix.items` 不能为空，矩阵项必须引用存在的 gate/example/responsibility/case_plan，且生成正式用例的 case_plan 必须被矩阵覆盖。

code review 映证发现的用例缺口、代码实现缺口、过期用例或待确认项，应先写入 `design/design_feedback.json`。`design_feedback` 的目标层只能是测试设计决策层产物，不允许把映证反馈直接覆盖到 `testcases_main.md`。

标准代码评审报告中的 `## Findings` 表在人工 confirmation 为 `confirmed` 后，可通过 `scripts/build_design_feedback_from_code_reviews.py` 转成 design feedback；仍需设计负责人确认后应用。

反馈状态进入 `accepted` 后，按以下两阶段命令回灌：

```bash
/usr/bin/python3 scripts/manage_feedback_application.py prepare \
  --project-code <PROJECT_CODE> --work-item-id <WORK_ITEM_ID> --feedback-id DF-001

# 仅修改 feedback.target_layer 对应的设计层产物

/usr/bin/python3 scripts/manage_feedback_application.py record \
  --project-code <PROJECT_CODE> --work-item-id <WORK_ITEM_ID> --feedback-id DF-001
```

`prepare` 将 baseline 写入 `.generation/feedback_applications/`；`record` 校验实际变更后写入 `design/feedback_application.json`，再把 feedback 置为 `applied`。不要先修改目标文件后再执行 prepare，也不要直接填写 before hash。

Agent 自动回灌时不直接执行文件写入，而是依次向受限入口提交三份 Action JSON：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py feedback-action \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --run-id <RUN_ID> \
  --actor <ACTOR_ID> \
  --provider <PROVIDER_ID> \
  --action-file <ACTION_JSON>
```

`action_type` 仅允许 `prepare_feedback_application`、`propose_feedback_design_artifacts`、`record_feedback_application`。设计产物只能通过 propose 写入，且路径必须已被 prepare 冻结；反馈状态只能由 record 更新。

每个动作使用全局不重复的 `action_id`。Runtime 会先确认 `RUN_ID` 存在且属于当前项目/工作项，再将 `run_id`、`actor`、`provider` 与 Action 一起绑定到不可覆盖的 intent/result 和请求哈希；执行失败也会写终态 result，修正后应使用新的 action ID。若进程在 intent 后中断，必须用相同 Action 和相同执行上下文重试。`actor/provider` 是可审计声明，不替代宿主认证。完成后执行：

```bash
/usr/bin/python3 scripts/run_work_item_pipeline.py audit-feedback-actions \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

新工作项的 `feedback_action_journal_required=true` 与 `feedback_action_execution_identity_required=true` 会让 Review/strict 同步执行该审计；同一 feedback 的成功动作不得跨 Harness run。历史工作项没有 journal 或仍使用 1.0 journal 时保持 legacy compatibility，不补造身份记录。

`reviews/quality_report.json` 会记录 structured PRD、coverage、主用例和主 traceability 的 SHA-256 指纹。默认只读校验发现指纹变化时，执行 `validate_work_item.py --write-report` 刷新报告后再放行。

校验项目：

```bash
/usr/bin/python3 scripts/refresh_project_views.py --project-code WX-YYPT
/usr/bin/python3 scripts/validate_project.py --project-code WX-YYPT --strict
```

## 十、产物清理 SOP

当工作项已经通过评审，且不需要继续保留调试过程包时，可以切换到 minimal retention，减少过程产物和派生投影的长期堆积。

必须保留：

- `inputs/`
- `manifest.json`
- `structured_prd/`
- `acceptance/`
- `design/`（复杂需求或存在代码映证反馈时）
- `testcases/case_plan.*`
- `testcases/testcases_main.md`
- `evidence/`
- `image_evidence/`（图片型需求）
- `traceability/coverage_first_traceability.json`
- `reviews/review_record.md`
- `reviews/quality_report.json`

可清理再生：

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

清理前先 dry-run：

```bash
/usr/bin/python3 scripts/cleanup_derived_artifacts.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --mode minimal \
  --dry-run
```

确认后执行：

```bash
/usr/bin/python3 scripts/cleanup_derived_artifacts.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --mode minimal
```

清理后校验：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --retention minimal
```

## 十一、旧测试提交兼容入口

旧消费方仍可使用：

```bash
/usr/bin/python3 scripts/run_submission_pipeline.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --input /path/to/prd.docx \
  --provider command \
  --generator-command "/path/to/your-local-runner"
```

脚本行为：

1. 自动创建或维护工作项
2. 自动把需求文件 / 补充资料落到 `inputs/`
3. 自动生成和维护重跑任务包
4. 自动执行到代码映证前
5. 若缺少代码目录，则自动生成提醒

补充代码目录后：

```bash
/usr/bin/python3 scripts/run_submission_pipeline.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --skip-generate \
  --frontend-code-dir /path/to/frontend \
  --backend-code-dir /path/to/backend
```

此时工作项会进入 `READY_FOR_CODE_REVIEW` 状态。

新工作项应优先使用 `run_work_item_pipeline.py start / resume` 保持单 run checkpoint、Requirement Approval 和审计语义。`run_submission_pipeline.py` 不替代 Harness run 状态；无代码工作项必须使用 run-scoped `mark-review-not-applicable`，不得用独立 `--skip-code-reviews` 结果冒充 Harness Review 终态。

## 十二、代码评审与人工确认

新增两轮代码评审：

1. 前端代码 CR
2. 后端代码 CR

产物路径：

- `code_reviews/frontend_code_review.md`
- `code_reviews/frontend_confirmation.json`
- `code_reviews/backend_code_review.md`
- `code_reviews/backend_confirmation.json`

约束：

- CR 只做代码与用例、结构化规则的相互映证
- CR 不修改业务代码
- CR 不修改历史产出物
- 每个 CR 阶段都必须人工确认
