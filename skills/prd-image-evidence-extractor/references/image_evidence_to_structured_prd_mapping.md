# Image Evidence To Structured PRD Mapping

用于说明 `image_evidence_inventory.json` 如何稳定映射到 `structured_prd.json`。

## 映射原则

- 先 page / section，再 module / feature
- 先字段主体，再字段规则，再说明表
- 先显式文本，再视觉布局，再推断

## section 映射

- `filter_area`
  - `pages[].sections[]`
  - 对应 feature 的筛选规则可进入 `rules`
- `list_area`
  - `pages[].sections[]`
  - `visual_elements` 映射为 `visible_elements`
  - `interactive_entries` 映射为 feature 的 `interactive_entries`
  - 列头字段可映射为 `field_definitions` 或列表区 `field_refs`
- `action_area`
  - `pages[].sections[]`
  - 按钮行为映射为 `interactive_entries`
- `edit_modal`
  - `pages[].sections[]`
  - `field_candidates` 映射为 `field_definitions`
  - `field_rules` 映射为 `field_rules`
  - `section_rules` 可拆为 `rules / abnormal_scenarios / boundary_scenarios`
- `sort_modal`
  - `pages[].sections[]`
  - `section_rules` 映射为排序 feature 的 `rules`
- `field_rule_table`
  - `pages[].sections[]`
  - `field_rule_tables` 映射为所属字段 feature 的 `field_rule_tables`
  - 若说明表无独立交互，`section.feature_names` 应指向所属字段 feature，而不是额外拆独立 feature

## field_candidates 映射

- `display_name / field_name / data_type / required / editable / default_value / enum_values / format_rule / length_rule / data_source`
  -> `field_definitions[]`
- `conditional_visibility / conditional_editability / notes`
  -> 优先进入 `field_rules[]`

## field_rules 映射

- `rule_text`
  -> `field_rules[].rule_text`
- `rule_type`
  -> 根据 structured PRD 可选值归一化
- `error_message`
  -> 优先保留在 `field_rules.expected_effects` 或 `rules / abnormal_scenarios`

## field_rule_tables 映射

- `table_name / rows`
  -> `field_rule_tables[]`
- `row_name / rule_text / expected_effect`
  -> 每一行保持独立，不合并
- 若说明表描述的是字段枚举效果或附加字段，后续 testcase 应优先验证“字段 -> 效果”，不要退化成“查看说明表”

## 高风险映射点

- 列表列头不能只留在 `visual_elements`，关键列要同步进入字段层
- 条件不可编辑不能只放在字段 notes，必须进入 `field_rules`
- 删除限制不能只放 section 备注，必须进入 `rules / abnormal_scenarios`
- 精确提示语不要丢在抽取层，后续要继续进入 structured PRD

## 建议流程

1. 先产出 `image_evidence_inventory.json`
2. 运行 `validate_image_evidence.py`
3. 再用 PRD Structurer 消费 image evidence 映射到 structured PRD
4. 最后再走 structured PRD validator
