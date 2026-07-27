# Workflow

本文档说明 AI Test Pipeline 当前推荐的工作流，覆盖：

- 项目层初始化
- 工作项层初始化
- 原始输入沉淀
- structured_prd 生成与修订
- testcase 生成与修订
- review 沉淀
- 统一校验

建议先配合以下文件一起阅读：

- `START_HERE.md`
- `AGENTS.md`
- `WORKFLOW_CONTRACT.md`

---

## 一、核心分层

当前仓库采用两层资产结构：

### 1. 项目层

用于承载轻量项目壳，不保存正式测试资产真源：

`assets/projects/<PROJECT_CODE>/`

典型内容包括：

- 项目 README
- `project_manifest.json`
- `inputs/common/` 公共输入
- `indexes/` 工作项、用例和风险索引
- `reports/` 项目质量汇总
- `knowledge/` 人工确认的复用知识

---

### 2. 工作项层

用于承载某一次具体需求、版本迭代或单个工作项的独立产物：

`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/`

典型内容包括：

- 本次需求输入
- 本次 evidence_inventory
- 本次 structured_prd
- 本次主 traceability 与兼容层
- 本次主 testcase 与兼容镜像
- 本次 review 记录
- manifest 元信息

---

## 二、推荐主流程

推荐按以下顺序执行：

1. 初始化项目
2. 初始化工作项
3. 放入原始输入资料
4. 生成主流程输入归一化产物 `inputs/requirement_summary.md` 与 `inputs/source_manifest.json`（见 `skills/requirement-summary/`）
5. 生成 evidence_inventory
6. 生成 structured_prd
7. 生成 testability_gate
8. 生成 acceptance_examples / verification_responsibility_map（按工作项复杂度启用）
9. 生成 case_plan
10. 从 case_plan 派生 testcase
11. 生成 traceability
12. 执行 review
13. 如有 code review 映证反馈，先写入 `design/design_feedback.json`
14. 执行统一质量门
15. 修订后再次校验

正式 testcase 的步骤和预期结果应使用统一元素标注。页面 / Tab 使用 `[]`，按钮 / 操作入口使用 `【】`，弹窗 / 抽屉 / 面板使用 `《》`，字段 / 列表列使用 `“”`，枚举值 / 输入值使用 `{}`，状态 / 结果使用 `<>`，提示语 / Toast 使用 `「」`，接口 / 参数使用反引号。完整规范见 `rules/testcase_element_notation.md`。

正式 testcase 的标题、前置条件、步骤和预期还应遵守人工可读表达风格：优先写清“测试人员看到什么、做什么、结果如何判断”，避免把 coverage、schema、机器字段或“语义等价 / 结构化规则一致 / 功能正常”等抽象表达暴露在正文中。完整规范见 `rules/testcase_human_readable_style.md`。

---

## 三、项目初始化流程

使用脚本：

```bash
/usr/bin/python3 scripts/init_project.py \
  --project-code WX-YYPT \
  --project-name 测试项目 \
  --business-line 广告业务
```

初始化后会创建：

- `assets/projects/WX-YYPT/project_manifest.json`
- `assets/projects/WX-YYPT/inputs/common/`
- `assets/projects/WX-YYPT/work_items/`
- `assets/projects/WX-YYPT/indexes/`
- `assets/projects/WX-YYPT/reports/`
- `assets/projects/WX-YYPT/knowledge/`

适用场景：

- 新项目首次接入 AI Test Pipeline
- 团队需要建立统一资产目录

---

## 四、工作项初始化流程

使用脚本：

```bash
/usr/bin/python3 scripts/create_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --title 首次需求验证 \
  --requirement-version v1
```

初始化后会创建：

- `assets/projects/WX-YYPT/work_items/REQ-001/inputs/`
- `assets/projects/WX-YYPT/work_items/REQ-001/evidence/`
- `assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/`
- `assets/projects/WX-YYPT/work_items/REQ-001/traceability/`
- `assets/projects/WX-YYPT/work_items/REQ-001/testcases/`
- `assets/projects/WX-YYPT/work_items/REQ-001/reviews/`

适用场景：

- 同一项目下多次需求迭代独立管理
- 单个需求独立沉淀结构化产物与评审记录

---

## 五、输入材料沉淀

原始输入建议统一放入：

