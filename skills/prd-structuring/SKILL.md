# PRD Structuring Skill

## 目标

将原始 PRD、截图、补充描述整理为可校验、可追溯、可用于测试用例生成的 `structured_prd.md`，再编译出 `structured_prd.json`。

该技能对应仓库中的 `PRD Structurer` 角色。

---

## 输入

可接受的输入包括：

- PRD 原文
- 截图描述
- `image_evidence/image_evidence_inventory.json`
- 原型说明
- 补充口述
- `inputs/requirement_summary.md`（主流程必需，优先于分散 raw inputs）
- 已整理的需求文本
- 项目编码 / 项目名称 / 业务线

输入材料通常放置于：

- 项目级公共资料：`assets/projects/<PROJECT_CODE>/inputs/common/`
- 工作项级：`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/`

---

## 输出

标准输出文件：

- 工作项级：`evidence/evidence_inventory.json`
- 工作项级：`structured_prd/structured_prd.md`
- 工作项级：`structured_prd/structured_prd.json`
- 工作项级：为后续 `coverage_first_traceability.json / traceability_adapter.json` 提供可映射结构

输出必须满足：

- 证据、结构化和 testcase 可追溯
- 顶层包含 `project_info / requirement_info / modules / flows`
- `structured_prd.md` 可稳定编译为 `structured_prd.json`
- 能通过 `validate_structured_prd.py`
- 能支撑后续 testcase 生成

---

## 关联资源

提示词：

- `prompts/prd_input_prompt.md`
- `prompts/prd_to_structured_prompt.md`
- `scripts/compile_structured_prd_json.py`

模板：

- `skills/prd-structuring/templates/structured_prd_template.json`

Schema：

- `schemas/structured_prd.schema.json`
- `skills/prd-structuring/schema/structured_prd.schema.json`

校验脚本：

- `skills/prd-structuring/scripts/validate_structured_prd.py`
- `scripts/validate_image_evidence_mapping.py`
- `scripts/validate_backend_config_chain.py`

---

## 执行步骤

### 1. 先整理输入

先读取主流程产物 `inputs/requirement_summary.md` 作为结构化阶段的归一化输入，并结合原始 `inputs/` 做来源核对。若该文件缺失或仍为模板，停止进入 structured_prd 阶段，先回到 `requirement-summary` 完成：

- 已明确的信息
- 待确认的信息
- Flow 线索
- 适合进入结构化阶段的整理文本

如果输入已经足够规整，可以直接进入下一步。

---

### 2. 生成 structured_prd Markdown

使用 `prompts/prd_to_structured_prompt.md` 生成 `structured_prd.md`。

生成时重点保证：

- 图上可见元素与交互入口不静默丢失
- 模块拆分合理
- feature 足够原子化
- rules 不是模糊语句
- `explicit_rules[].source_scope` 能区分正式需求、背景信息与后置 oracle；`context_only/oracle_only` 不得升级为正式验收规则
- 复合规则使用 `atomic_assertions` 拆出可独立失败的断言
- 对后台配置页优先输出 `fields[]`，`field_definitions` 作为兼容层保留
- 字段级规则优先进入对象版 `rules[]`，不要只留在 `field_rules.rule_text`
- `visible_elements / interactive_entries` 可承接截图证据
- flows 抽取合理且不悬空
- 若输入已存在 `image_evidence_inventory.json`，必须优先消费其页面骨架、字段矩阵、列表列头、操作入口、说明表逐行规则和便签限制
- 对 `banner / 瓷片区 / 金刚区 / 弹窗` 这类后台配置页，优先参照 `skills/prd-image-evidence-extractor/references/backend_config_golden_checklist.md`

尤其要保证以下规则不在 `structured_prd.md -> structured_prd.json` 过程中丢失：

- `required_when`
- `visible_when`
- `editable_when / readonly_when`
- `min / max / integer_only / max_length / max_count`
- `data_source / filter / display / order_by`

---

### 3. 补足 Flow

若输入存在连续业务链路，必须尽量抽取 `main_flow`。

同时按需要补充：

- `pre_flow`
- `post_flow`
- `support_flow`

Flow 必须重点包含：

- `flow_id`
- `flow_name`
- `flow_type`
- `business_goal`
- `steps`
- `success_criteria`
- `priority`
- `tags`

---

### 4. 保证模块映射一致

Flow 中每个 step 的：

- `module_name` 必须能在 `modules` 中找到
- `feature_name` 必须能在对应 module 的 `features` 中找到

如不存在，必须先补齐 `modules` 再输出 `flows`。

---

### 5. 编译并校验

生成后必须执行：

```bash
/usr/bin/python3 scripts/compile_structured_prd_json.py \
  --input <structured_prd.md> \
  --output <structured_prd.json>
```

然后执行：

```bash
/usr/bin/python3 skills/prd-structuring/scripts/validate_structured_prd.py \
  --input <structured_prd.json>
```

若需要显式 schema：

```bash
/usr/bin/python3 skills/prd-structuring/scripts/validate_structured_prd.py \
  --input <structured_prd.json> \
  --schema schemas/structured_prd.schema.json
```

若输入来自图片并存在 `image_evidence_inventory.json`，建议继续执行：

```bash
/usr/bin/python3 scripts/validate_image_evidence_mapping.py \
  --image-evidence <image_evidence_inventory.json> \
  --structured-prd <structured_prd.json>
```

---

## 自检清单

输出前必须自检：

- 是否包含 `project_info`
- 是否包含 `requirement_info`
- 是否包含 `modules`
- 是否包含 `flows`
- 是否至少抽取了关键 `main_flow`
- `step_no` 是否连续递增
- `main_flow` 是否有 `success_criteria / priority / tags`
- `related_modules` 是否合理
- 是否遗漏关键异常与边界场景
- 是否补齐后台配置页的 `filter_area / list_area / action_area / edit_modal / sort_modal / field_rule_table`
- 是否把列表字段、操作列行为、条数上限、默认值、删除限制继续承接到了 `structured_prd`
- 是否把条件展示、条件必填、条件只读 / 可编辑、边界值、数据源过滤 / 排序继续承接到了 `fields[]` 或对象版 `rules[]`

---

## 禁止行为

禁止：

- 只输出 modules，不输出 flows
- 用“功能正常”“支持配置”这类模糊规则替代原子规则
- 让 Flow 脱离 modules 独立存在
- 编造明显不存在的业务语义
- 输出无法直接保存为 JSON 的内容
