# Architecture

本文档描述 AI Test Pipeline 当前仓库的真实架构边界，重点对齐：

- 当前闭环能力
- 当前资产模型
- Agent 分工
- 质量门与脚本关系
- 项目层 / 工作项层目录组织

当前正式口径以 `START_HERE.md` 与 `WORKFLOW_CONTRACT.md` 为准。

---

## 一、仓库定位

`ai-test-pipeline-v1` 是测试资产生产仓，不承载业务代码。

仓库当前负责沉淀：

- 输入证据
- 结构化 PRD
- 追踪关系
- 测试用例
- 评审记录
- 对应规则、模板、脚本与质量门

当前闭环已跑通：

- `structured_prd`
- `testcase`
- `review_record`
- `review_gate`
- `validate_work_item`
- `feishu_ready`

核心原则：

- 不修改业务代码
- 不遗漏 PRD 信息
- 所有产物可追溯
- 所有规则以仓库内 schema / rules / templates 为准

---

## 二、总体分层

当前架构分为 5 层。

### 1. 规则层
负责定义“应该怎么做”。

主要位置：

- `tool_adapters/`
- 宿主私有规则目录（当前为 `.cursor/rules/`）
- `skills/numbering-tagging/rules/`
- `skills/review-gate/checklists/`

承载内容：

- 结构化规则
- 用例生成规则
- 编号规则
- 标签规则
- 优先级规则
- review checklist

### 2. 结构层
负责定义“产物长什么样”。

主要位置：

- `schemas/`
- `skills/*/templates/`
- `skills/prd-structuring/schema/`

承载内容：

- `structured_prd` schema
- testcase 模板
- evidence / traceability / review 占位结构

### 3. 能力层
负责定义“按什么阶段工作”。

主要位置：

- `skills/`
- `prompts/`
- `tool_adapters/`
- 宿主私有规则目录（当前为 `.cursor/rules/`）

当前能力围绕以下阶段组织：

- `requirement-summary`
- `prd-structuring`
- `case-generation`
- `numbering-tagging`
- `review-gate`
- `asset-formatting`

### 4. 资产层
负责定义“产物放在哪里”。

主要位置：

- `assets/projects/`

当前真实资产模型为：

- `evidence`
- `structured_prd`
- `traceability`
- `testcases`
- `review_record`

`manifest.json` 仍存在，但它是工作项元数据，不属于本轮强调的核心业务资产模型。

### 5. 执行层
负责定义“如何初始化、校验、串联流程”。

主要位置：

- `scripts/`
- `skills/*/scripts/`

当前已具备：

- 项目初始化
- 工作项初始化
- `structured_prd` 校验
- `testcase` lint
- `review_gate`
- `validate_work_item`
- `feishu_ready` 导出

---

## 三、Agent 分工

仓库当前以 `AGENTS.md` 中的 4 个角色为准。

### 1. PRD Structurer
职责：

- 将原始 PRD、截图、补充描述转为结构化 PRD

主要产物：

- `structured_prd.json`

### 2. Case Generator
职责：

- 基于结构化 PRD 生成标准测试用例

主要产物：

- `testcases.md`

关键关注点：

- 单点用例覆盖
- 流程类用例覆盖
- 编号 / 标签 / 优先级符合规则
- 标题 / 步骤 / 预期结果可执行、可校验

### 3. Case Reviewer
职责：

- 检查覆盖率、逻辑完整性、字段约束、异常场景、边界场景

主要产物：

- `review_record.md`

关键关注点：

- 评审结论
- 问题清单
- 质量门是否可通过

### 4. Asset Formatter
职责：

- 将产物整理为目标输出格式

当前重点输出：

- Markdown
- JSON
- `feishu_ready.md`

---

## 四、核心资产模型

### 1. evidence
工作项级路径：

- `evidence/evidence_inventory.json`

作用：

- 记录原始输入证据
- 标记输入来源与可用性
- 为结构化与追踪提供证据底座

### 2. structured_prd
工作项级路径：

- `structured_prd/structured_prd.json`

作用：

- 将原始需求重构为可生成、可校验、可追溯的结构对象

当前核心结构至少包括：

- `project_info`
- `requirement_info`
- `modules`
- `flows`

### 3. traceability
工作项级路径：

- `traceability/traceability_matrix.json`

作用：

- 建立 `evidence -> structured_prd -> testcase` 的追踪关系
- 支撑“信息不遗漏”和“产物可追溯”的仓库目标

### 4. testcases
工作项级路径：

- `testcases/testcases.md`

统一表头：

```md
| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |
```

testcase 同时包含：

- 单点用例
- 流程类用例

