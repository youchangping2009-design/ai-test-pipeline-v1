# PT083

- 项目编码：WX-YGJ
- 工作项 ID：PT083
- 标题：PT083需求
- 需求版本：待补充

## 目录说明

- `inputs/`：该工作项原始资料与补充输入
- `image_evidence/`：图片类 PRD 的中间证据层
- `analysis/`：AI 推理层产物，先落 `analysis_report.md` 与 `reasoning_pack.json`
- `coverage/`：coverage planner 产物，沉淀 `coverage_matrix.json`
- `evidence/`：从原始输入抽取的证据清单
- `structured_prd/`：该工作项结构化 PRD 产物，其中 `structured_prd.md` 是结构化 Markdown 真源，`structured_prd.json` 是从其编译出的机器投影
- `traceability/`：证据、结构化产物与 testcase 的追踪矩阵
- `testcases/`：该工作项测试用例产物
- `reviews/`：该工作项评审记录
- `code_reviews/`：前端/后端代码评审与人工确认产物
- `.generation/`：该工作项的重生成任务包

## 建议流程

1. 将该需求原始资料放入 `inputs/`
2. 若输入主要是截图，先产出 `image_evidence/image_evidence_inventory.json`
3. 先生成 `analysis/analysis_report.md` 与 `analysis/reasoning_pack.json`
4. 生成 `coverage/coverage_matrix.json`
5. 使用 `scripts/prepare_regeneration_run.py` 生成本次重跑任务包
6. 使用 `scripts/generate_regeneration_bundle.py` 生成本次 bundle（existing / command / openai provider）
7. 使用 `scripts/execute_regeneration_bundle.py` 落盘产物并自动编译/导出/校验；其中先由 `structured_prd.md` 编译出 `structured_prd.json`
8. 完成前端代码 CR、后端代码 CR，并分别人工确认
9. 如需人工修订，再回写 bundle 或重新生成 bundle 后重跑
10. 运行 reviewer + scorer，产出质量报告
11. 使用 `scripts/validate_work_item.py` 执行工作项级统一校验
12. 使用项目级校验脚本对该工作项产物执行检查
