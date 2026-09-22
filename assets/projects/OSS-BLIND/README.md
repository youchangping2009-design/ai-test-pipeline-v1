# OSS-BLIND

- 项目名称：待补充
- 业务线：待补充
- 资产模型：`work_item_truth`

## 目录

- `project_manifest.json`：项目级静态元数据
- `inputs/common/`：跨工作项共享资料
- `work_items/`：需求与测试资产正式真源
- `indexes/`：工作项、用例和风险的派生索引
- `reports/`：项目级质量汇总
- `knowledge/`：人工确认的可复用规则与样例

## 使用方式

```bash
python3 scripts/create_work_item.py --project-code OSS-BLIND --work-item-id REQ-001
python3 scripts/validate_work_item.py --project-code OSS-BLIND --work-item-id REQ-001 --strict
python3 scripts/refresh_project_views.py --project-code OSS-BLIND
python3 scripts/validate_project.py --project-code OSS-BLIND --strict
```

正式 structured PRD、Case Plan、Testpoints、Testcases、Traceability 和 Review 只保存在 `work_items/<WORK_ITEM_ID>/`；项目级索引与报告不得反写工作项。
