# Case Generation Skill

## 目标

基于 `structured_prd.json` 生成标准测试用例 Markdown 表格，覆盖：

- 单点用例
- 流程类用例

该技能对应仓库中的 `Case Generator` 角色。

---

## 输入

主要输入：

- `structured_prd.json`

可选辅助输入：

- review 问题列表
- 业务优先级偏好
- 自动化优先级偏好

---

## 输出

标准输出文件：

- 工作项级测试点评审视图：`testcases/testpoints.md` / `testpoints.json`（与正式用例同步生成，以 `case_plan.json` 为来源，不是真源）
- 工作项级主真源：`testcases/testcases_main.md`
- 工作项级兼容镜像：`testcases/testcases.md`
- 工作项级审计产物：`field_audit.json` / `grouped_audit.json`

输出必须满足：

- 使用统一表头
- 满足编号 / 标签 / 优先级规则
- 能通过 `testcase_lint.py`
- 在正式 review 阶段能通过 `review_gate.py`
- 步骤和预期中的关键 UI / 业务 / 技术元素遵守 `rules/testcase_element_notation.md`

---

## 关联资源

提示词：

- `prompts/structured_to_cases_prompt.md`

模板：

- `skills/case-generation/templates/testcase_template.md`
- `skills/case-generation/templates/testcase_row_template.json`
- `skills/case-generation/templates/testpoints.template.md`
- `skills/case-generation/templates/testpoints.template.json`

校验脚本：

- `skills/case-generation/scripts/testcase_lint.py`
- `skills/case-generation/scripts/validate_testpoints_view.py`

依赖规则：

- `skills/numbering-tagging/rules/numbering_rule.yaml`
- `skills/numbering-tagging/rules/tag_rule.yaml`
- `skills/numbering-tagging/rules/priority_rule.yaml`
- `skills/case-generation/references/product_description_patterns.md`

---

## 执行步骤

### 1. 读取 structured_prd

优先读取以下信息：

- `fields`
- `modules`
- `features`
- `rules`
- `field_definitions`
- `abnormal_scenarios`
- `boundary_scenarios`
- `flows`

---

### 2. 生成单点用例

单点用例主要来自：

- `fields[]`
- 对象版 `rules[]`
- 功能规则
- 字段规则
- 边界场景
- 异常场景
- 权限场景
- 数据校验场景

标题必须明确表达验证点，不得泛化。

若 feature 来自后台配置页，至少保证：

- `添加弹窗`
- `列表区`
- `操作区`
- `排序弹窗`

四类板块均有承接。

后台配置页若同时存在 `添加 / 编辑 / 删除` 操作入口，必须补足真实 CRUD 操作链路：

- `真实新增`：从点击添加、填写合法字段、保存，到列表新增记录回显
- `真实编辑`：从点击编辑、修改字段、保存，到原记录更新且不产生重复记录
- `真实删除`：从点击删除、确认删除，到列表移除记录；若涉及排序关系，还要检查剩余记录顺序仍连续
- CRUD 链路用例不能被“合法组合场景可提交”“字段必填校验”“主流程打通”替代
- 对同构后台配置页，每个配置对象至少各有 1 条真实新增、真实编辑、真实删除用例

若存在以下结构，还必须补足专项承接：

- `field_rule_tables`：字段说明表逐行承接，并回挂到所属字段语义
- 列表区字段 + 操作区：至少 1 条列表字段用例 + 1 条操作行为用例
- 删除/引用限制：至少 1 条独立校验用例
- 条数上限 / 默认值 / 状态原词：至少 1 条明确承接原词的用例

若 `fields[]` 与对象版 `rules[]` 已存在，优先按规则直接生成用例：

- `required_when` -> 条件必填用例
- `visible_when` -> 条件展示用例
- `editable_when / readonly_when` -> 条件可编辑 / 只读用例
- `max_length` -> 长度上限用例
- `min / max / integer_only` -> 数值边界 / 非整数非法用例
- `data_source / filter / order_by / display` -> 数据源、过滤、排序、展示格式用例
- `max_count` -> 条数上限用例

必填 / 必选默认口径：

- 只有需求文字明确出现“必填 / 必选 / 不能为空 / 必须填写 / 必须选择 / 必传”等强制语义，或原型图字段旁出现必填星号 `*` / 等价标识时，才生成保存失败、提交失败、阻止提交类必填用例。
- 若需求和原型均未说明必填，则字段默认非必填。单选、多选、筛选项、下拉框、枚举字段本身不构成必填证据。
- 对默认非必填字段，应验证展示、候选项、筛选效果、默认不选展示全部、可选配置等规则，不得脑补“为空不可提交”。

禁止默认生成以下摘要型用例：

- `字段矩阵完整性`
- `逐项检查字段矩阵`
- `条件联动`

替代策略：

- 一条规则生成一条主断言用例
- 每个 feature 额外补 1 条合法组合场景用例
- 不要再把整块添加弹窗压成一条“必填字段、条件字段和状态枚举”的摘要型用例

测试步骤和预期结果中的关键元素必须使用统一标注：

