# Extraction Contract

`image_evidence_inventory.json` 应尽量包含以下层次：

- `image_id`
- `source_file`
- `page_name`
- `section_name`
- `section_type`
- `evidence_source_type`
- `raw_text`
- `ocr_text`
- `visual_elements`
- `interactive_entries`
- `section_rules`
- `field_candidates`
- `field_rules`
- `field_rule_tables`
- `confidence`
- `needs_confirmation`
- `ambiguity_reason`

约束：
- `explicit_text` 优先级高于 `visual_layout`
- `visual_layout` 优先级高于 `inference`
- 低置信度内容允许进入待确认，但不允许静默丢失

对后台配置类截图，额外约束：

- 页面骨架必须尽量完整承接 `filter_area / list_area / action_area / edit_modal / sort_modal / field_rule_table / other`
- `visual_elements` 必须尽量包含列表列头、操作按钮、弹窗标题、排序对象、说明表标题
- `field_candidates` 必须尽量包含：
  - `field_name`
  - `display_name`
  - `data_type`
  - `control_type`
  - `required`
  - `default_value`
  - `editable`
  - `data_source`
  - `enum_values`
  - `content_values`
  - `conditional_visibility`
  - `conditional_editability`
- `field_rules` 必须尽量承接：
  - 上限规则
  - 排序规则
  - 删除限制
  - 精确提示语
- `interactive_entries` 必须尽量承接：
  - 添加
  - 编辑
  - 复制 / 复用
  - 删除
  - 排序
  - 点击图片查看大图
- `field_rule_tables` 必须逐行保留 `row_name / rule_text / expected_effect`

若图片中出现便签补充：

- 便签中的规则不得降级为普通备注
- 若便签描述了跨页面依赖，例如“活动被 banner/瓷片/金刚/弹窗引用后不可删除”，必须输出为独立 evidence，并标记为删除限制或依赖规则
- 若便签包含条数上限、默认值、状态过滤、精确提示语，也必须进入结构化规则，不得只保留为备注

推荐抽取粒度：

- `list_area`
  - 列头
  - 操作列
  - 列表数据来源说明
- `edit_modal`
  - 字段矩阵
  - 条件展示
  - 条件不可编辑
  - 默认值
- `sort_modal`
  - 排序对象
  - 过滤条件
  - 初始顺序
  - 删除/关闭后的顺位变化
  - 新增后的默认位置
- `field_rule_table`
  - 枚举行
  - 附加字段
  - 异常提示

后台配置页家族细则以 [backend_config_golden_checklist.md](backend_config_golden_checklist.md) 为准。
