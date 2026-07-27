# Claude Host Adapter

本目录只描述 Claude 类宿主如何接入仓库统一流程，不定义流程、模型或测试资产真源。

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

## Claude 专属适配

Claude 类宿主使用当前会话提供的模型、工具和项目指令。仓库不要求固定 Claude 型号，也没有提交 Claude 专属运行时桥接脚本。

## 适配边界

Claude adapter 可以处理：

- 当前会话上下文和工具能力
- Claude 私有项目指令
- 宿主侧运行时配置

不得处理：

- 重定义流程角色
- 修改 S/M/L 策略
- 切换 testcase 或 traceability 真源
- 绕过 strict gate
- 将 Claude 私有行为写入核心 prompts、skills 或 schemas

## 真源口径

- `testcases/testcases_main.md`：正式用例真源
- `testcases/case_plan.json`：用例计划真源
- `traceability/coverage_first_traceability.json`：追溯真源
- `tool_adapters/claude/`：仅宿主适配，不是流程真源
