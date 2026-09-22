# Reasoning 来源语义规则

## 目标

防止结构合法但与当前需求无关的历史样本术语、风险和测试维度进入 `analysis/reasoning_pack.json`。

## Grounding Contract 1.0

新工作项默认启用 `manifest.json.pipeline_policy.reasoning_grounding_required=true`，生成器必须输出 `grounding_contract_version=1.0`。

内容型条目必须满足：

- `explicit_rules`、`implicit_rules`、`field_constraints`、`data_source_rules`、`business_risks`、`edge_cases`、`ambiguities` 均有非空 `source_refs`。
- 每个来源必须包含非空 `path` 与 `excerpt`，且文件真实存在。
- `input_markdown` 的 `excerpt` 必须能在对应文本来源中回查。
- `recommended_test_dimensions.related_reasoning_ids` 与 `coverage_candidates.source_reasoning_ids` 必须非空，且只能引用当前 Reasoning Pack 中存在的 ID。

## 生成边界

- 通用生成器不得无条件写入具体项目、页面、组件、产品名或业务枚举。
- 图片需求的共性结构、跨页面承接、排序、状态和说明表风险，只能在当前 Evidence 出现对应信号时生成。
- 文本需求的风险、待确认问题和边界场景应从归一化摘要对应章节生成。
- 无法建立来源引用的推断不得进入正式 Reasoning Pack。

## 兼容策略

旧工作项未声明 `reasoning_grounding_required` 时仍执行来源存在性、文本摘录回查和悬空 ID 检查，但不强制补写 1.0 契约字段。新建工作项默认开启完整 1.0 门禁。