- 项目级公共输入：`assets/projects/<PROJECT_CODE>/inputs/common/`
- 工作项级输入：`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/`

可放入的内容包括：

- PRD 原文
- 截图
- 原型图
- 补充描述
- 外部规则附件

原则：

- 原始输入尽量不丢失
- 输入材料尽量可追溯
- 后续 structured_prd 应能够映射回输入来源

所有工作项先使用 `skills/requirement-summary/` 生成 `inputs/requirement_summary.md` 与 `inputs/source_manifest.json`，再进入 `structured_prd` 阶段。即使原始 PRD 已足够规整，也需要形成归一化摘要和来源清单；它们不替代原始输入。

输入清单命令：

```bash
/usr/bin/python3 skills/requirement-summary/scripts/inventory_inputs.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

输出契约见 `skills/requirement-summary/references/output-contract.md`。

---

## 六、Evidence 生成流程

evidence 产物路径：

- 工作项级：`evidence/evidence_inventory.json`

evidence 负责沉淀：

- 图上可见元素
- 可点击入口
- 输入字段
- 列表 / Banner / 卡片区
- 弹窗 / 空态 / 底栏

当输入主要来自截图、原型图或页面草图时，建议先生成：

- 工作项级：`image_evidence/image_evidence_inventory.json`

推荐顺序：

1. `inputs/`
2. `image_evidence/image_evidence_inventory.json`

图片输入建议先落盘到：

- `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/images/`

这样后续重新增强图片识别时，可以直接复用本地图片文件，而不是只依赖聊天上下文中的图片。
3. `evidence/evidence_inventory.json`
4. `structured_prd/structured_prd.json`

---

## 七、structured_prd 生成流程

structured_prd 正式产物只存在于工作项：

- Markdown 真源：`work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.md`
- 机器投影：`work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.json`

真源约定：

- `structured_prd.md` 是结构化 PRD 的 authoring 真源
- `structured_prd.json` 是从 Markdown 编译出的机器投影
- 修改 PRD 内容时，优先修改 Markdown 真源，再重新编译 JSON

当前 structured_prd 顶层要求至少包含：

- `project_info`
- `requirement_info`
- `pages`
- `modules`
- `flows`

从 JSON 重建 canonical Markdown：

```bash
/usr/bin/python3 scripts/render_structured_prd_markdown.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

从 Markdown 编译 JSON：

```bash
/usr/bin/python3 scripts/compile_structured_prd_json.py \
  --input assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.md \
  --output assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.json
```

其中：

- `modules` 用于承载模块、功能点、字段、规则、异常、边界
- `features[].page_name` 用于承载页面、Tab、一级页面容器或明确页面入口
- `features[].section_name` 用于承载页面下的业务板块、弹窗、区域、配置区、列表区、表单区或链路区
- `visible_elements / interactive_entries` 用于承接来自截图的可见元素和入口
- `flows` 用于承载关键业务链路、主流程、支撑流程、状态流转与 checkpoint
- 若存在 `image_evidence_inventory.json`，则 `structured_prd` 应优先消费其页面骨架、字段矩阵、字段规则、说明表逐行规则、列表列头、操作入口与便签补充规则

建议追加桥接校验：

```bash
/usr/bin/python3 scripts/validate_image_evidence_mapping.py \
  --image-evidence assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/image_evidence/image_evidence_inventory.json \
  --structured-prd assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.json
```

若工作项命中后台配置页家族模式，再继续执行：

```bash
/usr/bin/python3 scripts/validate_backend_config_chain.py \
  --image-evidence assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/image_evidence/image_evidence_inventory.json \
  --evidence assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/evidence/evidence_inventory.json \
  --structured-prd assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.json \
  --testcases assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/testcases/testcases_main.md
```

---

## 八、Traceability 生成流程

traceability 产物路径：

- 工作项级主真源：`traceability/coverage_first_traceability.json`
- 工作项级兼容层：`traceability/traceability_adapter.json`
- 工作项级 legacy 对照：`traceability/traceability_matrix.json`

traceability 负责沉淀：

- 主链：`evidence / reasoning_pack -> rule -> coverage -> testcase`
- 兼容层：由 `coverage_first_traceability.json` 投影出 `traceability_adapter.json`
- legacy：`traceability_matrix.json` 仅保留对照用途，不再决定主门禁

---

## 九、testcase 生成流程