- 页面 / Tab：`[商品配置页]`、`[宣传内容]Tab`
- 按钮 / 操作入口：`【保存】`、`【新增】`
- 弹窗 / 抽屉 / 面板：`《新增商品弹窗》`
- 字段 / 表单项 / 列表列：`“商品名称”`
- 枚举值 / 输入值：`{特殊区}`、`{0}`
- 状态 / 标签 / 结果：`<已启用>`、`<体验中>`
- 提示语 / Toast / 校验文案：`「保存成功」`
- 接口 / 参数 / 技术字段：`` `goodsRegion` ``

不要把弹窗和字段都写成 `“”`；不要把提示语写成强拦截，除非 PRD 明确要求。

---

### 3. 生成流程类用例

流程类用例主要来自：

- `main_flow`
- `pre_flow`
- `post_flow`
- `support_flow`

必须重点体现：

- 前置条件
- 关键步骤
- checkpoint
- success_criteria
- state_transition
- 最终业务结果

每个 `main_flow` 至少生成 1 条完整流程型用例。

---

### 4. 应用编号 / 标签 / 优先级规则

生成 testcase 时，必须同步应用：

- 编号规则
- 标签规则
- 优先级规则

流程类用例重点注意：

- 测试类型优先为 `流程验证`
- 备注必须包含 `来源 Flow`
- 编号必须完整包含页面 / 页面模块 / 终端 / 类型编码
- 标签只能使用封闭集合，且至少包含 1 个自动化执行载体或人工执行责任标签
- 核心流程或关键变更必须同时包含 `开发必测` 与 `测试必测`
- 至少应存在一条 `P0` 流程类用例

数据 / 状态类单点 API 用例重点注意：

- 可使用 `状态流转` 或 `数据校验`
- 不要求补写 `来源 Flow`
- 备注应优先写清来源规则、断言对象和自动化建议

---

### 5. 生成标准 Markdown 文档

最终 testcase 必须按以下层级输出：

- `# 页面：...`
- `## 板块：...`
- 每个板块下再输出统一表头的 Markdown 表格

必须使用统一表头：

```md
| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |
```

输出只保留页面 / 板块标题和表格，不输出额外说明文字。

---

### 6. 生成测试点评审视图

Case Generator 必须在生成正式 testcase 的同一轮同步产出“模块 -> 功能点 -> 测试维度 -> 测试点”视图：

- `testcases/testpoints.md`
- `testcases/testpoints.json`

该视图只用于评审与沟通，必须保持：

- `truth_source = testcases/case_plan.json`
- `projection_only = true`
- 不得替代 `case_plan.json`
- 不得作为 `testcases_main.md` 的生成真源
- 可读取 `testcases_main.md` 补充页面、板块、模块和功能点上下文

必须执行：

```bash
/usr/bin/python3 skills/case-generation/scripts/generate_testpoints_view.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --case-plan <case_plan.json> \
  --testcases <testcases_main.md> \
  --json-output <testpoints.json> \
  --md-output <testpoints.md>
```

---

### 7. 执行 testcase lint

生成后必须执行：

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_lint.py \
  --input <testcases_main.md>
```

若工作项启用元素标注检查，再执行：

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_element_lint.py \
  --input <testcases_main.md>
```

---

## 自检清单

输出前必须自检：

- 是否覆盖主要模块与功能点
- 是否覆盖 rules / field_definitions / field_rules / field_rule_tables
- 若存在 `fields[]` 与对象版 `rules[]`，是否优先从它们生成用例
- 是否按页面与板块分组输出
- 是否对状态字段原词保留枚举值
- 是否覆盖异常 / 边界 / 权限
- 是否覆盖关键 `main_flow`
- 对后台配置页，是否每个配置对象都存在 `真实新增 / 真实编辑 / 真实删除` 三类操作链路用例
- 是否体现 `checkpoint / success_criteria / state_transition`
- 是否避免标题 / 步骤 / 预期结果泛化
- 是否按 `rules/testcase_element_notation.md` 标注关键页面、按钮、弹窗、字段、值、状态、提示语和技术字段
- 是否所有用例都有编号 / 标签 / 优先级 / 测试类型
- 对后台配置页，是否至少覆盖了“添加弹窗 / 列表区 / 操作区 / 排序弹窗”
- 若存在 `触达用户类型` 说明表，是否已经在所属字段 / 弹窗 / 业务规则中显式承接
- 若存在 `展示规则 / 选择活动 / 被引用不可删除 / 默认关闭` 等精确规则，是否原词进入 testcase
- 是否避免输出“字段矩阵完整性”这类摘要型标题
- 是否与 `testcases_main.md` 同步生成 `testpoints.md/json`，并确认它以 `case_plan.json` 为来源且不替代主链真源
- 每个生成正式用例的 Case Plan 是否提供 `source_coverage_ids` 或稳定的 `generated_testcase_ids`
- 若 Coverage 为空或 Case Plan 无法匹配候选，是否已停止生成而不是写出空 `testcases_main.md`

---

## 禁止行为

禁止：

- 只生成单点用例，不生成流程类用例
- 只生成流程类用例，不生成单点用例
- 使用“正常”“成功”“符合预期”这类模糊预期
- 忽略 Flow 的来源与终态
- 输出解释说明替代表格