流程类用例通过以下信息识别，而不是靠旧标签：

- 测试类型
- 编号 `type_code`
- 备注中的 `来源 Flow`

### 5. review_record
工作项级路径：

- `reviews/review_record.md`

当前关键章节：

- `评审结论`
- `问题清单`

它既是人工评审沉淀，也是工作项闭环的追溯记录。

### 衍生产物
当前工作项还可产出：

- `feishu_ready.md`

它用于分发与展示，不替代上述核心资产。

---

## 五、项目层与工作项层组织

### 项目层
目录：

`assets/projects/<PROJECT_CODE>/`

用于沉淀：

- 项目静态元数据 `project_manifest.json`
- 公共输入 `inputs/common/`
- 工作项、用例、风险派生索引
- 项目级质量汇总
- 人工确认的可复用知识

项目层不保存 evidence、structured PRD、testcase、traceability 或 review 正式真源。

### 工作项层
目录：

`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/`

用于沉淀：

- 单次需求输入
- 工作项 evidence
- 工作项 structured_prd
- 工作项 traceability
- 工作项 testcase
- 工作项 review
- 工作项 manifest 元数据
- 工作项 `feishu_ready`

---

## 六、脚本入口与质量门

### 1. 初始化入口

- `scripts/init_project.py`
- `scripts/create_work_item.py`

负责创建项目 / 工作项资产骨架与占位模板。

### 2. 单项校验入口

- `skills/prd-structuring/scripts/validate_structured_prd.py`
- `skills/case-generation/scripts/testcase_lint.py`
- `skills/review-gate/scripts/review_gate.py`

负责分别校验：

- structured_prd
- testcase
- review 阶段质量门

### 3. 统一校验入口

- `scripts/validate_work_item.py`

当前工作项级统一校验会串联：

- `manifest.json`
- `inputs/requirement_summary.md`
- `inputs/source_manifest.json`
- `evidence/evidence_inventory.json`
- `structured_prd/structured_prd.json`
- `acceptance/` 与 `design/` 决策层
- `traceability/coverage_first_traceability.json`
- `testcases/case_plan.json`
- `testcases/testpoints.json`
- `testcases/testcases_main.md`
- `reviews/review_record.md`
- `reviews/quality_report.json`
- `review_gate`

项目级使用：

- `scripts/refresh_project_views.py`
- `scripts/validate_project.py`

### 4. 导出入口

- `scripts/render_structured_prd_markdown.py`
- `scripts/compile_structured_prd_json.py`
- `scripts/export_feishu_ready.py`

用于在 `structured_prd.md` 与 `structured_prd.json` 之间做编译/重建，并导出飞书可用稿。

---

## 七、目录示意

```text
ai-test-pipeline-v1/
├── .cursor/
├── docs/
├── prompts/
├── schemas/
├── skills/
├── scripts/
└── assets/
    └── projects/
        └── <PROJECT_CODE>/
            ├── README.md
            ├── project_manifest.json
            ├── inputs/common/
            ├── indexes/
            ├── reports/
            ├── knowledge/
            └── work_items/
                └── <WORK_ITEM_ID>/
                    ├── README.md
                    ├── manifest.json
                    ├── inputs/
                    ├── evidence/
                    ├── structured_prd/
                    ├── traceability/
                    ├── testcases/
                    ├── reviews/
                    └── feishu_ready.md
```

---

## 八、当前边界

本轮架构口径强调“收口”，不强调扩展新功能。

当前已稳定的内容：

- 工作项闭环可跑通
- 编号 / 标签 / 优先级规则已切到最新版
- testcase 已按新规则产出并可校验
- `review_gate.py` 已复用 `validate_structured_prd.py` 与 `testcase_lint.py`
- 初始化脚本已补齐 evidence / traceability / review 模板

当前仍可后续处理但不属于本轮收口重点的内容：

- demo 资产样例进一步同步
- 历史文档与 roadmap 的补充清理
- 更多输出格式适配

---

## 九、架构总结

当前真实闭环可以概括为：

`原始输入 -> evidence -> structured_prd -> traceability -> testcase -> review_record -> review_gate -> feishu_ready`

其中：

- `structured_prd/structured_prd.md` 是结构化 PRD 真源
- `structured_prd/structured_prd.json` 是从 Markdown 编译出的机器投影
- `feishu_ready.md` 是阅读/协作用派生产物
- `evidence / structured_prd / traceability / testcases / review_record` 是核心业务资产
- `manifest` 是工作项元数据
- 编号、标签、优先级、测试类型统一受规则文件约束

这也是当前仓库在“只做一致性收口”前提下应保持的一致口径。
