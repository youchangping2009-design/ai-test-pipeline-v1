# AI Test Pipeline V1 试运行计划

说明：

- 这是试运行方案文档，保留了部分历史阶段口径
- 当前正式流程口径以 `START_HERE.md` 与 `WORKFLOW_CONTRACT.md` 为准
- 文中若出现 `testcases.md` 或 `traceability_matrix.json` 的单一真源表述，应按历史兼容口径理解

## 一、试运行目标

本次试运行目标是验证当前仓库的真实闭环是否稳定，而不是继续扩展新功能。

重点验证以下链路：

原始输入  
→ `evidence`  
→ `structured_prd`  
→ `traceability`  
→ `testcases`  
→ `review_record`  
→ `review_gate`  
→ `validate_work_item`  
→ `feishu_ready`

本轮重点关注：

- PRD 信息是否完整保留
- evidence 与 traceability 是否可追溯
- 单点用例与流程类用例是否都能正确产出
- 编号 / 标签 / 测试类型 / 优先级是否稳定
- review 记录是否可用于闭环追踪
- 飞书导出是否可直接用于同步

---

## 二、试运行范围

### 1. 纳入范围

- PRD 结构化
- evidence_inventory 补全
- traceability_matrix 补全
- 单点用例生成
- 流程类用例生成
- structured_prd 校验
- testcase lint
- review gate
- validate_work_item
- feishu_ready 导出

### 2. 不纳入范围

- 自动化脚本自动生成
- 平台化 UI 建设
- 缺陷系统自动回写
- 多项目统一看板
- 更多角色审批流
- 与业务代码实现的自动比对

---

## 三、试运行需求选择原则

试点需求建议满足：

- 输入资料较完整
- 可整理为 evidence
- 存在明确主流程或关键链路
- 同时包含规则校验与页面表现
- review 参与人可给出反馈

建议优先选择：

- 配置 / 发布 / 生效类需求
- 涉及状态流转的需求
- 同时含 API 规则与 UI 展现的需求

---

## 四、角色分工建议

### 1. 方案负责人

- 选择试运行项目与工作项
- 组织 review
- 维护问题清单
- 汇总试运行结论

### 2. 执行测试同学

- 整理输入资料
- 补全 evidence
- 生成 structured_prd
- 生成 testcase
- 补全 traceability
- 运行校验脚本

### 3. 评审参与人

- 评审 structured_prd / testcase / traceability / review_record
- 识别规则口径、提示词口径、输出质量问题

---

## 五、执行流程

### Step 1：初始化项目与工作项

如项目未初始化：

```bash
/usr/bin/python3 scripts/init_project.py \
  --project-code <PROJECT_CODE> \
  --project-name "<项目名称>"
```

创建工作项：

```bash
/usr/bin/python3 scripts/create_work_item.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --title "<需求标题>" \
  --requirement-version <VERSION>
```

初始化后至少应看到：

- `manifest.json`
- `inputs/`
- `evidence/evidence_inventory.json`
- `structured_prd/structured_prd.json`
- `traceability/traceability_matrix.json`
- `testcases/testcases.md`
- `reviews/review_record.md`

### Step 2：沉淀输入资料与 evidence

将原始 PRD、截图、补充说明放入：

`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/`

同时补全：

`evidence/evidence_inventory.json`

重点检查：

- 输入来源是否清楚
- evidence 是否能支撑后续结构化
- 待确认项是否被明确记录

### Step 3：生成 structured_prd

产出：

`structured_prd/structured_prd.json`

要求：

- 包含 `project_info / requirement_info / modules / flows`
- 模块、功能点、规则、字段定义清晰
- Flow 能承接主流程、关键 checkpoint、success_criteria

### Step 4：执行 structured_prd 校验

```bash
/usr/bin/python3 skills/prd-structuring/scripts/validate_structured_prd.py \
  --input assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.json
```

重点关注：

- schema 是否通过
- `step_no` 是否连续
- `module_name / feature_name` 是否能映射
- `main_flow` 是否具备必填结构

### Step 5：生成 testcase

产出：

- `testcases/testcases_main.md`
- `testcases/testcases.md`（兼容镜像）

要求：

