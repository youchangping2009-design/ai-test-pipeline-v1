# Codex Host Adapter

本目录只描述 Codex 如何接入仓库统一流程，不定义流程、模型或测试资产真源。

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

## Codex 专属适配

Codex 使用当前会话提供的模型、工具和项目指令。仓库不读取 Codex 私有配置或会话文件，也没有提交 Codex 专属运行时桥接脚本。

如需使用兼容 HTTP provider，和其他宿主一样显式提供通用运行时配置：

```bash
export ATP_MODEL=<MODEL>
export ATP_API_KEY=<API_KEY>
export ATP_BASE_URL=<BASE_URL>
```

## 适配边界

Codex adapter 可以处理：

- 当前会话上下文和工具能力
- Codex 私有项目指令
- 宿主侧运行时配置

不得处理：

- 重定义流程角色
- 修改 S/M/L 策略
- 切换 testcase 或 traceability 真源
- 绕过 strict gate
- 将 Codex 私有行为写入核心 prompts、skills 或 schemas

## 真源口径

- `testcases/testcases_main.md`：正式用例真源
- `testcases/case_plan.json`：用例计划真源
- `traceability/coverage_first_traceability.json`：追溯真源
- `tool_adapters/codex/`：仅宿主适配，不是流程真源
