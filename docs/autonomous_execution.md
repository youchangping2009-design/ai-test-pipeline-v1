# Codex Autonomous Execution

本文档定义 Codex 在本仓库中的自驱动执行协议。目标是让 Codex 通过仓库内的队列、决策记录、验收命令和阻塞模板推进升级，而不是依赖用户在外部反复搬运上下文。

## 启动顺序

每次进入仓库后，Codex 必须先读取：

1. `START_HERE.md`
2. `WORKFLOW_CONTRACT.md`
3. `AGENTS.md`
4. `docs/roadmap/NEXT_ACTION.md`
5. `docs/roadmap/WORK_QUEUE.md`
6. `docs/roadmap/DECISION_LOG.md`

如果这些文件之间冲突，以 `WORKFLOW_CONTRACT.md` 的流程契约和 `docs/roadmap/DECISION_LOG.md` 的最新决策为准。

## 如何选择任务

1. 优先读取 `docs/roadmap/NEXT_ACTION.md`。
2. 如果 NEXT_ACTION 中存在 `status: todo` 或 `status: in_progress` 的任务，优先执行该任务。
3. 如果 NEXT_ACTION 为空、已完成或明确阻塞，则从 `docs/roadmap/WORK_QUEUE.md` 选择最高优先级 `todo` 任务。
4. 只选择一个任务进入执行，不跨阶段顺手大改。
5. 如果任务描述要求人类决策，或缺少必要业务信息，写入 `docs/roadmap/HUMAN_ACTION_REQUIRED.md`，并停止盲改。

## 如何执行任务

执行前必须输出简短计划，至少说明：

- 当前选择的任务 ID
- 本轮会改哪些类型的文件
- 本轮明确不改什么
- 完成后要跑哪些校验

执行时遵守：

- 不修改业务代码。
- 不切换 testcase 真源，除非 roadmap 明确进入 P3。
- 不绕过 strict gate。
- 不降低规则强度来通过校验。
- 不把 `risk_note` / `api_guard` 混入 `product_acceptance` 主用例。
- 不把 `soft_prompt` 升级为 `hard_block`。
- 不把 `technical_background` 生成正式业务用例。
- 不允许无 `case_plan_id` 的正式 testcase 进入 strict。
- 不允许正式 testcase 丢失页面/板块上下文；`testcases_main.md` 应按 `page_name + section_name` 分表。

## 如何验证任务

最小回归入口：

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```

该脚本会执行当前 P0.5 基线：

- PT083 非 strict 应通过。
- PT083 strict 应通过。
- PT083 eval 应通过。

如果任务修改了特定 validator、schema 或 eval fixture，还应额外运行对应脚本的局部校验。

若任务涉及 testcase 分组，还应运行：

```bash
/usr/bin/python3 skills/case-generation/scripts/validate_testcase_grouping.py \
  --input assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/testcases/testcases_main.md \
  --strict
```

## 如何处理失败

校验失败后，Codex 可以自动 repair，但最多 2 轮。

每轮 repair 必须满足：

- 根据失败信息定位具体规则或产物。
- 只改与失败直接相关的文件。
- 不通过删除校验、放宽 strict、降低规则强度来规避失败。
- repair 后重新运行失败命令和基线命令。

如果 2 轮后仍失败，停止继续盲改，写入 `docs/roadmap/HUMAN_ACTION_REQUIRED.md`。

仓库提供轻量 repair loop 入口：

```bash
/usr/bin/python3 scripts/run_repair_loop.py \
  --task-id P2-001 \
  --command-json '["/usr/bin/python3","scripts/run_quality_baseline.py"]' \
  --expect pass \
  --write-human-action-on-fail
```

该脚本只负责执行校验、区分 expected pass / expected fail、可选执行外部 repair 命令并限制最多 2 轮；它不绑定模型、provider 或宿主工具，也不允许通过降低规则强度来绕过 strict gate。

## 什么时候必须找人

以下情况必须写入 `docs/roadmap/HUMAN_ACTION_REQUIRED.md`，并等待用户决策：

- 需求含义无法从 PRD / evidence / structured_prd 判断。
- 是否属于本期范围无法确认。
- 需要修改业务代码。
- 需要切换 testcase 真源。
- strict gate 与用户明确业务期望冲突。
- eval fixture 的历史期望和当前契约冲突。
- 修复需要超过当前任务范围的大重构。

## 如何记录结果

任务完成后应更新：

- `docs/roadmap/NEXT_ACTION.md`：记录当前任务状态和下一步建议。
- `docs/roadmap/DECISION_LOG.md`：只记录已经确认的关键决策，不记录流水账。
- `docs/roadmap/HUMAN_ACTION_REQUIRED.md`：仅在存在真实阻塞时写入。

最终回复需要说明：

- 本轮完成的任务 ID。
- 新增/修改文件。
- 运行过的校验命令和结果。
- 剩余风险与下一步建议。
