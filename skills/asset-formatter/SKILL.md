# Asset Formatter Skill

## 目标

将已通过评审的结构化需求、测试用例和评审记录整理为阅读友好的 `feishu_ready.md`。该技能对应仓库中的 `Asset Formatter` 角色，只负责渲染与格式整理，不生成业务规则、不修改测试真源。

## 输入

- `structured_prd/structured_prd.md`
- `structured_prd/structured_prd.json`
- `testcases/testcases_main.md`
- `testcases/testcases.md`
- `testcases/field_audit.json`
- `testcases/grouped_audit.json`
- `reviews/review_record.md`

## 输出

- `feishu_ready.md`

`feishu_ready.md` 是阅读和协作派生产物，不是 structured PRD、Case Plan 或 testcase 真源。

## 执行步骤

1. 确认 `testcases/testcases_main.md`、评审记录和必要审计产物存在。
2. 执行确定性导出：

```bash
/usr/bin/python3 scripts/export_feishu_ready.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

3. 执行工作项 strict，确认导出未掩盖上游失败：

```bash
/usr/bin/python3 scripts/validate_work_item.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --strict \
  --skip-code-reviews
```

## 强制约束

- 只允许写 `feishu_ready.md`。
- 不修改 `structured_prd/*`、`testcases/*`、`reviews/*` 或 `traceability/*`。
- 不改变用例标题、步骤、预期、优先级、标签和追溯关系。
- 不把阅读版 Markdown 反向作为任何正式生成真源。
- 上游 Validator 或 strict 失败时停止，不通过格式调整规避门禁。
