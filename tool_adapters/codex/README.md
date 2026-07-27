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

如需让兼容 HTTP provider 从 Codex 本地配置解析运行时参数，显式设置：

```bash
export ATP_HOST_ADAPTER=codex
```

核心脚本随后按统一 adapter 协议加载：

```text
tool_adapters/codex/runtime_context.py
```

未设置 `ATP_HOST_ADAPTER` 时，仓库不会自动探测或默认绑定 Codex。

## 适配边界

Codex adapter 可以处理：

- 当前宿主配置读取
- 运行时模型、endpoint 和凭证解析
- 当前会话与本地执行器衔接

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
