# Cursor Host Adapter

本目录只描述 Cursor 如何接入仓库统一流程，不定义流程、模型或测试资产真源。

## 统一入口

进入仓库后按以下顺序读取：

1. `AGENTS.md`
2. `START_HERE.md`
3. `WORKFLOW_CONTRACT.md`
4. `docs/operating_sop.md`

执行命令与其他宿主一致：

```bash
python3 scripts/create_work_item.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>

python3 scripts/prepare_regeneration_run.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>

python3 scripts/validate_work_item.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID> \
  --strict
```

## Cursor 专属适配

仓库不再提交 `.cursor/`。用 Cursor 打开本仓库时，直接读 `AGENTS.md` 与 `START_HERE.md`，不要把编辑器规则目录当成流程真源。

## 适配边界

Cursor adapter 可以处理：

- 当前会话模型和工具调用
- 本机私有工作区配置（不提交）

不得处理：

- 重定义流程角色
- 修改 S/M/L 策略
- 切换 testcase 或 traceability 真源
- 绕过 strict gate
- 将 Cursor 私有行为写入核心 prompts、skills 或 schemas

## 真源口径

- `testcases/testcases_main.md`：正式用例真源
- `testcases/case_plan.json`：用例计划真源
- `traceability/coverage_first_traceability.json`：追溯真源
