# ai-test-pipeline-v1

AI 测试流程仓，用于沉淀：

- 流程规范
- AGENTS.md
- Skills
- 提示词模板
- PRD 结构化 schema
- 用例模板
- 编号规则
- 标签规则
- 优先级规则
- 输出脚本
- 评审记录模板

## 目标

- 规则与流程独立版本化
- 团队统一使用一个仓库流程入口
- 不污染业务代码仓
- 为后续平台化演进提供基础
- 兼容不同宿主工具与不同运行时模型


## 先看这里

推荐阅读顺序：

1. `START_HERE.md`
2. `AGENTS.md`
3. `WORKFLOW_CONTRACT.md`
4. `tool_adapters/<host>/README.md`

当前推荐口径：

- 仓库定义流程，不定义模型
- `testcases/testcases_main.md` 是主 testcase 真源
- `testcases/testcases.md` 是兼容镜像
- `testcases/testpoints.md` / `testpoints.json` 与正式用例在主流程同步生成，以 `case_plan.json` 为来源，不是真源
- `traceability/coverage_first_traceability.json` 是主 traceability 真源
- `traceability/traceability_adapter.json` 是兼容层
- `traceability/traceability_matrix.json` 仅保留 legacy 对照角色

## 目录说明

- `.cursor/`：Cursor 宿主适配资产，不是流程真源
- `tool_adapters/`：不同宿主工具的最小差异说明
- `skills/`：按流程阶段沉淀能力
- `prompts/`：标准提示词
- `schemas/`：结构定义
- `assets/`：项目资产沉淀
- `scripts/`：辅助脚本
- `docs/`：架构与SOP文档

## 推荐流程

当前仓库推荐按“两层资产 + 一层适配”组织：

1. 项目层
用于沉淀项目公共信息与长期资产，目录形如：

`assets/projects/<PROJECT_CODE>/`

2. 工作项层
用于沉淀某一次具体需求、版本迭代或单个工作项的独立产物，目录形如：

`assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/`

3. 宿主适配层
用于承接 Codex / Cursor / Claude 等宿主差异，但不重写流程真源，目录形如：

`tool_adapters/<HOST>/`

推荐链路如下：

1. 初始化项目
2. 初始化工作项
3. 放入原始输入材料，并生成主流程产物 `inputs/requirement_summary.md` 与 `inputs/source_manifest.json`
4. 若输入主要是截图，先将原始图片放入工作项 `inputs/images/`，再生成并校验 `image_evidence_inventory.json`
5. 生成并完善 structured_prd
6. 生成并完善 testcases
7. 补充 review 记录
8. 执行统一校验

## 项目初始化

使用项目初始化脚本创建项目级目录结构：

```bash
/usr/bin/python3 scripts/init_project.py \
  --project-code WX-YYPT \
  --project-name 测试项目 \
  --business-line 广告业务
```

初始化后会创建：

- `assets/projects/WX-YYPT/inputs/`
- `assets/projects/WX-YYPT/evidence/`
- `assets/projects/WX-YYPT/structured_prd/`
- `assets/projects/WX-YYPT/traceability/`
- `assets/projects/WX-YYPT/testcases/`
- `assets/projects/WX-YYPT/reviews/`

并生成基础占位文件：

- `README.md`
- `inputs/README.md`
- `evidence/evidence_inventory.json`
- `structured_prd/structured_prd.json`
- `traceability/coverage_first_traceability.json`（主真源）
- `traceability/traceability_adapter.json`（兼容层）
- `traceability/traceability_matrix.json`（legacy 对照）
- `testcases/testcases_main.md`（主真源）
- `testcases/testcases.md`（兼容镜像）
- `reviews/review_record.md`

## 工作项初始化

当同一个项目下存在多次需求迭代时，使用工作项初始化脚本创建独立目录：

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

并生成基础占位文件：

- `README.md`
- `manifest.json`
- `inputs/README.md`
- `evidence/evidence_inventory.json`
- `structured_prd/structured_prd.json`
- `traceability/coverage_first_traceability.json`（主真源）
- `traceability/traceability_adapter.json`（兼容层）
- `traceability/traceability_matrix.json`（legacy 对照）
- `testcases/testcases_main.md`（主真源）
- `testcases/testcases.md`（兼容镜像）
- `reviews/review_record.md`

说明：

- `project_code` 会统一转大写
- `work_item_id` 会统一转大写
- `work_item_id` 中的空格会自动替换为中划线

## 校验入口

当前推荐口径：