testcase 产物路径：

- 工作项级用例计划真源：`testcases/case_plan.json`
- 工作项级用例计划 Markdown：`testcases/case_plan.md`
- 工作项级主真源：`testcases/testcases_main.md`
- 工作项级兼容镜像：`testcases/testcases.md`
- 工作项级测试点评审视图：`testcases/testpoints.md` / `testpoints.json`，与正式用例同步生成，以 `case_plan.json` 为来源，当前不作为真源
- 工作项级结构化投影：`testcases/testcase_bundle.json`，由 `testcases_main.md` 派生，当前不作为真源
- 工作项级审计产物：`testcases/field_audit.json`
- 工作项级分组审计产物：`testcases/grouped_audit.json`

当前统一表头为：

```md
| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |
```

生成时需要同时覆盖：

- 单点用例
- 流程类用例

最终 `testcases_main.md` 必须按“页面 + 板块”分表：

```md
# 页面：xxx
## 板块：yyy
| 用例编号 | 所属模块 | 所属功能点 | ... |
```

`page_name / section_name` 用于 Markdown 分组，`module_name / feature_name` 继续输出为表格内“所属模块 / 所属功能点”。不要把“所属模块”当成唯一分表依据。详细规则见 `rules/testcase_grouping_rules.md`。

正式用例不再建议直接从 `structured_prd` 临时生成。推荐先生成 `acceptance/testability_gate.json`，再生成 `testcases/case_plan.json`，最后从 case_plan 派生 `testcases_main.md`。正式 testcase 必须可追溯到 `case_plan_id`。

当前兼容表结构不新增列，正式 testcase 推荐在 `备注` 中显式写：

```text
来源 CasePlan：CP-001
```

P3 compatibility-only 阶段可生成 `testcases/testcase_bundle.json`：

```bash
/usr/bin/python3 scripts/build_testcase_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --testcases assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md \
  --output assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcase_bundle.json
```

该 bundle 必须通过 `scripts/validate_testcase_bundle.py` 与 `testcases_main.md` 逐条一致性比对。当前阶段仍以 `testcases_main.md` 为主 testcase 真源。

Case Generator 主流程必须从 `case_plan.json` 同步派生 `testcases/testpoints.md` / `testpoints.json`：

```bash
/usr/bin/python3 skills/case-generation/scripts/generate_testpoints_view.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --case-plan assets/projects/WX-YYPT/work_items/REQ-001/testcases/case_plan.json \
  --testcases assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md \
  --json-output assets/projects/WX-YYPT/work_items/REQ-001/testcases/testpoints.json \
  --md-output assets/projects/WX-YYPT/work_items/REQ-001/testcases/testpoints.md
```

该视图必须保持 `projection_only=true`，只用于评审，不得反写 `case_plan` 或替代 `testcases_main.md`。

或使用等价标记：

```text
case_plan_id=CP-001
```

strict 模式下，缺少显式 `case_plan_id`、引用不存在的 `case_plan_id`、空模板或仍含占位文本的 testability/case_plan 都会失败。
strict 模式下，缺失页面/板块、使用“默认页面”“未识别页面”“默认板块”“其他”“未分类”等弱分组也会被 grouping validator 阻断；非 strict 仅 warning，兼容旧工作项。

轻量需求可走：

```text
structured_prd -> testability_gate -> case_plan -> testcases
```

复杂需求可走：

```text
structured_prd -> testability_gate -> acceptance_examples -> verification_responsibility_map -> case_plan -> testcases
```

`validate_work_item.py` 默认只读，不刷新 `reviews/quality_report.json`；如需重新生成质量报告，显式传 `--write-report`。

P1-5 当前正式接入 `acceptance_examples`，并在 L 档 strict 接入轻量责任划分门与测试设计矩阵。M/L strict 要求：

- `acceptance_examples.examples` 非空
- 每条 example 有 Given / When / Then
- `case_plan.source_example_ids` 指向存在的 example
- example 的 `source_gate_ids` 与 case_plan 的 `source_gate_ids` 至少有交集
- `soft_prompt` 不得生成 hard_block acceptance example
- `technical_background` 不得生成 acceptance example

L 档 strict 额外要求：

