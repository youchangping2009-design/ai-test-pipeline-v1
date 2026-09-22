# Reasoning Analysis Skill

## 目标

将 `requirement_summary.md`、`source_manifest.json`、原始输入及可选 image evidence 转换为机器可消费的需求推理包。

## 输入

- `inputs/requirement_summary.md`
- `inputs/source_manifest.json`
- `inputs/received_screenshots.md`（可选）
- `image_evidence/image_evidence_inventory.json`（可选）

## 输出

- `analysis/reasoning_pack.json`
- `analysis/analysis_report.md`
- 新工作项必须声明 `grounding_contract_version=1.0`

## 执行入口

```bash
python3 scripts/generate_reasoning_pack.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

## 校验入口

```bash
python3 skills/reasoning-analysis/scripts/validate_reasoning_pack.py \
  --input <reasoning_pack.json> \
  --schema schemas/reasoning_pack.schema.json \
  --require-grounding-contract
```

校验除 JSON Schema 外，还会检查内容型条目的来源文件、文本摘录回查，以及测试维度与 coverage candidate 的 reasoning ID 引用。正式规则见 `../../rules/reasoning_grounding_rules.md`。

## 禁止行为

- 不得从既有 structured PRD 反推 reasoning。
- 不得把推断规则伪装成明确需求。
- 纯文本需求不得因缺少 image evidence 被阻塞。
- 不得把历史样本的页面、组件、业务枚举或风险模板无证据注入当前工作项。