- `structured_prd/structured_prd.md` 是结构化 PRD 的 authoring 真源
- `structured_prd/structured_prd.json` 是从 Markdown 编译出的机器投影
- `testcases/testcases_main.md` 是主 testcase 真源，`testcases/testcases.md` 仅保留兼容镜像
- `testcases/testpoints.md` / `testpoints.json` 与 `testcases_main.md` 同步生成，是以 `case_plan.json` 为来源的人工评审视图
- `traceability/coverage_first_traceability.json` 是主 traceability 真源
- `traceability/traceability_adapter.json` 是旧消费方兼容层
- `traceability/traceability_matrix.json` 仅保留 legacy 对照角色
- `feishu_ready.md` 是面向飞书同步的派生产物，不是业务真源

仓库当前提供 4 层校验入口：

1. `structured_prd` 校验

```bash
/usr/bin/python3 skills/prd-structuring/scripts/validate_structured_prd.py \
  --input assets/projects/WX-YYPT/structured_prd/structured_prd.json
```

2. testcase 校验

```bash
/usr/bin/python3 skills/case-generation/scripts/testcase_lint.py \
  --input assets/projects/WX-YYPT/testcases/testcases_main.md
```

3. review gate 校验

```bash
/usr/bin/python3 skills/review-gate/scripts/review_gate.py \
  --structured-prd assets/projects/WX-YYPT/structured_prd/structured_prd.json \
  --testcases assets/projects/WX-YYPT/testcases/testcases_main.md \
  --checklist skills/review-gate/checklists/manual_review_checklist.md
```

4. 项目级统一校验

```bash
/usr/bin/python3 scripts/validate_outputs.py --project-code WX-YYPT
```

也支持显式传入路径：

```bash
/usr/bin/python3 scripts/validate_outputs.py \
  --structured-prd assets/projects/WX-YYPT/structured_prd/demo.json \
  --testcases assets/projects/WX-YYPT/testcases/demo.md \
  --checklist skills/review-gate/checklists/manual_review_checklist.md
```

5. 工作项级统一校验

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

6. 生成工作项重跑任务包

```bash
/usr/bin/python3 scripts/prepare_regeneration_run.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

7. 生成 regeneration bundle 或由当前宿主执行同一任务包

```bash
/usr/bin/python3 scripts/generate_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --provider existing
```

也支持调用任意本地命令 / 本地工具 / 宿主执行器生成 bundle：

```bash
/usr/bin/python3 scripts/generate_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --provider command \
  --generator-command "/path/to/your-local-runner"
```

如需使用 HTTP endpoint 兼容入口，也可以继续使用：

```bash
/usr/bin/python3 scripts/generate_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --provider openai
```

8. 执行重生成 bundle

```bash
/usr/bin/python3 scripts/execute_regeneration_bundle.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --bundle assets/projects/WX-YYPT/work_items/REQ-001/.generation/latest/regeneration_bundle.json
```

9. 从 structured_prd.json 重建 structured_prd.md

```bash
/usr/bin/python3 scripts/render_structured_prd_markdown.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

10. 从 structured_prd.md 编译 structured_prd.json

```bash
/usr/bin/python3 scripts/compile_structured_prd_json.py \
  --input assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.md \
  --output assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json
```

## 初始化宽松、Review 严格

当前仓库对 testcase 校验采用分层策略：

- 初始化阶段宽松：刚创建的 `testcases.md` 允许只有表头
- 正式 review 严格：进入 `review_gate.py` 时，必须存在真实用例数据

这意味着：

- 新初始化的项目或工作项可以先保留空模板
- 正式进入评审和质量门时，必须补齐真实 testcase 内容

## 典型命令组合

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

测试提交流水线入口：

```bash
/usr/bin/python3 scripts/run_submission_pipeline.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001 \
  --input /path/to/prd.docx \
  --provider command \
  --generator-command "/path/to/your-local-runner"
```

说明：

- 测试只需提供需求文件或补充资料
- 脚本会自动落到 `inputs/`
- 自动创建或维护工作项
- 自动执行任务包创建、bundle 生成与执行
- 模型与 endpoint 应由当前宿主工具或运行时环境决定，而不是由仓库写死
- 默认运行到代码映证前
- 若未提供代码目录，会自动生成 `code_review_request.md` 提醒测试补充
- 若提供 `--frontend-code-dir` / `--backend-code-dir`，会把工作项状态推进到 `READY_FOR_CODE_REVIEW`

校验单个工作项：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code WX-YYPT \
  --work-item-id REQ-001
```

校验整个项目：

```bash
/usr/bin/python3 scripts/validate_outputs.py --project-code WX-YYPT
```

## 代码评审也是流水线环节

在产出 evidence / structured_prd / testcase 后，还需要补两轮代码评审：

1. 前端代码 CR
2. 后端代码 CR

默认产物路径：

- `code_reviews/frontend_code_review.md`
- `code_reviews/frontend_confirmation.json`
- `code_reviews/backend_code_review.md`
- `code_reviews/backend_confirmation.json`

约束：

- 代码评审只做映证，不修改业务代码
- 代码评审只新增 CR 产物，不修改历史产出物
- 两个 confirmation 都人工确认后，工作项级统一校验才会通过