- `design/verification_responsibility_map.json` 存在且 `responsibilities` 非空
- `design/test_design_matrix.json` 存在且 `items` 非空
- responsibility 关键字段不能是 TODO / TEMPLATE / 待补充 / 示例值
- `case_plan.source_responsibility_ids` 必须指向存在的 responsibility
- responsibility 的 `source_rule_id` 必须来自 `testability_gate`
- case_plan 引用的 responsibility 必须与自身 `source_gate_ids` 对应规则一致
- `consumer_verification_required=true` 时，case_plan 必须存在 linkage 类计划
- test_design_matrix 项必须引用存在的 gate/example/responsibility/case_plan
- 生成正式用例的 case_plan 必须被 test_design_matrix 覆盖

S 档轻量需求可显式传 `--work-item-level S`，只强制 `testability_gate -> case_plan -> testcases`。

P1-3 后，S/M/L 执行策略固定为：

- S: strict 强制 `testability_gate`、`case_plan`、testcase 到 `case_plan_id` 的追溯。
- M: 在 S 基础上强制 `acceptance_examples`，并要求 case_plan 追溯到 example。
- L: 在 M 基础上强制 `verification_responsibility_map` 与 `test_design_matrix`，并要求 case_plan 追溯到 responsibility。

工作项级别持久化在 `manifest.json.work_item_level`。生成、重跑和校验按“命令行显式覆盖 > manifest > 默认 M”解析有效档位；重跑 bundle 必须携带本轮有效档位，避免生成与校验策略不一致。

`run_submission_pipeline.py --stop-at` 支持 `verification_responsibility_map` 和 `test_design_matrix` 停点；L strict 会校验 `test_design_matrix`。

重生成任务包将 testability gate、acceptance examples、test design、case plan 拆为独立任务文件。Bundle post-write 会依次刷新 testpoints、开发自测、testcase bundle、主 traceability、兼容投影和 quality report；quality report 通过主产物 SHA-256 指纹检查是否过期。

若存在活跃 Case Plan 但 `coverage_matrix.entries` 为空，或 Case Plan 无法通过 `source_coverage_ids / generated_testcase_ids` 匹配候选用例，规则生成器必须失败，禁止写出空 `testcases_main.md`。

code review 映证结果不应直接覆盖 testcase。若 CR 发现用例缺口、实现缺口或过期用例，应先写入 `design/design_feedback.json`，再由设计层修订 `testability_gate`、`acceptance_examples`、`verification_responsibility_map`、`test_design_matrix` 或 `case_plan`。

其中流程类用例应重点体现：

- 完整链路目标
- 关键步骤
- 关键 checkpoint
- success_criteria
- 最终业务结果

---

## 十、Review 流程

review 正式资产路径：

- 工作项级：`work_items/<WORK_ITEM_ID>/reviews/review_record.md`

评审时可使用：

- `skills/review-gate/checklists/manual_review_checklist.md`

重点关注：

- structured_prd 完整性
- Flow 提取合理性
- testcase 质量
- 编号 / 标签 / 优先级
- review 结论与问题沉淀

---

## 十一、校验流程

当前仓库提供 4 层校验入口。

### 1. structured_prd 校验

```bash
/usr/bin/python3 skills/prd-structuring/scripts/validate_structured_prd.py \
  --input assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json
```

---

### 2. testcase 校验

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_lint.py \
  --input assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md
```

---

### 3. review_gate 校验

```bash
/usr/bin/python3 skills/review-gate/scripts/review_gate.py \
  --structured-prd assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json \
  --testcases assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md \
  --checklist skills/review-gate/checklists/manual_review_checklist.md
```

---

### 4. 工作项门禁与项目视图校验

工作项级：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

项目级：

```bash
/usr/bin/python3 scripts/refresh_project_views.py --project-code WX-YYPT
/usr/bin/python3 scripts/validate_project.py --project-code WX-YYPT --strict
```

---

## 十二、重生成入口

当规则已更新，或需要清理旧思路后重新执行 structuring / case generation / review / export 时，先生成一套正式任务包：

```bash
/usr/bin/python3 scripts/prepare_regeneration_run.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

脚本会在工作项目录下生成：

- `.generation/latest/00-preflight.md`
- `.generation/latest/01-prd-structurer.md`
- `.generation/latest/02-case-generator.md`
- `.generation/latest/03-case-reviewer.md`
- `.generation/latest/04-asset-formatter.md`
- `.generation/latest/run_manifest.json`

作用：

