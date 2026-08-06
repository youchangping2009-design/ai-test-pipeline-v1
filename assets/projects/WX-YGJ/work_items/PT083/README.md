# PT083

- 项目编码：WX-YGJ
- 工作项 ID：PT083
- 标题：云挂机免费体验3（manifest 元数据当前简写为“云挂机免费体验”）
- 需求版本：未设置（manifest 当前为空字符串）
- 工作项级别：M

## 目录说明

- `inputs/`：该工作项原始资料与补充输入
- `image_evidence/`：图片类 PRD 的中间证据层
- `analysis/`：AI 推理层产物，先落 `analysis_report.md` 与 `reasoning_pack.json`
- `coverage/`：coverage planner 产物，沉淀 `coverage_matrix.json`
- `evidence/`：从原始输入抽取的证据清单
- `structured_prd/`：该工作项结构化 PRD 产物，其中 `structured_prd.md` 是结构化 Markdown 真源，`structured_prd.json` 是从其编译出的机器投影
- `acceptance/`：testability gate 与 acceptance examples 产物
- `design/`：责任划分、测试设计矩阵与 code review 映证反馈产物
- `traceability/`：证据、结构化产物与 testcase 的追踪矩阵
- `testcases/`：该工作项测试用例产物
- `reviews/`：该工作项评审记录
- `code_reviews/`：前端/后端代码评审与人工确认产物
- `.generation/`：该工作项的重生成任务包

## 建议流程

1. 将该需求原始资料放入 `inputs/`
2. 生成 `inputs/requirement_summary.md` 与 `inputs/source_manifest.json`
3. Requirement Sources 校验后通过 Harness 人工审核；当前 approval receipt 已绑定迁移 run 和内容指纹
4. 若输入主要是截图，产出 `image_evidence/image_evidence_inventory.json`
5. 生成 `analysis/analysis_report.md` 与 `analysis/reasoning_pack.json`
6. 生成 structured_prd、测试设计决策层与 `case_plan`
7. 同步生成 `testpoints.md/json` 与 `testcases_main.md`
8. 生成 Bundle、coverage-first traceability、review 和导出产物
9. 当前无代码样本使用 `scripts/validate_work_item.py --work-item-level M --skip-code-reviews --strict` 执行统一校验

当前正式样本数量：82 条 Coverage、62 条 Gate、75 条 Acceptance/Case Plan/Testcase/Testpoint/Bundle、25 条开发自测、37 条唯一 main Coverage 追溯，invalid=0。
