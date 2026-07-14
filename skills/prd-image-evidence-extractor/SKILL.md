---
name: prd-image-evidence-extractor
description: Use when PRD input is mainly screenshots, mockups, or prototype images and you need a stable image-evidence layer before structuring. Extract pages, sections, fields, field-rule tables, explicit text, visual layout, inference, confidence, and uncertain items into image_evidence_inventory JSON that downstream structuring can consume.
---

# PRD Image Evidence Extractor

用于把图片类 PRD 输入先转换为可追溯证据，再交给后续 `PRD Structurer` 消费。

## 何时使用

- 输入主要是截图、原型图、页面草图
- OCR 文本不完整，直接结构化偏离高
- 需要先沉淀“页面 / 板块 / 字段 / 规则 / 说明表 / 不确定项”

## 输出目标

优先输出：
- `image_evidence_inventory.json`

推荐遵循：
- [schema](../../schemas/image_evidence_inventory.schema.json)
- [template](templates/image_evidence_inventory.template.json)
- [contract](references/extraction_contract.md)
- [backend config playbook](references/backend_config_extraction_playbook.md)
- [backend config golden checklist](references/backend_config_golden_checklist.md)
- [config family variants](references/config_family_variants.md)
- [field naming conventions](references/field_naming_conventions.md)
- [mapping guide](references/image_evidence_to_structured_prd_mapping.md)
- [extraction prompt](references/extraction_prompt.md)
- [validator](scripts/validate_image_evidence.py)

## 工作流

1. 优先使用当前环境里最好用的本地模型 / OCR / 多模态工具，不绑定供应商。
2. 对每张图先识别页面，再识别板块，再识别字段和规则。
3. 每条识别结果必须区分：
   - `explicit_text`
   - `visual_layout`
   - `inference`
4. 若字段后面跟独立说明表，必须把该表绑定回字段，输出为 `field_rule_tables`；默认把它视为字段语义扩展，而不是新的配置对象。
5. 若识别不确定，不允许静默丢失，必须输出：
   - `confidence`
   - `needs_confirmation`
   - `ambiguity_reason`

6. 产出后必须执行自检校验：

```bash
/usr/bin/python3 skills/prd-image-evidence-extractor/scripts/validate_image_evidence.py \
  --input <image_evidence_inventory.json>
```

## 图片类后台配置页的专项抽取规则

若图片是“后台配置列表 + 添加弹窗 + 排序弹窗 + 说明表”的组合页，必须按下面顺序抽：

1. 先抽页面骨架
   - 筛选区
   - 列表区
   - 操作区
   - 添加弹窗
   - 编辑弹窗（若操作区存在编辑，即使图里未展开，也要显式记为同构待确认或同构已确认）
   - 排序弹窗
   - 字段说明表
   - 系统说明区 / 便签补充区
2. 再抽列表区
   - 列头字段
   - 操作列动作
   - 缩略图点击查看大图等交互
   - 创建人 / 创建时间 / 修改时间这类元数据列
3. 再抽弹窗字段矩阵
   - 字段名
   - 控件类型
   - 必填/非必填
   - 默认值
   - 数据来源
   - 是否可编辑
   - 条件展示 / 条件必填 / 条件不可编辑
4. 再抽排序和说明表
   - 初始顺序
   - 过滤条件
   - 删除/关闭后的顺位变化
   - 新增后的默认位置
   - 说明表每一行的效果与附加字段
5. 最后抽补充便签
   - 精确提示语
   - 上限是否带状态条件
   - 反向引用关系
   - 删除限制

对 `banner / 瓷片区 / 金刚区 / 弹窗` 这 4 类后台配置页，优先按 [backend config golden checklist](references/backend_config_golden_checklist.md) 自检：

- 页面骨架是否完整
- 列表区列头与操作区入口是否都有
- 添加/编辑弹窗字段矩阵是否补齐字段级属性
- 排序弹窗与说明表是否逐项承接
- 说明表是否已经明确回挂到所属字段语义，而不是漂成独立业务实体
- 条数上限、默认值、删除限制、状态原词是否原样保留

## 红字注释抽取要求

图片里字段旁的红字说明，默认视为 `explicit_text` 高优先级规则来源，必须尽量原词保留并拆成字段属性，而不是只保留摘要。

重点抽取：

- `文本输入框 / 下拉菜单 / 单选 / 多选 / 上传 / 开关`
- `必填 / 非必填`
- `默认为空 / 默认关闭 / 默认值为X`
- `可编辑 / 不可编辑`
- `content: ...`
- `数据来源于...`
- `仅在...时展示`
- `仅在...时可编辑`
- `提示“...”`

## 强制保真项

以下内容必须原词保留：
- 状态枚举
- 条数上限
- 时间间隔
- 排序主次规则
- 跳转目标
- 固定文案
- 精确错误提示语
- 字段 content 文案
- 删除限制中的“被引用 / 不可删除 / 无法删除”

## 领域模式

优先识别以下高频模式：
- 字段定义 + 说明表
- 状态字段
- 条数上限
- 排序弹窗
- 触达用户类型表
- 列表字段 + 操作区
- 添加 / 编辑弹窗字段矩阵
- 反向引用删除校验
- 同构配置页面家族

参考：
- [product patterns](../case-generation/references/product_description_patterns.md)
- [backend config playbook](references/backend_config_extraction_playbook.md)
- [backend config golden checklist](references/backend_config_golden_checklist.md)
- [config family variants](references/config_family_variants.md)

## 自检清单

- 是否抽出了列表区列头，而不是只写“配置列表”
- 是否抽出了操作区入口，而不是只写“可操作”
- 是否把添加/编辑弹窗整理成字段矩阵
- 是否补了字段的 `control_type / required / editable / default_value / data_source`
- 是否保留了红字里的固定 content、条件展示、条件不可编辑
- 是否逐行抽取了说明表
- 是否单独承接了删除限制、引用关系和错误提示
- 是否命中了后台配置页家族基线：`5 / 4 / 4 / 3` 条数上限、`展示企微单人单码`、`展示规则`
- 是否执行了 `validate_image_evidence.py`