- 固定本次重跑前应清理的旧产物范围
- 固定本次重跑的输入、输出与角色分工
- 固定 structurer / case generator / reviewer / formatter 的参考规则
- 固定重跑后必须执行的校验命令
- 让重跑从“口头流程”变成“有正式入口、有任务包、有校验闭环”的标准流程

生成任务包后，通过兼容执行入口生成 regeneration bundle：

```bash
/usr/bin/python3 scripts/generate_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --provider existing
```

说明：

- `existing` 是当前产物固化入口
- `command` 是本地命令执行入口
- `openai` 是 HTTP endpoint 兼容入口
- 这些都只是兼容执行方式，不是流程真源
- 模型、endpoint、凭证应由当前宿主工具或运行时环境决定
- bundle 会经过完整性校验，缺少必要产物时不会写入

`command` 兼容入口约定：

- 通过 `--generator-command` 传入本地命令
- 执行时会注入环境变量：
  - `ATP_REPO_ROOT`
  - `ATP_WORK_ITEM_ROOT`
  - `ATP_PROJECT_CODE`
  - `ATP_WORK_ITEM_ID`
  - `ATP_RUN_MANIFEST`
  - `ATP_OUTPUT_BUNDLE`
- 本地命令可以：
  - 直接把 bundle JSON 写到 `ATP_OUTPUT_BUNDLE`
  - 或在 stdout 直接输出 bundle JSON

执行 bundle：

```bash
/usr/bin/python3 scripts/execute_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --bundle assets/projects/WX-YYPT/work_items/REQ-001/.generation/latest/regeneration_bundle.json
```

---

## 十三、初始化宽松、Review 严格

当前 testcase 校验采用分层策略：

### 1. 初始化阶段宽松

刚初始化的 `testcases_main.md` / `testcases.md` 允许只有表头，不要求立即有真实数据行。

适用场景：

- `init_project.py`
- `create_work_item.py`
- 仅做目录骨架初始化

---

### 2. Review 阶段严格

进入 `review_gate.py` 后，testcase 必须是正式产物，不能只有表头。

适用场景：

- 人工评审前
- MR 前质量门
- CI 正式校验

---

## 十四、推荐闭环

一个完整工作项的推荐闭环如下：

1. `init_project.py` 初始化项目
2. `create_work_item.py` 初始化工作项
3. 优先使用 `run_submission_pipeline.py` 自动落输入并执行到代码映证前
4. 若需要底层控制，再手动执行 `prepare_regeneration_run.py`
5. 使用 `generate_regeneration_bundle.py` 生成 bundle
6. 使用 `execute_regeneration_bundle.py` 执行 bundle
7. 完成前端代码 CR，并人工确认 `frontend_confirmation.json`
8. 完成后端代码 CR，并人工确认 `backend_confirmation.json`
9. 运行 `validate_work_item.py`
10. 如失败，根据 summary 修订后重跑

当工作项达到稳定状态后，刷新项目索引和质量汇总；不得复制正式产物到项目根。

## 十五、代码评审阶段

代码评审现在也是流水线的一环，但有两个硬约束：

1. 代码评审只做映证，不修改业务代码。
2. 代码评审只新增 CR 产物，不修改历史产出物。

### 1. 更适合放到前端 CR 的行为

- 点击能力、是否真可跳转
- 固定文案、显隐状态、默认选中、弹窗/抽屉/Tab 等容器结果
- 样式差异、超长截断、前端定时器、前端实现的数量上限
- 前端本地排序、过滤、补齐、去重

### 2. 更适合放到后端 CR 的行为

- 数据来源、状态过滤、枚举值
- 排序主规则与并列规则
- 分页、默认值、补齐逻辑
- 接口字段、缺省返回、共享契约

## 十六、测试提交流水线入口

推荐测试直接使用：

```bash
/usr/bin/python3 scripts/run_submission_pipeline.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --input /path/to/prd.docx \
  --provider command \
  --generator-command "/path/to/your-local-runner"
```

若尚未提供代码目录，脚本会自动停在代码映证前，并生成：

- `code_reviews/code_review_scope.json`
- `code_reviews/code_review_request.md`

之后测试只需补充：

- `--frontend-code-dir`
- `--backend-code-dir`

再次执行同一脚本即可把工作项推进到 `READY_FOR_CODE_REVIEW`。
