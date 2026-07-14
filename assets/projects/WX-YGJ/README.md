# WX-YGJ

- 项目编码：WX-YGJ
- 项目名称：待补充
- 业务线：待补充

## 目录说明

- `inputs/`：原始 PRD、截图、补充材料
- `image_evidence/`：图片类 PRD 的中间证据层
- `analysis/`：AI 推理层产物，先沉淀 `analysis_report.md` 与 `reasoning_pack.json`
- `coverage/`：coverage planner 产物，沉淀 `coverage_matrix.json`
- `evidence/`：原始输入证据清单
- `structured_prd/`：结构化 PRD 产物，其中 `structured_prd.md` 是结构化 Markdown 真源，`structured_prd.json` 是从其编译出的机器投影
- `traceability/`：证据、结构化结果与 testcase 的追踪矩阵
- `testcases/`：测试用例产物
- `reviews/`：评审记录与问题沉淀

## 建议流程

1. 将原始需求资料放入 `inputs/`
2. 若输入主要是截图，先生成 `image_evidence/image_evidence_inventory.json`
3. 先生成 `analysis/analysis_report.md` 与 `analysis/reasoning_pack.json`
4. 生成 `coverage/coverage_matrix.json`
5. 对具体需求先使用 `scripts/create_work_item.py` 初始化工作项
6. 对工作项执行 `scripts/prepare_regeneration_run.py`
7. 使用 `scripts/generate_regeneration_bundle.py` 生成 bundle
8. 在工作项 `code_reviews/` 中完成前端代码 CR、后端代码 CR 与人工确认
9. 运行 reviewer + scorer 产出质量报告
10. 使用 `scripts/execute_regeneration_bundle.py` 执行 bundle，并自动编译 `structured_prd.json` / 导出 `feishu_ready.md`
11. 使用 `scripts/validate_outputs.py` 或 `scripts/validate_work_item.py` 执行统一校验
