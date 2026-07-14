# Image Evidence Consumption

用于说明 `PRD Structurer` 如何消费 `image_evidence_inventory.json`。

## 适用条件

- 输入主要是截图、原型图、页面草图
- 已先通过 `prd-image-evidence-extractor` 产出 `image_evidence_inventory.json`

## 消费顺序

1. 先按 `page_name / section_name / section_type` 还原页面骨架
2. 再把 `field_candidates` 映射为 `field_definitions`
3. 再把 `field_rules` 映射为 `field_rules`
4. 再把 `field_rule_tables` 逐行映射为 `field_rule_tables`
5. 最后把 `section_rules / interactive_entries / visual_elements` 补回 feature 和 pages.sections

## 强制要求

- 不得把 image evidence 重新压缩成摘要后再结构化
- 红字注释中的 `default_value / editable / content_values / conditional_visibility` 必须继续保留
- 列表列头与操作区入口不得在 `structured_prd` 层丢失
- 便签中的条数上限、删除限制、精确提示语必须继续进入 `rules / abnormal_scenarios / explicit_rules`
- 对后台配置页，`pages.sections` 应尽量完整包含 `filter_area / list_area / action_area / edit_modal / sort_modal / field_rule_table`
- `list_area` 不得只保留“配置列表”，必须尽量保留列头字段与元数据列
- `action_area` 不得只保留“支持操作”，必须尽量保留 `添加 / 编辑 / 复用 / 删除 / 排序`
- `field_rule_table` 可以保留在 `pages.sections` 作为证据板块，但若说明表无独立入口/动作，`modules.features` 应优先挂回所属字段 feature，不额外拆“查表 feature”

## 推荐校验

在生成 `structured_prd.json` 后，建议追加执行：

```bash
/usr/bin/python3 scripts/validate_image_evidence_mapping.py \
  --image-evidence <image_evidence_inventory.json> \
  --structured-prd <structured_prd.json>
```

若工作项包含后台配置页家族，建议继续执行：

```bash
/usr/bin/python3 scripts/validate_backend_config_chain.py \
  --image-evidence <image_evidence_inventory.json> \
  --evidence <evidence_inventory.json> \
  --structured-prd <structured_prd.json> \
  --testcases <testcases.md>
```
