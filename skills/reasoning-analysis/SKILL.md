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
  --schema schemas/reasoning_pack.schema.json
```

## 禁止行为

- 不得从既有 structured PRD 反推 reasoning。
- 不得把推断规则伪装成明确需求。
- 纯文本需求不得因缺少 image evidence 被阻塞。