- 同时包含单点用例与流程类用例
- 使用统一表头
- 编号符合 `project_code-page_code-page_module_code-terminal_code-type_code-seq`
- 标签只使用封闭集合
- 流程类用例通过测试类型、备注、编号识别，而不是靠旧标签

### Step 6：执行 testcase lint

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_lint.py \
  --input assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/testcases/testcases_main.md
```

重点关注：

- 表头与必填列是否正确
- 编号是否唯一且完整
- 标签是否来自封闭集合
- 是否至少命中 1 个自动化执行载体或人工执行责任标签
- 核心流程或关键变更是否同时包含 `开发必测` 与 `测试必测`
- 测试类型与 `type_code` 是否一致
- 流程类用例是否具备 `来源 Flow`、关键结果和终态表达

### Step 7：补全 traceability

补全：

- `traceability/coverage_first_traceability.json`
- `traceability/traceability_adapter.json`
- `traceability/traceability_matrix.json`（legacy 对照）

重点关注：

- evidence 是否映射到 structured item
- structured item 是否映射到 testcase
- 关键链路与关键规则是否可追溯

### Step 8：执行 review gate

```bash
/usr/bin/python3 skills/review-gate/scripts/review_gate.py \
  --structured-prd assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/structured_prd/structured_prd.json \
  --testcases assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/testcases/testcases_main.md \
  --evidence assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/evidence/evidence_inventory.json \
  --traceability assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/traceability/coverage_first_traceability.json \
  --checklist skills/review-gate/checklists/manual_review_checklist.md
```

重点关注：

- structured_prd 是否达到正式评审门槛
- testcase 是否达到正式评审质量
- evidence / traceability 是否支撑追溯

### Step 9：完成人工评审

在：

`reviews/review_record.md`

中至少记录：

- `评审结论`
- `问题清单`
- 修改建议或后续动作

### Step 10：执行工作项级统一校验

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

该步骤会统一确认：

- `manifest.json`
- `evidence/evidence_inventory.json`
- `structured_prd/structured_prd.json`
- `traceability/traceability_matrix.json`
- `testcases/testcases.md`
- `reviews/review_record.md`
- `review_gate`

是否已形成工作项闭环。

### Step 11：导出 feishu_ready

```bash
/usr/bin/python3 scripts/export_feishu_ready.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

输出：

- `feishu_ready.md`

---

## 六、试运行验收标准

### 1. 流程可执行

至少 1 个项目、1 个工作项能跑通：

- 初始化
- evidence
- structured_prd
- testcase
- traceability
- review
- validate_work_item
- feishu_ready

### 2. 输出质量

至少满足：

- `structured_prd` 无明显结构错误
- evidence 与 traceability 可追溯
- testcase 无明显泛化问题
- 编号 / 标签 / 测试类型 / 优先级符合规则
- `review_record` 章节完整

### 3. 使用成本

至少满足：

- 执行同学可按文档走通
- 报错可理解、可修复
- 人工 review 成本可接受

---

## 七、试运行问题清单维度

建议按以下维度记录问题：

### 1. 输入问题

- PRD 信息缺失
- evidence 录入不完整
- 待确认项过多

### 2. 结构化问题

- 模块拆分不合理
- Flow 抽取不稳定
- 字段 / 规则漏提

### 3. 用例问题

- 单点用例覆盖不足
- 流程类用例不闭环
- 编号 / 标签 / 测试类型 / 优先级不稳定

### 4. 追踪问题

- evidence 与 structured_prd 断链
- structured_prd 与 testcase 断链
- traceability 表达不清晰

### 5. 协作问题

- 文档不清晰
- review 成本偏高
- 导出结果不顺手

---

## 八、试运行输出物

### 1. 过程产物

- evidence
- structured_prd
- traceability
- testcase
- review_record
- feishu_ready

### 2. 总结产物

- 试运行问题清单
- 试运行结论
- 下一轮收口建议

---

## 九、后续收口原则

试运行后的下一阶段只建议做：

- 高频失败项修复
- prompt / rules / docs 口径继续收口
- 导出与 review 体验优化

不建议立即扩展：

- 更复杂的自动化能力
- 更复杂的平台能力
- 更大范围的流程改造
